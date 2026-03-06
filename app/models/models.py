"""
Modelos SQLAlchemy para el sistema de tractopartes.
Diseñados para escalar con un agente de IA en el futuro.
"""

from sqlalchemy import (
    Column, Integer, String, Float, Text, DateTime,
    ForeignKey, Enum, Boolean, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.core.database import Base


# ─────────────────────────────────────────────
# ENUMS
# ─────────────────────────────────────────────

class EstadoVenta(str, enum.Enum):
    pendiente = "pendiente"
    confirmada = "confirmada"
    enviada = "enviada"
    entregada = "entregada"
    cancelada = "cancelada"

class EstadoCotizacion(str, enum.Enum):
    borrador = "borrador"
    enviada = "enviada"
    aceptada = "aceptada"
    rechazada = "rechazada"
    vencida = "vencida"

class CategoriaProducto(str, enum.Enum):
    motor = "motor"
    transmision = "transmision"
    frenos = "frenos"
    suspension = "suspension"
    electrico = "electrico"
    carroceria = "carroceria"
    hidraulico = "hidraulico"
    escape = "escape"
    filtros = "filtros"
    otros = "otros"


# ─────────────────────────────────────────────
# MODELOS
# ─────────────────────────────────────────────

class Cliente(Base):
    __tablename__ = "clientes"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(200), nullable=False)
    empresa = Column(String(200))
    telefono = Column(String(20), unique=True, index=True)
    email = Column(String(200), unique=True, index=True)
    ciudad = Column(String(100))
    notas = Column(Text)
    activo = Column(Boolean, default=True)
    fecha_registro = Column(DateTime(timezone=True), server_default=func.now())
    fecha_actualizacion = Column(DateTime(timezone=True), onupdate=func.now())

    # Para el agente de IA: perfil de comportamiento
    preferencias = Column(Text)          # JSON con preferencias del cliente
    ultimo_contacto = Column(DateTime(timezone=True))
    canal_preferido = Column(String(50), default="whatsapp")  # whatsapp | email | web

    # Relaciones
    ventas = relationship("Venta", back_populates="cliente", lazy="dynamic")
    cotizaciones = relationship("Cotizacion", back_populates="cliente", lazy="dynamic")


class Producto(Base):
    __tablename__ = "productos"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(300), nullable=False)
    descripcion = Column(Text)
    marca = Column(String(100), index=True)
    modelo_compatible = Column(String(300))   # Ej: "Kenworth T680, Peterbilt 579"
    categoria = Column(Enum(CategoriaProducto), index=True)
    sku = Column(String(100), unique=True, index=True)
    precio = Column(Float, nullable=False)
    costo = Column(Float)
    stock = Column(Integer, default=0)
    stock_minimo = Column(Integer, default=5)   # Alerta de reabastecimiento
    ubicacion_bodega = Column(String(100))       # Ej: "Estante A - Nivel 3"
    activo = Column(Boolean, default=True)
    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now())
    fecha_actualizacion = Column(DateTime(timezone=True), onupdate=func.now())

    # Para analytics y Mercado Libre
    tags = Column(Text)              # JSON: ["filtro", "kenworth", "aceite"]
    imagen_url = Column(String(500))
    publicado_ml = Column(Boolean, default=False)  # Mercado Libre
    ml_item_id = Column(String(100))               # ID en Mercado Libre

    # Relaciones
    detalles_venta = relationship("DetalleVenta", back_populates="producto")
    detalles_cotizacion = relationship("DetalleCotizacion", back_populates="producto")

    # Índice compuesto para búsquedas por marca + categoría
    __table_args__ = (
        Index("ix_productos_marca_categoria", "marca", "categoria"),
    )


class Venta(Base):
    __tablename__ = "ventas"

    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False, index=True)
    fecha = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    total = Column(Float, nullable=False)
    estado = Column(Enum(EstadoVenta), default=EstadoVenta.pendiente, index=True)
    notas = Column(Text)
    creado_por = Column(String(100), default="sistema")  # "agente_ia" | "vendedor" | "sistema"
    cotizacion_origen_id = Column(Integer, ForeignKey("cotizaciones.id"), nullable=True)

    # Relaciones
    cliente = relationship("Cliente", back_populates="ventas")
    detalles = relationship("DetalleVenta", back_populates="venta", cascade="all, delete-orphan")
    cotizacion_origen = relationship("Cotizacion", back_populates="venta_generada")


class DetalleVenta(Base):
    __tablename__ = "detalles_venta"

    id = Column(Integer, primary_key=True, index=True)
    venta_id = Column(Integer, ForeignKey("ventas.id"), nullable=False, index=True)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False, index=True)
    cantidad = Column(Integer, nullable=False)
    precio_unitario = Column(Float, nullable=False)
    subtotal = Column(Float, nullable=False)  # calculado: cantidad * precio_unitario

    # Relaciones
    venta = relationship("Venta", back_populates="detalles")
    producto = relationship("Producto", back_populates="detalles_venta")


class Cotizacion(Base):
    __tablename__ = "cotizaciones"

    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False, index=True)
    fecha = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    fecha_vencimiento = Column(DateTime(timezone=True))
    total = Column(Float, nullable=False, default=0.0)
    estado = Column(Enum(EstadoCotizacion), default=EstadoCotizacion.borrador, index=True)
    notas = Column(Text)
    generada_por = Column(String(100), default="sistema")  # "agente_ia" | "vendedor"

    # Relaciones
    cliente = relationship("Cliente", back_populates="cotizaciones")
    detalles = relationship("DetalleCotizacion", back_populates="cotizacion", cascade="all, delete-orphan")
    venta_generada = relationship("Venta", back_populates="cotizacion_origen", uselist=False)


class DetalleCotizacion(Base):
    __tablename__ = "detalles_cotizacion"

    id = Column(Integer, primary_key=True, index=True)
    cotizacion_id = Column(Integer, ForeignKey("cotizaciones.id"), nullable=False, index=True)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False, index=True)
    cantidad = Column(Integer, nullable=False)
    precio = Column(Float, nullable=False)
    subtotal = Column(Float, nullable=False)

    # Relaciones
    cotizacion = relationship("Cotizacion", back_populates="detalles")
    producto = relationship("Producto", back_populates="detalles_cotizacion")


# ─────────────────────────────────────────────
# TABLA PARA EL AGENTE DE IA (FASE 2)
# Se incluye ahora para no migrar después
# ─────────────────────────────────────────────

class RegistroAgente(Base):
    """
    Guarda cada interacción del agente de IA con clientes.
    Útil para auditoría, mejora del agente y contexto de conversación.
    """
    __tablename__ = "registro_agente"

    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=True, index=True)
    canal = Column(String(50))          # "whatsapp" | "web"
    sesion_id = Column(String(200))     # ID único de la conversación
    mensaje_usuario = Column(Text)
    respuesta_agente = Column(Text)
    intencion = Column(String(100))     # "consulta_inventario" | "cotizar" | "comprar"
    accion_tomada = Column(String(200)) # "cotizacion_generada:123" | "venta_creada:456"
    tokens_usados = Column(Integer)
    fecha = Column(DateTime(timezone=True), server_default=func.now(), index=True)
