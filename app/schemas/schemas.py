"""
Schemas Pydantic — Validación de entrada y salida de la API.
"""

from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, List
from datetime import datetime
from app.models.models import EstadoVenta, EstadoCotizacion, CategoriaProducto


# ─────────────────────────────────────────────
# AUTH
# ─────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ─────────────────────────────────────────────
# CLIENTES
# ─────────────────────────────────────────────

class ClienteBase(BaseModel):
    nombre: str
    empresa: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[EmailStr] = None
    ciudad: Optional[str] = None
    notas: Optional[str] = None
    canal_preferido: Optional[str] = "whatsapp"

class ClienteCreate(ClienteBase):
    pass

class ClienteUpdate(BaseModel):
    nombre: Optional[str] = None
    empresa: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[EmailStr] = None
    ciudad: Optional[str] = None
    notas: Optional[str] = None

class ClienteResponse(ClienteBase):
    id: int
    activo: bool
    fecha_registro: datetime
    total_compras: Optional[float] = 0.0
    num_ventas: Optional[int] = 0

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────
# PRODUCTOS
# ─────────────────────────────────────────────

class ProductoBase(BaseModel):
    nombre: str
    descripcion: Optional[str] = None
    marca: Optional[str] = None
    modelo_compatible: Optional[str] = None
    categoria: Optional[CategoriaProducto] = None
    sku: str
    precio: float
    costo: Optional[float] = None
    stock: int = 0
    stock_minimo: int = 5
    ubicacion_bodega: Optional[str] = None
    tags: Optional[str] = None
    imagen_url: Optional[str] = None

    @field_validator("precio", "costo", mode="before")
    @classmethod
    def precio_positivo(cls, v):
        if v is not None and v < 0:
            raise ValueError("El precio no puede ser negativo")
        return v

class ProductoCreate(ProductoBase):
    pass

class ProductoUpdate(BaseModel):
    nombre: Optional[str] = None
    precio: Optional[float] = None
    costo: Optional[float] = None
    stock: Optional[int] = None
    stock_minimo: Optional[int] = None
    ubicacion_bodega: Optional[str] = None
    activo: Optional[bool] = None

class ProductoResponse(ProductoBase):
    id: int
    activo: bool
    publicado_ml: bool
    fecha_creacion: datetime

    class Config:
        from_attributes = True

class ProductoResumen(BaseModel):
    """Versión compacta para listas y el agente de IA."""
    id: int
    nombre: str
    sku: str
    marca: Optional[str]
    precio: float
    stock: int
    disponible: bool  # stock > 0

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────
# VENTAS
# ─────────────────────────────────────────────

class DetalleVentaCreate(BaseModel):
    producto_id: int
    cantidad: int
    precio_unitario: float

class DetalleVentaResponse(BaseModel):
    id: int
    producto_id: int
    nombre_producto: Optional[str] = None
    cantidad: int
    precio_unitario: float
    subtotal: float

    class Config:
        from_attributes = True

class VentaCreate(BaseModel):
    cliente_id: int
    detalles: List[DetalleVentaCreate]
    notas: Optional[str] = None
    cotizacion_origen_id: Optional[int] = None
    creado_por: str = "sistema"

class VentaResponse(BaseModel):
    id: int
    cliente_id: int
    nombre_cliente: Optional[str] = None
    fecha: datetime
    total: float
    estado: EstadoVenta
    notas: Optional[str]
    detalles: List[DetalleVentaResponse] = []

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────
# COTIZACIONES
# ─────────────────────────────────────────────

class DetalleCotizacionCreate(BaseModel):
    producto_id: int
    cantidad: int
    precio: Optional[float] = None  # Si None, usa precio actual del producto

class DetalleCotizacionResponse(BaseModel):
    id: int
    producto_id: int
    nombre_producto: Optional[str] = None
    cantidad: int
    precio: float
    subtotal: float

    class Config:
        from_attributes = True

class CotizacionCreate(BaseModel):
    cliente_id: int
    detalles: List[DetalleCotizacionCreate]
    notas: Optional[str] = None
    generada_por: str = "sistema"

class CotizacionResponse(BaseModel):
    id: int
    cliente_id: int
    nombre_cliente: Optional[str] = None
    fecha: datetime
    fecha_vencimiento: Optional[datetime]
    total: float
    estado: EstadoCotizacion
    notas: Optional[str]
    generada_por: str
    detalles: List[DetalleCotizacionResponse] = []

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────
# ANALYTICS
# ─────────────────────────────────────────────

class TopProducto(BaseModel):
    id: int
    nombre: str
    sku: str
    marca: Optional[str]
    total_vendido: int
    total_ingresos: float
    num_ventas: int

class TopCliente(BaseModel):
    id: int
    nombre: str
    empresa: Optional[str]
    telefono: Optional[str]
    total_gastado: float
    num_ventas: int
    ultima_compra: Optional[datetime]

class ResumenInventario(BaseModel):
    total_productos: int
    productos_sin_stock: int
    productos_stock_bajo: int
    valor_inventario: float

class ProductosJuntos(BaseModel):
    producto_a: str
    producto_b: str
    veces_juntos: int
