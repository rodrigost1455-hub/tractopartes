"""
Router de Cotizaciones.
El agente de IA generará cotizaciones automáticamente usando este endpoint.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from datetime import datetime, timedelta
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import Cotizacion, DetalleCotizacion, Producto, Cliente, EstadoCotizacion
from app.schemas.schemas import CotizacionCreate, CotizacionResponse, DetalleCotizacionResponse

router = APIRouter(prefix="/cotizaciones", tags=["Cotizaciones"])


def _build_cotizacion_response(cotizacion: Cotizacion) -> CotizacionResponse:
    detalles = [
        DetalleCotizacionResponse(
            id=d.id,
            producto_id=d.producto_id,
            nombre_producto=d.producto.nombre if d.producto else None,
            cantidad=d.cantidad,
            precio=d.precio,
            subtotal=d.subtotal
        )
        for d in cotizacion.detalles
    ]
    return CotizacionResponse(
        id=cotizacion.id,
        cliente_id=cotizacion.cliente_id,
        nombre_cliente=cotizacion.cliente.nombre if cotizacion.cliente else None,
        fecha=cotizacion.fecha,
        fecha_vencimiento=cotizacion.fecha_vencimiento,
        total=cotizacion.total,
        estado=cotizacion.estado,
        notas=cotizacion.notas,
        generada_por=cotizacion.generada_por,
        detalles=detalles
    )


@router.get("", response_model=List[CotizacionResponse])
def listar_cotizaciones(
    cliente_id: Optional[int] = None,
    estado: Optional[EstadoCotizacion] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    _user = Depends(get_current_user)
):
    q = db.query(Cotizacion)
    if cliente_id:
        q = q.filter(Cotizacion.cliente_id == cliente_id)
    if estado:
        q = q.filter(Cotizacion.estado == estado)
    return [_build_cotizacion_response(c) for c in q.order_by(desc(Cotizacion.fecha)).offset(skip).limit(limit).all()]


@router.get("/{cotizacion_id}", response_model=CotizacionResponse)
def obtener_cotizacion(
    cotizacion_id: int,
    db: Session = Depends(get_db),
    _user = Depends(get_current_user)
):
    cotizacion = db.query(Cotizacion).filter(Cotizacion.id == cotizacion_id).first()
    if not cotizacion:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")
    return _build_cotizacion_response(cotizacion)


@router.post("", response_model=CotizacionResponse, status_code=status.HTTP_201_CREATED)
def crear_cotizacion(
    data: CotizacionCreate,
    db: Session = Depends(get_db),
    _user = Depends(get_current_user)
):
    """
    Genera una cotización automáticamente.
    Si no se especifica precio en un ítem, usa el precio actual del producto.
    Endpoint diseñado para ser llamado por el agente de IA.
    """
    cliente = db.query(Cliente).filter(Cliente.id == data.cliente_id, Cliente.activo == True).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    # Verificar productos
    items_validados = []
    for item in data.detalles:
        producto = db.query(Producto).filter(Producto.id == item.producto_id, Producto.activo == True).first()
        if not producto:
            raise HTTPException(status_code=404, detail=f"Producto ID {item.producto_id} no encontrado")
        precio_final = item.precio if item.precio is not None else producto.precio
        items_validados.append((producto, item, precio_final))

    total = sum(precio * item.cantidad for _, item, precio in items_validados)

    cotizacion = Cotizacion(
        cliente_id=data.cliente_id,
        total=total,
        notas=data.notas,
        generada_por=data.generada_por,
        estado=EstadoCotizacion.borrador,
        fecha_vencimiento=datetime.utcnow() + timedelta(days=7)  # Válida 7 días
    )
    db.add(cotizacion)
    db.flush()

    for producto, item, precio in items_validados:
        detalle = DetalleCotizacion(
            cotizacion_id=cotizacion.id,
            producto_id=item.producto_id,
            cantidad=item.cantidad,
            precio=precio,
            subtotal=precio * item.cantidad
        )
        db.add(detalle)

    db.commit()
    db.refresh(cotizacion)
    return _build_cotizacion_response(cotizacion)


@router.patch("/{cotizacion_id}/estado")
def cambiar_estado_cotizacion(
    cotizacion_id: int,
    estado: EstadoCotizacion,
    db: Session = Depends(get_db),
    _user = Depends(get_current_user)
):
    cotizacion = db.query(Cotizacion).filter(Cotizacion.id == cotizacion_id).first()
    if not cotizacion:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")
    cotizacion.estado = estado
    db.commit()
    return {"mensaje": f"Cotización {cotizacion_id} actualizada a: {estado}"}


@router.post("/{cotizacion_id}/convertir-venta")
def convertir_a_venta(
    cotizacion_id: int,
    db: Session = Depends(get_db),
    _user = Depends(get_current_user)
):
    """Convierte una cotización aceptada en una venta real."""
    from app.models.models import Venta, DetalleVenta

    cotizacion = db.query(Cotizacion).filter(Cotizacion.id == cotizacion_id).first()
    if not cotizacion:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")
    if cotizacion.venta_generada:
        raise HTTPException(status_code=400, detail="Esta cotización ya fue convertida a venta")

    # Verificar stock antes de convertir
    for detalle in cotizacion.detalles:
        if detalle.producto.stock < detalle.cantidad:
            raise HTTPException(
                status_code=400,
                detail=f"Stock insuficiente para '{detalle.producto.nombre}'"
            )

    # Crear venta desde cotización
    venta = Venta(
        cliente_id=cotizacion.cliente_id,
        total=cotizacion.total,
        cotizacion_origen_id=cotizacion.id,
        creado_por="cotizacion"
    )
    db.add(venta)
    db.flush()

    for d in cotizacion.detalles:
        db.add(DetalleVenta(
            venta_id=venta.id,
            producto_id=d.producto_id,
            cantidad=d.cantidad,
            precio_unitario=d.precio,
            subtotal=d.subtotal
        ))
        d.producto.stock -= d.cantidad

    cotizacion.estado = EstadoCotizacion.aceptada
    db.commit()
    return {"mensaje": "Cotización convertida a venta", "venta_id": venta.id}
