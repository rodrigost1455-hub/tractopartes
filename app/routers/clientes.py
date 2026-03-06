"""
Router de Clientes — CRUD + historial de compras.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from typing import List, Optional
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import Cliente, Venta
from app.schemas.schemas import ClienteCreate, ClienteUpdate, ClienteResponse

router = APIRouter(prefix="/clientes", tags=["Clientes"])


@router.get("", response_model=List[ClienteResponse])
def listar_clientes(
    buscar: Optional[str] = Query(None, description="Nombre, empresa, teléfono o email"),
    ciudad: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    _user = Depends(get_current_user)
):
    """Lista clientes con estadísticas de compras."""
    q = db.query(Cliente).filter(Cliente.activo == True)

    if buscar:
        q = q.filter(or_(
            Cliente.nombre.ilike(f"%{buscar}%"),
            Cliente.empresa.ilike(f"%{buscar}%"),
            Cliente.telefono.ilike(f"%{buscar}%"),
            Cliente.email.ilike(f"%{buscar}%"),
        ))
    if ciudad:
        q = q.filter(Cliente.ciudad.ilike(f"%{ciudad}%"))

    clientes = q.offset(skip).limit(limit).all()

    # Agregar estadísticas de ventas
    result = []
    for c in clientes:
        stats = db.query(
            func.count(Venta.id).label("num_ventas"),
            func.coalesce(func.sum(Venta.total), 0).label("total_compras")
        ).filter(Venta.cliente_id == c.id).first()

        data = ClienteResponse.model_validate(c)
        data.num_ventas = stats.num_ventas
        data.total_compras = float(stats.total_compras)
        result.append(data)

    return result


@router.get("/{cliente_id}", response_model=ClienteResponse)
def obtener_cliente(
    cliente_id: int,
    db: Session = Depends(get_db),
    _user = Depends(get_current_user)
):
    cliente = db.query(Cliente).filter(
        Cliente.id == cliente_id,
        Cliente.activo == True
    ).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    stats = db.query(
        func.count(Venta.id).label("num_ventas"),
        func.coalesce(func.sum(Venta.total), 0).label("total_compras")
    ).filter(Venta.cliente_id == cliente_id).first()

    data = ClienteResponse.model_validate(cliente)
    data.num_ventas = stats.num_ventas
    data.total_compras = float(stats.total_compras)
    return data


@router.post("", response_model=ClienteResponse, status_code=status.HTTP_201_CREATED)
def crear_cliente(
    data: ClienteCreate,
    db: Session = Depends(get_db),
    _user = Depends(get_current_user)
):
    """Registra un nuevo cliente."""
    if data.email:
        if db.query(Cliente).filter(Cliente.email == data.email).first():
            raise HTTPException(status_code=400, detail="Ya existe un cliente con ese email")
    if data.telefono:
        if db.query(Cliente).filter(Cliente.telefono == data.telefono).first():
            raise HTTPException(status_code=400, detail="Ya existe un cliente con ese teléfono")

    cliente = Cliente(**data.model_dump())
    db.add(cliente)
    db.commit()
    db.refresh(cliente)

    result = ClienteResponse.model_validate(cliente)
    result.num_ventas = 0
    result.total_compras = 0.0
    return result


@router.patch("/{cliente_id}", response_model=ClienteResponse)
def actualizar_cliente(
    cliente_id: int,
    data: ClienteUpdate,
    db: Session = Depends(get_db),
    _user = Depends(get_current_user)
):
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(cliente, field, value)

    db.commit()
    db.refresh(cliente)
    return ClienteResponse.model_validate(cliente)


@router.get("/{cliente_id}/historial")
def historial_cliente(
    cliente_id: int,
    db: Session = Depends(get_db),
    _user = Depends(get_current_user)
):
    """
    Historial completo de compras de un cliente.
    Endpoint clave para el agente de IA — permite recordar qué compra cada cliente.
    """
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    ventas = cliente.ventas.order_by(Venta.fecha.desc()).limit(20).all()

    historial = []
    for v in ventas:
        historial.append({
            "venta_id": v.id,
            "fecha": v.fecha,
            "total": v.total,
            "estado": v.estado,
            "productos": [
                {
                    "nombre": d.producto.nombre,
                    "sku": d.producto.sku,
                    "cantidad": d.cantidad,
                    "precio": d.precio_unitario
                }
                for d in v.detalles
            ]
        })

    return {
        "cliente": {"id": cliente.id, "nombre": cliente.nombre, "empresa": cliente.empresa},
        "historial": historial
    }
