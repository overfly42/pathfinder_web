from collections.abc import Generator

import pytest
import sqlalchemy
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.db import get_db
from app.main import app
from app.models import Base

TEST_DATABASE_URL = sqlalchemy.engine.make_url(settings.database_url).set(
    database=sqlalchemy.engine.make_url(settings.database_url).database + "_test"
)


@pytest.fixture(scope="session")
def db_engine() -> Generator[Engine, None, None]:
    """Creates (if needed) and schema-resets a dedicated `..._test` database on the
    same Postgres instance as `docker-compose.yml`'s `db` service — kept separate
    from the dev database so running tests never touches dev data."""
    admin_engine = create_engine(
        sqlalchemy.engine.make_url(settings.database_url).set(database="postgres"),
        isolation_level="AUTOCOMMIT",
    )
    with admin_engine.connect() as conn:
        exists = conn.execute(
            sqlalchemy.text("SELECT 1 FROM pg_database WHERE datname = :name"),
            {"name": TEST_DATABASE_URL.database},
        ).first()
        if not exists:
            conn.execute(sqlalchemy.text(f'CREATE DATABASE "{TEST_DATABASE_URL.database}"'))
    admin_engine.dispose()

    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def db_session(db_engine: Engine) -> Generator[Session, None, None]:
    """One connection + transaction per test, rolled back afterwards so tests
    never leak state into each other."""
    connection = db_engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection, autoflush=False, expire_on_commit=False)()
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    app.dependency_overrides[get_db] = lambda: db_session
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)
