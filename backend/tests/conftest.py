import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app
from app.storage import storage


@pytest.fixture
def client(monkeypatch):
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestSession = sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(test_engine)

    def override_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    blobs = {}
    monkeypatch.setattr(storage, "put", lambda key, data, content_type: blobs.update({key: data}))
    monkeypatch.setattr(storage, "get", lambda key: blobs[key])
    monkeypatch.setattr(storage, "stream", lambda key, chunk_size=65536: iter([blobs[key]]))
    monkeypatch.setattr(storage, "delete", lambda key: blobs.pop(key, None))
    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(test_engine)
    test_engine.dispose()
