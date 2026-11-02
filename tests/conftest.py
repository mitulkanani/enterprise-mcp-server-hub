import pytest

from app.storage.store import HubStore


@pytest.fixture
def store(tmp_path):
    return HubStore(str(tmp_path / "test.sqlite3"))
