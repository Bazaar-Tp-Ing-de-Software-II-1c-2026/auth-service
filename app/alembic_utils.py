from pathlib import Path
import os

from alembic import command
from alembic.config import Config


def run_migrations() -> None:
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))

    database_url = os.getenv("DATABASE_URL")
    if database_url:
        config.set_main_option("sqlalchemy.url", database_url)

    command.upgrade(config, "head")