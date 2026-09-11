"""Collect an entire Metrika window before replacing any persisted statistics.

One row per integration/day/goal, summed across selected counters. This module
does not commit its caller's transaction and never converts an API failure to 0.
"""
from datetime import date
from sqlalchemy import func, select

from core import models


def latest_goal_names(db, integration_id, goal_ids):
    ranked = select(
        models.MetrikaGoals.goal_id,
        models.MetrikaGoals.goal_name,
        func.row_number().over(
            partition_by=models.MetrikaGoals.goal_id,
            order_by=(models.MetrikaGoals.date.desc(), models.MetrikaGoals.id.desc()),
        ).label("rank"),
    ).where(
        models.MetrikaGoals.integration_id == integration_id,
        models.MetrikaGoals.goal_id.in_(goal_ids),
        models.MetrikaGoals.goal_name.is_not(None),
        models.MetrikaGoals.goal_name != "",
    ).subquery()
    return dict(db.execute(select(ranked.c.goal_id, ranked.c.goal_name).where(ranked.c.rank == 1)).all())


async def collect_goal_rows(api, queue, counter_ids, goal_ids, days, known_names, filters=None, batch_size=20):
    if not days or batch_size < 1:
        raise ValueError("A nonempty date window and positive batch size are required")
    rows = {}
    available_anywhere = set()
    # Create totals even for a confirmed, legitimately empty counter response.
    for day in days:
        rows[day, "all"] = {"date": day, "goal_id": "all", "goal_name": "Selected Goals", "conversion_count": 0}

    for counter_id in dict.fromkeys(counter_ids):
        # Metadata errors are errors, not evidence that a selected goal vanished.
        metadata = await queue.enqueue("metrica", api.get_counter_goals, counter_id)
        if not isinstance(metadata, list):
            raise ValueError("Invalid Metrika goals metadata")
        names = {str(goal["id"]): goal.get("name") for goal in metadata}
        available_anywhere.update(names)
        selected = [goal_id for goal_id in dict.fromkeys(goal_ids) if goal_id in names]
        for offset in range(0, len(selected), batch_size):
            batch = selected[offset:offset + batch_size]
            response = await queue.enqueue(
                "metrica", api.get_goals_stats, counter_id, days[0].isoformat(), days[-1].isoformat(),
                metrics=",".join(f"ym:s:goal{goal_id}visits" for goal_id in batch), filters=filters,
            )
            if not isinstance(response, list):
                raise ValueError("Invalid Metrika statistics response")
            by_day = {}
            for item in response:
                day = date.fromisoformat(item["dimensions"][0]["name"])
                values = item["metrics"]
                if day not in days or day in by_day or len(values) != len(batch):
                    raise ValueError("Invalid Metrika statistics date or metric count")
                counts = []
                for value in values:
                    # Visits are counts. Do not silently truncate/correct bad data.
                    count = int(value)
                    if isinstance(value, bool) or count < 0 or count != float(value):
                        raise ValueError("Invalid Metrika visit count")
                    counts.append(count)
                by_day[day] = counts
            for day in days:
                for goal_id, count in zip(batch, by_day.get(day, [0] * len(batch))):
                    row = rows.setdefault((day, goal_id), {
                        "date": day, "goal_id": goal_id,
                        "goal_name": names.get(goal_id) or known_names.get(goal_id) or f"Goal {goal_id}",
                        "conversion_count": 0,
                    })
                    row["conversion_count"] += count
                    rows[day, "all"]["conversion_count"] += count
    missing = [goal_id for goal_id in goal_ids if goal_id not in available_anywhere]
    return list(rows.values()), missing


def replace_goal_window(db, integration, days, rows, missing, known_names, notify_missing):
    # A SAVEPOINT protects existing values even when a caller catches this
    # failure and subsequently commits other, successfully collected channels.
    with db.begin_nested():
        db.query(models.MetrikaGoals).filter(
            models.MetrikaGoals.integration_id == integration.id,
            models.MetrikaGoals.date >= days[0],
            models.MetrikaGoals.date <= days[-1],
        ).delete(synchronize_session=False)
        if rows:
            db.bulk_insert_mappings(models.MetrikaGoals, [
                {**row, "integration_id": integration.id, "client_id": integration.client_id}
                for row in rows
            ])
        notify_missing(db, integration, missing, known_names)
        db.flush()
