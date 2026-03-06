"""
Conexión a PostgreSQL con SQLAlchemy.
Compatible con Railway y variables de entorno.
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://usuario:password@localhost:5432/tractopartes"
)

# Railway entrega URLs con prefijo "postgres://" — SQLAlchemy necesita "postgresql://"
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,       # Verifica conexión antes de usar
    pool_size=10,             # Conexiones simultáneas
    max_overflow=20,
    echo=False                # Cambiar a True para debug SQL
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Dependency de FastAPI para inyectar sesión de DB."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
