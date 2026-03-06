"""
Router de Ventas — Registro y consulta de ventas.
Descuenta stock automáticamente al confirmar una venta.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from datetime import datetime
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import Venta, DetalleVenta, Producto, Cliente, EstadoVenta
from app.schemas.schemas import VentaCreate, VentaResponse, DetalleVentaResponse

router = APIRouter(prefix="/ventas", tags=["Ventas"])


def _build_venta_response(venta: Venta) -> VentaResponse:
    detalles = [
        DetalleVentaResponse(
            id=d.id,
            producto_id=d.producto_id,
            nombre_producto=d.producto.nombre if d.producto else None,
            cantidad=d.cantidad,
            precio_unitario=d.precio_unitario,
            subtotal=d.subtotal
        )
        for d in venta.detalles
    ]
    return VentaResponse(
        id=venta.id,
        cliente_id=venta.cliente_id,
        nombre_cliente=venta.cliente.nombre if venta.cliente else None,
        fecha=venta.fecha,
        total=venta.total,
        estado=venta.estado,
        notas=venta.notas,
        detalles=detalles
    )


@router.get("", response_model=List[VentaResponse])
def listar_ventas(
    cliente_id: Optional[int] = None,
    estado: Optional[EstadoVenta] = None,
    fecha_desde: Optional[datetime] = None,
    fecha_hasta: Optional[datetime] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    _user = Depends(get_current_user)
):
    q = db.query(Venta)
    if cliente_id:
        q = q.filter(Venta.cliente_id == cliente_id)
    if estado:
        q = q.filter(Venta.estado == estado)
    if fecha_desde:
        q = q.filter(Venta.fecha >= fecha_desde)
    if fecha_hasta:
        q = q.filter(Venta.fecha <= fecha_hasta)

    ventas = q.order_by(desc(Venta.fecha)).offset(skip).limit(limit).all()
    return [_build_venta_response(v) for v in ventas]


@router.get("/{venta_id}", response_model=VentaResponse)
def obtener_venta(
    venta_id: int,
    db: Session = Depends(get_db),
    _user = Depends(get_current_user)
):
    venta = db.query(Venta).filter(Venta.id == venta_id).first()
    if not venta:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    return _build_venta_response(venta)


@router.post("", response_model=VentaResponse, status_code=status.HTTP_201_CREATED)
def crear_venta(
    data: VentaCreate,
    db: Session = Depends(get_db),
    _user = Depends(get_current_user)
):
    """
    Registra una venta y descuenta el stock automáticamente.
    Si un producto no tiene stock suficiente, la venta es rechazada completa.
    """
    # Verificar cliente
    cliente = db.query(Cliente).filter(Cliente.id == data.cliente_id, Cliente.activo == True).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    # Verificar disponibilidad de TODOS los productos antes de crear nada
    productos_validados = []
    for item in data.detalles:
        producto = db.query(Producto).filter(Producto.id == item.producto_id, Producto.activo == True).first()
        if not producto:
            raise HTTPException(status_code=404, detail=f"Producto ID {item.producto_id} no encontrado")
        if producto.stock < item.cantidad:
            raise HTTPException(
                status_code=400,
                detail=f"Stock insuficiente para '{producto.nombre}'. Disponible: {producto.stock}, solicitado: {item.cantidad}"
            )
        productos_validados.append((producto, item))

    # Calcular total
    total = sum(item.precio_unitario * item.cantidad for _, item in productos_validados)

    # Crear venta
    venta = Venta(
        cliente_id=data.cliente_id,
        total=total,
        notas=data.notas,
        cotizacion_origen_id=data.cotizacion_origen_id,
        creado_por=data.creado_por,
        estado=EstadoVenta.confirmada
    )
    db.add(venta)
    db.flush()  # Para obtener el ID antes del commit

    # Crear detalles y descontar stock
    for producto, item in productos_validados:
        detalle = DetalleVenta(
            venta_id=venta.id,
            producto_id=item.producto_id,
            cantidad=item.cantidad,
            precio_unitario=item.precio_unitario,
            subtotal=item.precio_unitario * item.cantidad
        )
        db.add(detalle)
        producto.stock -= item.cantidad  # Descuento automático de stock

    db.commit()
    db.refresh(venta)
    return _build_venta_response(venta)


@router.patch("/{venta_id}/estado")
def cambiar_estado_venta(
    venta_id: int,
    estado: EstadoVenta,
    db: Session = Depends(get_db),
    _user = Depends(get_current_user)
):
    """Actualiza el estado de una venta (enviada, entregada, cancelada...)."""
    venta = db.query(Venta).filter(Venta.id == venta_id).first()
    if not venta:
        raise HTTPException(status_code=404, detail="Venta no encontrada")

    # Si se cancela, devolver stock
    if estado == EstadoVenta.cancelada and venta.estado != EstadoVenta.cancelada:
        for detalle in venta.detalles:
            detalle.producto.stock += detalle.cantidad

    venta.estado = estado
    db.commit()
    return {"mensaje": f"Venta {venta_id} actualizada a estado: {estado}"}
