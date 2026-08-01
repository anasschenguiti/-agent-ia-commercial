"""
Configuration SQLAlchemy async pour PostgreSQL.
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.shared.config import settings

# Engine initialization with fallback for local dev
try:
    if "sqlite" in settings.DATABASE_URL:
        engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG)
    else:
        engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG, pool_size=10, max_overflow=20)
except Exception:
    engine = create_async_engine("sqlite+aiosqlite:///./sales_db.sqlite", echo=settings.DEBUG)

# Factory de sessions async
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Classe de base pour tous les modèles SQLAlchemy."""
    pass


async def get_db() -> AsyncSession:
    """Dépendance FastAPI : fournit une session de base de données."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Initialise les tables en base de données (dev/test uniquement)."""
    global engine, AsyncSessionLocal
    from sqlalchemy import text

    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            if "sqlite" not in str(engine.url):
                columns = [
                    "country VARCHAR",
                    "annual_revenue VARCHAR",
                    "technologies TEXT",
                    "data_confidence TEXT",
                    "phone_source VARCHAR",
                    "email_source VARCHAR",
                    "company_size_source VARCHAR",
                    "annual_revenue_source VARCHAR",
                    "date_collecte TIMESTAMP WITH TIME ZONE DEFAULT now()",
                    "base_legale VARCHAR DEFAULT 'Intérêt Légitime (Prospection B2B)'",
                    "role VARCHAR NOT NULL DEFAULT 'user'",
                ]
                for col in columns:
                    try:
                        await conn.execute(text(f"ALTER TABLE prospects ADD COLUMN IF NOT EXISTS {col}"))
                    except Exception:
                        pass
    except Exception as db_err:
        print(f"[Database] Connection PostgreSQL échouée ({db_err}). Initalisation en SQLite local...")
        engine = create_async_engine("sqlite+aiosqlite:///./sales_db.sqlite", echo=settings.DEBUG)
        AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            sqlite_columns = [
                "country TEXT",
                "annual_revenue TEXT",
                "technologies TEXT",
                "data_confidence TEXT",
                "phone_source TEXT",
                "email_source TEXT",
                "company_size_source TEXT",
                "annual_revenue_source TEXT",
                "date_collecte DATETIME",
                "base_legale TEXT",
                "score REAL",
            ]
            for col in sqlite_columns:
                try:
                    await conn.execute(text(f"ALTER TABLE prospects ADD COLUMN {col}"))
                except Exception:
                    pass

            try:
                await conn.execute(text("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'"))
            except Exception:
                pass


async def seed_users() -> None:
    """Cree un utilisateur administrateur par defaut si la table est vide."""
    from app.shared.models_sql import UserSQL
    from app.shared.auth import hash_password
    import uuid

    async with AsyncSessionLocal() as db:
        try:
            from sqlalchemy.future import select
            stmt = select(UserSQL)
            result = await db.execute(stmt)
            users = result.scalars().all()
            if not users:
                admin_user = UserSQL(
                    id=str(uuid.uuid4()),
                    email="admin@iksatech.com",
                    hashed_password=hash_password("admin"),
                    role="admin",
                )
                db.add(admin_user)
                await db.commit()
                print("[Database] Utilisateur admin par defaut cree (admin@iksatech.com / admin).")
        except Exception as e:
            await db.rollback()
            print(f"[Database] Erreur lors du seeding utilisateur : {e}")
        finally:
            await db.close()
