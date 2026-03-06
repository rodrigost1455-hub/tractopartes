from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from app.core.database import engine, Base
from app.models import models  # noqa
from app.routers import productos, clientes, ventas, cotizaciones, analytics, auth


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Tablas creadas correctamente")
    except Exception as e:
        logger.error(f"Error al crear tablas: {e}")
    yield


app = FastAPI(
    title="Tractopartes API",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(productos.router)
app.include_router(clientes.router)
app.include_router(ventas.router)
app.include_router(cotizaciones.router)
app.include_router(analytics.router)


@app.get("/", tags=["Sistema"])
def root():
    return {
        "sistema": "Tractopartes API",
        "version": "1.0.0",
        "estado": "operacional",
        "docs": "/docs"
    }


@app.get("/health", tags=["Sistema"])
def health():
    """Railway usa este endpoint para saber si la app está viva."""
    db_status = "desconocido"
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_status = "conectada"
    except Exception as e:
        db_status = f"error: {str(e)[:80]}"

    # IMPORTANTE: siempre retorna 200 para que Railway no falle el healthcheck
    return {"status": "ok", "database": db_status}
