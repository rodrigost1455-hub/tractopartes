"""
Router de Productos — CRUD completo + búsqueda.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import List, Optional
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import Producto, CategoriaProducto
from app.schemas.schemas import ProductoCreate, ProductoUpdate, ProductoResponse, ProductoResumen

router = APIRouter(prefix="/productos", tags=["Productos"])


@router.get("", response_model=List[ProductoResumen])
def listar_productos(
    buscar: Optional[str] = Query(None, description="Busca en nombre, SKU o marca"),
    categoria: Optional[CategoriaProducto] = None,
    marca: Optional[str] = None,
    solo_disponibles: bool = False,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    _user = Depends(get_current_user)
):
    """Lista productos con filtros. Endpoint principal para el agente de IA."""
    q = db.query(Producto).filter(Producto.activo == True)

    if buscar:
        q = q.filter(or_(
            Producto.nombre.ilike(f"%{buscar}%"),
            Producto.sku.ilike(f"%{buscar}%"),
            Producto.marca.ilike(f"%{buscar}%"),
            Producto.modelo_compatible.ilike(f"%{buscar}%")
        ))
    if categoria:
        q = q.filter(Producto.categoria == categoria)
    if marca:
        q = q.filter(Producto.marca.ilike(f"%{marca}%"))
    if solo_disponibles:
        q = q.filter(Producto.stock > 0)

    productos = q.offset(skip).limit(limit).all()

    return [
        ProductoResumen(
            id=p.id,
            nombre=p.nombre,
            sku=p.sku,
            marca=p.marca,
            precio=p.precio,
            stock=p.stock,
            disponible=p.stock > 0
        )
        for p in productos
    ]


@router.get("/{producto_id}", response_model=ProductoResponse)
def obtener_producto(
    producto_id: int,
    db: Session = Depends(get_db),
    _user = Depends(get_current_user)
):
    """Detalle completo de un producto."""
    producto = db.query(Producto).filter(
        Producto.id == producto_id,
        Producto.activo == True
    ).first()

    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return producto


@router.post("", response_model=ProductoResponse, status_code=status.HTTP_201_CREATED)
def crear_producto(
    data: ProductoCreate,
    db: Session = Depends(get_db),
    _user = Depends(get_current_user)
):
    """Crea un nuevo producto en inventario."""
    existente = db.query(Producto).filter(Producto.sku == data.sku).first()
    if existente:
        raise HTTPException(status_code=400, detail=f"Ya existe un producto con SKU: {data.sku}")

    producto = Producto(**data.model_dump())
    db.add(producto)
    db.commit()
    db.refresh(producto)
    return producto


@router.patch("/{producto_id}", response_model=ProductoResponse)
def actualizar_producto(
    producto_id: int,
    data: ProductoUpdate,
    db: Session = Depends(get_db),
    _user = Depends(get_current_user)
):
    """Actualiza campos específicos de un producto (ej: stock, precio)."""
    producto = db.query(Producto).filter(Producto.id == producto_id).first()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(producto, field, value)

    db.commit()
    db.refresh(producto)
    return producto


@router.delete("/{producto_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_producto(
    producto_id: int,
    db: Session = Depends(get_db),
    _user = Depends(get_current_user)
):
    """Soft-delete: marca el producto como inactivo."""
    producto = db.query(Producto).filter(Producto.id == producto_id).first()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    producto.activo = False
    db.commit()


@router.get("/sku/{sku}", response_model=ProductoResumen)
def buscar_por_sku(
    sku: str,
    db: Session = Depends(get_db),
    _user = Depends(get_current_user)
):
    """Búsqueda rápida por SKU — usada por el agente de IA."""
    producto = db.query(Producto).filter(
        Producto.sku == sku,
        Producto.activo == True
    ).first()
    if not producto:
        raise HTTPException(status_code=404, detail=f"Producto con SKU '{sku}' no encontrado")

    return ProductoResumen(
        id=producto.id,
        nombre=producto.nombre,
        sku=producto.sku,
        marca=producto.marca,
        precio=producto.precio,
        stock=producto.stock,
        disponible=producto.stock > 0
    )


@router.patch("/{producto_id}/stock", response_model=ProductoResponse)
def ajustar_stock(
    producto_id: int,
    cantidad: int = Query(..., description="Positivo para entrada, negativo para salida"),
    db: Session = Depends(get_db),
    _user = Depends(get_current_user)
):
    """Ajuste manual de inventario."""
    producto = db.query(Producto).filter(Producto.id == producto_id).first()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    nuevo_stock = producto.stock + cantidad
    if nuevo_stock < 0:
        raise HTTPException(status_code=400, detail="Stock insuficiente para esta operación")

    producto.stock = nuevo_stock
    db.commit()
    db.refresh(producto)
    return producto
