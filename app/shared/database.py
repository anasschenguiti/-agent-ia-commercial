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


async def seed_prospects() -> None:
    """Cree des prospects B2B de demonstration par defaut si la table prospects est vide."""
    from app.prospection.models import ProspectSQL
    import uuid
    from datetime import datetime, timezone

    async with AsyncSessionLocal() as db:
        try:
            from sqlalchemy.future import select
            stmt = select(ProspectSQL)
            result = await db.execute(stmt)
            prospects = result.scalars().all()
            if not prospects:
                sample_leads = [
                    ProspectSQL(
                        id=str(uuid.uuid4()),
                        first_name="Anass",
                        last_name="Chenguiti",
                        job_title="Directeur Général",
                        company="Atlas Digital Solutions",
                        email="anass@atlasdigital.ma",
                        phone="+212661234567",
                        website="https://atlasdigital.ma",
                        linkedin_url="https://linkedin.com/in/anass-chenguiti",
                        industry="Technologies & IA",
                        company_size="20-50 employés",
                        location="Casablanca",
                        country="Maroc",
                        annual_revenue="10M - 50M MAD",
                        technologies="Next.js, Python, FastAPI, Docker",
                        score=92.0,
                        status="Qualifié HOT",
                        base_legale="Intérêt Légitime (Prospection B2B)",
                        created_at=datetime.now(timezone.utc)
                    ),
                    ProspectSQL(
                        id=str(uuid.uuid4()),
                        first_name="Fatima-Zahra",
                        last_name="El Amrani",
                        job_title="VP Commercial & Business Dev",
                        company="Technopark Maroc",
                        email="fatimazahra@technopark.ma",
                        phone="+212662987654",
                        website="https://technopark.ma",
                        linkedin_url="https://linkedin.com/in/fz-elamrani",
                        industry="Incubation & Innovation",
                        company_size="50-200 employés",
                        location="Rabat",
                        country="Maroc",
                        annual_revenue="50M - 100M MAD",
                        technologies="CRM HubSpot, Odoo ERP, Cloud AWS",
                        score=85.0,
                        status="Qualifié WARM",
                        base_legale="Intérêt Légitime (Prospection B2B)",
                        created_at=datetime.now(timezone.utc)
                    ),
                    ProspectSQL(
                        id=str(uuid.uuid4()),
                        first_name="Mehdi",
                        last_name="Bennani",
                        job_title="Chief Technology Officer",
                        company="Financial Systems Morocco",
                        email="m.bennani@finsys.ma",
                        phone="+212663112233",
                        website="https://finsys.ma",
                        linkedin_url="https://linkedin.com/in/mehdi-bennani-tech",
                        industry="Services Financiers & FinTech",
                        company_size="100-500 employés",
                        location="Casablanca",
                        country="Maroc",
                        annual_revenue="100M+ MAD",
                        technologies="PostgreSQL, Redis, LangChain, Kubernetes",
                        score=78.0,
                        status="Qualifié WARM",
                        base_legale="Intérêt Légitime (Prospection B2B)",
                        created_at=datetime.now(timezone.utc)
                    ),
                    ProspectSQL(
                        id=str(uuid.uuid4()),
                        first_name="Sara",
                        last_name="Chraibi",
                        job_title="Responsable Achats B2B",
                        company="Logistics & Supply Casa",
                        email="sara.chraibi@logistics.ma",
                        phone="+212664556677",
                        website="https://logistics.ma",
                        linkedin_url="https://linkedin.com/in/sara-chraibi",
                        industry="Logistique & Transport",
                        company_size="10-50 employés",
                        location="Mohammedia",
                        country="Maroc",
                        annual_revenue="5M - 20M MAD",
                        technologies="SAP ERP, MySQL",
                        score=65.0,
                        status="Prospect Nouveau",
                        base_legale="Intérêt Légitime (Prospection B2B)",
                        created_at=datetime.now(timezone.utc)
                    )
                ]
                for p in sample_leads:
                    db.add(p)
                await db.commit()
                print("[Database] Prospects B2B de demonstration crees par defaut.")
        except Exception as e:
            await db.rollback()
            print(f"[Database] Erreur lors du seeding des prospects : {e}")
        finally:
            await db.close()
