from unittest.mock import MagicMock, patch

import pytest

from app.database import get_db


def test_get_db_yields_session_and_closes_on_success():
    fake_db = MagicMock()

    with patch("app.database.SessionLocal", return_value=fake_db):
        generator = get_db()
        yielded = next(generator)
        assert yielded is fake_db

        with pytest.raises(StopIteration):
            next(generator)

    fake_db.close.assert_called_once()


def test_get_db_closes_session_on_exception_path():
    fake_db = MagicMock()

    with patch("app.database.SessionLocal", return_value=fake_db):
        generator = get_db()
        next(generator)

        with pytest.raises(RuntimeError):
            generator.throw(RuntimeError("boom"))

    fake_db.close.assert_called_once()
