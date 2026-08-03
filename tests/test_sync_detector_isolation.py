from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from automation.sync import _run_detector_after_sync


def test_detector_failure_rolls_back_only_detector_savepoint(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    session_factory = sessionmaker(bind=engine)
    db = session_factory()
    try:
        db.execute(text("CREATE TABLE sync_probe (value VARCHAR(32) NOT NULL)"))
        db.commit()

        # Represents successfully collected advertising data which still
        # belongs to the outer synchronization transaction.
        db.execute(text("INSERT INTO sync_probe (value) VALUES ('sync-data')"))

        def failing_detector(session, _client_id):
            session.execute(text("INSERT INTO sync_probe (value) VALUES ('detector-data')"))
            raise RuntimeError("detector write failed")

        monkeypatch.setattr(
            "backend_api.services.detector.run_detector_for_client",
            failing_detector,
        )

        assert _run_detector_after_sync(db, "client-id") is False

        # The session remains usable and the original sync transaction can be
        # committed after the detector SAVEPOINT has been rolled back.
        db.execute(text("INSERT INTO sync_probe (value) VALUES ('sync-status')"))
        db.commit()

        values = db.execute(text("SELECT value FROM sync_probe ORDER BY rowid")).scalars().all()
        assert values == ["sync-data", "sync-status"]
    finally:
        db.close()
        engine.dispose()
