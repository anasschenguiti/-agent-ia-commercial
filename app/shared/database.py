"""
Configuration SQLAlchemy async pour PostgreSQL.
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.shared.config import settings

# Moteur async
if "sqlite" in settings.DATABASE_URL:
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,
    )
else:
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,
        pool_size=10,
        max_overflow=20,
    )

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
    from sqlalchemy import text
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Migrations automatiques de schéma pour PostgreSQL/SQLite
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
            "base_legale VARCHAR DEFAULT 'Intérêt Légitime (Prospection B2B)'"
        ]
        if "sqlite" not in settings.DATABASE_URL:
            for col in columns:
                try:
                    await conn.execute(text(f"ALTER TABLE prospects ADD COLUMN IF NOT EXISTS {col}"))
                except Exception:
                    pass


async def seed_users() -> None:
    """Crée un utilisateur administrateur par défaut si la table est vide."""
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
                    hashed_password=hash_password("admin")
                )
                db.add(admin_user)
                await db.commit()
                print("[Database] Utilisateur admin par défaut créé (admin@iksatech.com / admin).")
        except Exception as e:
            await db.rollback()
            print(f"[Database] Erreur lors du seeding utilisateur : {e}")
        finally:
            await db.close()
