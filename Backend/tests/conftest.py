import os
import uuid

# Must be set before importing app modules (Settings requires DATABASE_URL)
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite://")
os.environ.setdefault("GROQ_API_KEY", "test")
os.environ.setdefault("GEMINI_API_KEY", "test")
os.environ.setdefault("SMTP_EMAIL", "test@example.com")
os.environ.setdefault("SMTP_PASSWORD", "test-password")
os.environ.setdefault("SMTP_SERVER", "smtp.test.local")
os.environ.setdefault("SMTP_PORT", "587")

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app as fastapi_app
print("APP =", fastapi_app)
print("TYPE =", type(fastapi_app))
from app.database import Base, get_db
from app.firebase import get_current_user
#import app.models  # noqa: F401 — register all models with Base.metadata
from app.models.template import Template, TemplateQuestion

# holds the per-test sessionmaker so the app dependency uses the same DB
_state = {"sessionmaker": None}

# uid of the currently "authenticated" user
_current_user = {"uid": "user-1"}


async def override_get_db():
    async with _state["sessionmaker"]() as session:
        yield session


async def override_get_current_user():
    return dict(_current_user)


fastapi_app.dependency_overrides[get_db] = override_get_db
fastapi_app.dependency_overrides[get_current_user] = override_get_current_user


@pytest_asyncio.fixture
async def db():
    """Fresh in-memory SQLite database per test."""
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    _state["sessionmaker"] = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with _state["sessionmaker"]() as session:
        yield session

    await engine.dispose()
    _state["sessionmaker"] = None


@pytest.fixture
def as_user():
    """Switch the authenticated user for subsequent requests."""
    def _set(uid: str):
        _current_user["uid"] = uid
    yield _set
    _current_user["uid"] = "user-1"


@pytest_asyncio.fixture
async def client(db):
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def stub_emails(monkeypatch):
    """Never send real emails from tests."""
    async def fake_send_trip_invite(**kwargs):
        return True

    async def fake_send_final_plan(**kwargs):
        return None

    monkeypatch.setattr("app.api.trips.send_trip_invite", fake_send_trip_invite)
    monkeypatch.setattr("app.api.votes.send_final_plan", fake_send_final_plan)


@pytest_asyncio.fixture
async def template_id(db):
    """A minimal form template with one required choice and one optional text question."""
    template = Template(
        id=str(uuid.uuid4()),
        name="Weekend Trip",
        description="Test template",
        icon="T",
        is_custom=False,
    )
    db.add(template)
    await db.flush()
    db.add_all([
        TemplateQuestion(
            id=str(uuid.uuid4()),
            template_id=template.id,
            question_text="What is your budget?",
            question_type="single_choice",
            options=["Low", "High"],
            is_required=True,
            order=1,
        ),
        TemplateQuestion(
            id=str(uuid.uuid4()),
            template_id=template.id,
            question_text="Any notes?",
            question_type="text",
            options=None,
            is_required=False,
            order=2,
        ),
    ])
    await db.commit()
    return template.id
