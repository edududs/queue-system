from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ..app.auth.models import TokenData
from ..app.auth.service import get_password_hash
from ..app.models.base import Base
from ..app.models.users import User
from ..app.rate_limiter import limiter

app_root = Path(__file__).parent.parent

SQLALCHEMY_DATABASE_URL = f"sqlite:///{app_root}/test.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db_session():
    # Use a unique database URL for testing

    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_user():
    # Create a user with a known password hash
    password_hash = get_password_hash("password123")
    return User(
        id=uuid4(),
        username="username",
        email="test@example.com",
        first_name="Test",
        last_name="User",
        hashed_password=password_hash,
    )


@pytest.fixture
def test_token_data():
    return TokenData(user_id=str(uuid4()))


@pytest.fixture
def client(db_session):
    from ..app.main import app
    from ..app.settings.database import get_db

    # Disable rate limiting for tests
    limiter.reset()

    def override_get_db():
        try:
            yield db_session
        finally:
            db_session.close()

    app.dependency_overrides[get_db] = override_get_db

    from fastapi.testclient import TestClient

    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers(client, db_session):
    # Register a test user
    response = client.post(
        "/auth/",
        json={
            "username": "username",
            "email": "test.user@example.com",
            "password": "testpassword123",
            "first_name": "Test",
            "last_name": "User",
        },
    )
    assert response.status_code == 201

    # Login to get access token
    response = client.post(
        "/auth/token",
        data={
            "username": "username",
            "password": "testpassword123",
            "grant_type": "password",
        },
    )
    assert response.status_code == 200
    token = response.json()["access_token"]

    return {"Authorization": f"Bearer {token}"}
