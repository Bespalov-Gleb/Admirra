"""Production-compatible PostgreSQL fixture without pending DevOps tables."""
import os
import uuid
from urllib.parse import urlsplit

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def pg():
    url = os.getenv("ISOLATED_POSTGRES_URL")
    if not url:
        pytest.skip("isolated PostgreSQL required")
    assert os.getenv("WW_TEST") == "1" and urlsplit(url).hostname == "test-db"
    schema = "assistant_" + uuid.uuid4().hex
    admin = sa.create_engine(url)
    with admin.begin() as db:
        db.execute(sa.text(f'CREATE SCHEMA "{schema}"'))
    engine = sa.create_engine(url, connect_args={"options": f"-csearch_path={schema} -cstatement_timeout=5000"})
    try:
        yield sessionmaker(bind=engine), engine
    finally:
        engine.dispose()
        with admin.begin() as db:
            db.execute(sa.text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()
