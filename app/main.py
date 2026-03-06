"""
Tractopartes API — Sistema de gestión para venta de refacciones de tractocamiones.
Diseñado para escalar con un agente de IA (WhatsApp + Web).
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from app.core.database import engine, Base
from app.models import models  # noqa: F401
from app.routers import productos, clientes, ventas, cotizaciones, analytics, auth


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Tablas creadas/verificadas correctamente")
    except Exception as e:
        logger.error(f"⚠️  Error al crear tablas: {e}")
    yield


app = FastAPI(
    title="Tractopartes API",
    description="""
    ## Sistema de gestión para venta de refacciones de tractocamiones

    ### Módulos disponibles:
    - **Productos** — Inventario completo con búsqueda avanzada
    - **Clientes** — Registro y historial de compras
    - **Ventas** — Registro con descuento automático de stock
    - **Cotizaciones** — Generación automática (lista para agente de IA)
    - **Analytics** — Top productos, clientes, rotación de inventario

    ### Autenticación:
    Usar el endpoint `/auth/login` para obtener un token JWT.
    Incluirlo en cada request: `Authorization: Bearer <token>`
    """,
    version="1.0.0",
    lifespan=lifespan
)

# ─── CORS ─────────────────────────────────────────────────────────────────────
# Ajustar origins en producción para mayor seguridad
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── ROUTERS ──────────────────────────────────────────────────────────────────
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
        "docs": "/docs",
        "redoc": "/redoc"
    }


@app.get("/health", tags=["Sistema"])
def health():
    """
    Healthcheck para Railway.
    SIEMPRE responde 200 — Railway necesita esto para considerar el deploy exitoso.
    """
    db_status = "desconocido"
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_status = "conectada"
    except Exception as e:
        db_status = f"error: {str(e)[:80]}"

    return {"status": "ok", "database": db_status}
