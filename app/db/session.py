from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool, StaticPool

from app.core.config import settings

_url = settings.sqlalchemy_url

if _url.startswith("sqlite"):
    # Una base en memoria necesita una sola conexión compartida, si no cada
    # sesión ve una base vacía. Un archivo sí puede atender varias peticiones
    # a la vez: StaticPool las mete todas en la misma conexión y SQLite
    # devuelve fechas vacías. NullPool abre y cierra una conexión por petición.
    _destino = make_url(_url).database
    en_memoria = not _destino or _destino == ":memory:"
    engine = create_engine(
        _url,
        connect_args={"check_same_thread": False, "timeout": 30},
        poolclass=StaticPool if en_memoria else NullPool,
        echo=settings.DEBUG,
    )

    @event.listens_for(engine, "connect")
    def _sqlite_listo(conexion, _registro):
        cursor = conexion.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        if not en_memoria:
            cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()

else:
    # pool_pre_ping: Supabase y Render cortan conexiones quietas.
    engine = create_engine(
        _url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        echo=settings.DEBUG,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
