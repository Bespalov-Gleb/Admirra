"""Lossless totals and explicit pagination for compact VK tool responses."""
from datetime import date
from decimal import Decimal


def page_options(args):
    offset, limit = args.get('offset', 0), args.get('limit', 100)
    if type(offset) is not int or offset < 0:
        raise ValueError('offset должен быть целым числом >= 0')
    if type(limit) is not int or not 1 <= limit <= 200:
        raise ValueError('limit должен быть целым числом от 1 до 200')
    return offset, limit


def page(rows, offset, limit):
    end = offset + limit
    return {'rows': rows[offset:end], 'row_count': len(rows),
            'returned_count': len(rows[offset:end]), 'offset': offset,
            'has_more': end < len(rows), 'next_offset': end if end < len(rows) else None}


def validate_period(args):
    start, end = date.fromisoformat(args['date_from']), date.fromisoformat(args['date_to'])
    if end < start:
        raise ValueError('date_to должен быть не раньше date_from')
    if (end - start).days >= 366:
        raise ValueError('Запрашивайте не более 366 дней за один вызов')


def select_campaigns(campaigns, requested):
    if requested is None or requested == []:
        return campaigns
    if not isinstance(requested, list) or any(
        isinstance(x, bool) or not isinstance(x, (str, int)) or not str(x).strip()
        for x in requested
    ):
        raise ValueError('campaign_ids должен быть списком ID кампаний')
    ids = {str(x).strip() for x in requested}
    known = {str(c['id']) for c in campaigns}
    if ids - known:
        raise ValueError('Некоторые campaign_ids не найдены в выбранном проекте; '
                         'получите ID через vk_get_campaigns')
    return [c for c in campaigns if str(c['id']) in ids]


def aggregate(rows, group_by='campaign'):
    groups = {}
    total = {'impressions': 0, 'clicks': 0, 'conversions': 0, 'cost': Decimal(0)}
    for row in rows:
        key = str(row['campaign_id']) if group_by == 'campaign' else row['date']
        if key not in groups:
            groups[key] = dict(impressions=0, clicks=0, conversions=0, cost=Decimal(0))
            if group_by == 'campaign':
                groups[key].update(campaign_id=key, campaign_name=row.get('campaign_name'))
            else:
                groups[key]['date'] = key
        for metric in ('impressions', 'clicks', 'conversions', 'cost'):
            value = Decimal(str(row.get(metric) or 0)) if metric == 'cost' else int(row.get(metric) or 0)
            if metric == 'cost' and not value.is_finite():
                raise ValueError('VK вернул некорректное значение расхода')
            total[metric] += value
            groups[key][metric] += value

    def finish(item):
        cost = item['cost']
        return {**item, 'cost': float(cost.quantize(Decimal('0.01'))),
                'cpc': float(round(cost / item['clicks'], 2)) if item['clicks'] else None,
                'cpa': float(round(cost / item['conversions'], 2)) if item['conversions'] else None}

    result = [finish(item) for item in groups.values()]
    result.sort(key=(lambda r: (-r['cost'], -r['impressions'], r['campaign_id']))
                if group_by == 'campaign' else lambda r: r['date'])
    return finish(total), result
