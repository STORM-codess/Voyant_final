from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, DeclarativeBase
import ssl
from app.config import settings

ssl_context = ssl.create_default_context()
if not settings.DB_SSL_VERIFY:
    # relaxed verification for local/dev or providers with self-signed chains;
    # set DB_SSL_VERIFY=true in production with proper certificates
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=True,
    connect_args={"ssl": ssl_context},
    # Neon (serverless Postgres) drops idle connections, which otherwise
    # surfaces as "connection was closed in the middle of operation" when
    # SQLAlchemy reuses a dead pooled connection. pre_ping checks liveness
    # before use; recycle proactively retires connections before Neon's
    # idle timeout.
    pool_pre_ping=True,
    pool_recycle=300,
)

AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

class Base(DeclarativeBase):
    pass

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()