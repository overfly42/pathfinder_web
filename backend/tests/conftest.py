import os
from collections.abc import Callable, Generator

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
from app.seed import (
    class_ability_granted_feat_seed,
    class_ability_option_seed,
    class_ability_seed,
    class_option_seed,
    class_seed,
    companion_seed,
    condition_seed,
    feat_seed,
    item_seed,
    race_seed,
    secondary_class_seed,
    skill_seed,
    spell_seed,
    trait_seed,
    weapon_ability_seed,
)

# One database per pytest-xdist worker (`pytest -n 8`): `..._test_gw0`,
# `..._test_gw1`, ... — workers run in parallel and each resets its own
# schema, so they must never share one. Plain `..._test` when not running
# under xdist.
_WORKER = os.environ.get("PYTEST_XDIST_WORKER")
TEST_DATABASE_URL = sqlalchemy.engine.make_url(settings.database_url).set(
    database=sqlalchemy.engine.make_url(settings.database_url).database + "_test" + (f"_{_WORKER}" if _WORKER else "")
)

# Every catalog seed function, in foreign-key order. The whole catalog is
# seeded once per test database (`db_engine` below) and committed, instead of
# once per test: re-seeding ~thousands of rows row-by-row in every test was
# nearly all of the suite's runtime. Each test still runs inside its own
# rolled-back transaction (`db_session`), so a test that changes catalog rows
# can't leak that into the next one.
_SEED_FUNCTIONS: list[tuple[object, str]] = [
    (race_seed, "seed_races"),
    (class_seed, "seed_classes"),
    (class_option_seed, "seed_class_options"),
    (skill_seed, "seed_skills"),
    (class_ability_seed, "seed_class_abilities"),
    (feat_seed, "seed_feats"),
    (class_ability_option_seed, "seed_class_ability_options"),
    (class_ability_granted_feat_seed, "seed_class_ability_granted_feats"),
    (secondary_class_seed, "seed_secondary_class_abilities"),
    (companion_seed, "seed_companions"),
    (spell_seed, "seed_spells"),
    (item_seed, "seed_items"),
    (item_seed, "seed_item_granted_spells"),
    (weapon_ability_seed, "seed_weapon_abilities"),
    (trait_seed, "seed_traits"),
    (condition_seed, "seed_conditions"),
]
_ORIGINAL_SEED_FUNCTIONS: list[Callable[[Session], None]] = [
    getattr(module, name) for module, name in _SEED_FUNCTIONS
]


def _already_seeded(db: Session) -> None:
    """Stand-in for every `seed_*` function inside tests: the catalog is
    already there (`db_engine`), and seeding is an idempotent upsert, so
    skipping it changes nothing a test can observe."""
    del db


# Replaced on the modules themselves at conftest import time — before any
# test module runs its own `from app.seed.x import seed_y` — so every
# explicit `seed_y(db_session)` call in the tests becomes a no-op.
for _module, _name in _SEED_FUNCTIONS:
    setattr(_module, _name, _already_seeded)


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
    Base.metadata.drop_all(engine)  # a previous run killed mid-way leaves its tables behind
    Base.metadata.create_all(engine)
    with Session(engine, autoflush=False) as session:  # same as `db_session` below; the seeds rely on it
        for seed in _ORIGINAL_SEED_FUNCTIONS:
            seed(session)
        session.commit()
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
