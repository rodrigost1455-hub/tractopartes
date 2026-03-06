"""
Router de Analytics — Inteligencia de negocio.
Alimenta el dashboard y el agente de IA con datos para decisiones.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, text
from typing import List, Optional
from datetime import datetime, timedelta
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import (
    Venta, DetalleVenta, Producto, Cliente,
    EstadoVenta, CategoriaProducto
)
from app.schemas.schemas import TopProducto, TopCliente, ResumenInventario

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/top-productos", response_model=List[TopProducto])
def top_productos(
    dias: int = Query(30, description="Período en días"),
    limite: int = Query(10, description="Cuántos productos mostrar"),
    categoria: Optional[CategoriaProducto] = None,
    db: Session = Depends(get_db),
    _user = Depends(get_current_user)
):
    """Los productos más vendidos. Útil para publicar en Mercado Libre."""
    fecha_inicio = datetime.utcnow() - timedelta(days=dias)

    q = (
        db.query(
            Producto.id,
            Producto.nombre,
            Producto.sku,
            Producto.marca,
            func.sum(DetalleVenta.cantidad).label("total_vendido"),
            func.sum(DetalleVenta.subtotal).label("total_ingresos"),
            func.count(DetalleVenta.venta_id.distinct()).label("num_ventas")
        )
        .join(DetalleVenta, DetalleVenta.producto_id == Producto.id)
        .join(Venta, Venta.id == DetalleVenta.venta_id)
        .filter(
            Venta.estado != EstadoVenta.cancelada,
            Venta.fecha >= fecha_inicio
        )
        .group_by(Producto.id, Producto.nombre, Producto.sku, Producto.marca)
        .order_by(desc("total_vendido"))
    )

    if categoria:
        q = q.filter(Producto.categoria == categoria)

    rows = q.limit(limite).all()
    return [
        TopProducto(
            id=r.id, nombre=r.nombre, sku=r.sku, marca=r.marca,
            total_vendido=int(r.total_vendido or 0),
            total_ingresos=float(r.total_ingresos or 0),
            num_ventas=int(r.num_ventas or 0)
        )
        for r in rows
    ]


@router.get("/top-clientes", response_model=List[TopCliente])
def top_clientes(
    dias: int = Query(90, description="Período en días"),
    limite: int = Query(10),
    db: Session = Depends(get_db),
    _user = Depends(get_current_user)
):
    """Los clientes que más compran. El agente los priorizará para contacto."""
    fecha_inicio = datetime.utcnow() - timedelta(days=dias)

    rows = (
        db.query(
            Cliente.id,
            Cliente.nombre,
            Cliente.empresa,
            Cliente.telefono,
            func.sum(Venta.total).label("total_gastado"),
            func.count(Venta.id).label("num_ventas"),
            func.max(Venta.fecha).label("ultima_compra")
        )
        .join(Venta, Venta.cliente_id == Cliente.id)
        .filter(
            Venta.estado != EstadoVenta.cancelada,
            Venta.fecha >= fecha_inicio
        )
        .group_by(Cliente.id, Cliente.nombre, Cliente.empresa, Cliente.telefono)
        .order_by(desc("total_gastado"))
        .limit(limite)
        .all()
    )

    return [
        TopCliente(
            id=r.id, nombre=r.nombre, empresa=r.empresa, telefono=r.telefono,
            total_gastado=float(r.total_gastado or 0),
            num_ventas=int(r.num_ventas or 0),
            ultima_compra=r.ultima_compra
        )
        for r in rows
    ]


@router.get("/inventario/resumen", response_model=ResumenInventario)
def resumen_inventario(
    db: Session = Depends(get_db),
    _user = Depends(get_current_user)
):
    """Estado general del inventario."""
    total = db.query(func.count(Producto.id)).filter(Producto.activo == True).scalar()
    sin_stock = db.query(func.count(Producto.id)).filter(Producto.activo == True, Producto.stock == 0).scalar()
    stock_bajo = db.query(func.count(Producto.id)).filter(
        Producto.activo == True,
        Producto.stock > 0,
        Producto.stock <= Producto.stock_minimo
    ).scalar()
    valor = db.query(func.sum(Producto.precio * Producto.stock)).filter(Producto.activo == True).scalar()

    return ResumenInventario(
        total_productos=total or 0,
        productos_sin_stock=sin_stock or 0,
        productos_stock_bajo=stock_bajo or 0,
        valor_inventario=float(valor or 0)
    )


@router.get("/inventario/rotacion")
def rotacion_inventario(
    dias: int = Query(30),
    db: Session = Depends(get_db),
    _user = Depends(get_current_user)
):
    """Qué inventario rota más rápido (ventas / stock actual)."""
    fecha_inicio = datetime.utcnow() - timedelta(days=dias)

    rows = (
        db.query(
            Producto.id,
            Producto.nombre,
            Producto.sku,
            Producto.stock.label("stock_actual"),
            func.coalesce(func.sum(DetalleVenta.cantidad), 0).label("vendido_periodo")
        )
        .outerjoin(DetalleVenta, DetalleVenta.producto_id == Producto.id)
        .outerjoin(Venta, (Venta.id == DetalleVenta.venta_id) & (Venta.fecha >= fecha_inicio))
        .filter(Producto.activo == True, Producto.stock > 0)
        .group_by(Producto.id, Producto.nombre, Producto.sku, Producto.stock)
        .order_by(desc("vendido_periodo"))
        .limit(20)
        .all()
    )

    return [
        {
            "id": r.id,
            "nombre": r.nombre,
            "sku": r.sku,
            "stock_actual": r.stock_actual,
            "vendido_en_periodo": int(r.vendido_periodo),
            "tasa_rotacion": round(int(r.vendido_periodo) / r.stock_actual, 2) if r.stock_actual > 0 else 0
        }
        for r in rows
    ]


@router.get("/productos-juntos")
def productos_comprados_juntos(
    limite: int = Query(10),
    db: Session = Depends(get_db),
    _user = Depends(get_current_user)
):
    """
    Qué productos se compran juntos con frecuencia.
    Clave para que el agente haga sugerencias de cross-selling.
    """
    sql = text("""
        SELECT
            p1.nombre AS producto_a,
            p2.nombre AS producto_b,
            COUNT(*) AS veces_juntos
        FROM detalles_venta dv1
        JOIN detalles_venta dv2 ON dv1.venta_id = dv2.venta_id AND dv1.producto_id < dv2.producto_id
        JOIN productos p1 ON p1.id = dv1.producto_id
        JOIN productos p2 ON p2.id = dv2.producto_id
        GROUP BY p1.nombre, p2.nombre
        ORDER BY veces_juntos DESC
        LIMIT :limite
    """)
    rows = db.execute(sql, {"limite": limite}).fetchall()
    return [{"producto_a": r[0], "producto_b": r[1], "veces_juntos": r[2]} for r in rows]


@router.get("/ventas/por-mes")
def ventas_por_mes(
    meses: int = Query(6),
    db: Session = Depends(get_db),
    _user = Depends(get_current_user)
):
    """Tendencia de ventas mensual para el dashboard."""
    sql = text("""
        SELECT
            TO_CHAR(fecha, 'YYYY-MM') AS mes,
            COUNT(id) AS num_ventas,
            ROUND(SUM(total)::numeric, 2) AS total_ingresos
        FROM ventas
        WHERE estado != 'cancelada'
          AND fecha >= NOW() - INTERVAL ':meses months'
        GROUP BY mes
        ORDER BY mes ASC
    """)
    # Usamos query builder para mayor compatibilidad
    fecha_inicio = datetime.utcnow() - timedelta(days=30 * meses)
    rows = (
        db.query(
            func.to_char(Venta.fecha, "YYYY-MM").label("mes"),
            func.count(Venta.id).label("num_ventas"),
            func.round(func.sum(Venta.total), 2).label("total_ingresos")
        )
        .filter(Venta.estado != EstadoVenta.cancelada, Venta.fecha >= fecha_inicio)
        .group_by("mes")
        .order_by("mes")
        .all()
    )
    return [{"mes": r.mes, "num_ventas": r.num_ventas, "total_ingresos": float(r.total_ingresos or 0)} for r in rows]


@router.get("/clientes/sin-compras-recientes")
def clientes_inactivos(
    dias_inactivo: int = Query(60, description="Días sin comprar para considerarlo inactivo"),
    limite: int = 20,
    db: Session = Depends(get_db),
    _user = Depends(get_current_user)
):
    """
    Clientes que no han comprado en X días.
    El agente de IA los contactará automáticamente en Fase 2.
    """
    fecha_corte = datetime.utcnow() - timedelta(days=dias_inactivo)

    subq = (
        db.query(Venta.cliente_id, func.max(Venta.fecha).label("ultima_compra"))
        .filter(Venta.estado != EstadoVenta.cancelada)
        .group_by(Venta.cliente_id)
        .subquery()
    )

    rows = (
        db.query(Cliente, subq.c.ultima_compra)
        .join(subq, subq.c.cliente_id == Cliente.id)
        .filter(subq.c.ultima_compra <= fecha_corte, Cliente.activo == True)
        .order_by(subq.c.ultima_compra.asc())
        .limit(limite)
        .all()
    )

    return [
        {
            "id": c.id,
            "nombre": c.nombre,
            "empresa": c.empresa,
            "telefono": c.telefono,
            "canal_preferido": c.canal_preferido,
            "ultima_compra": ultima,
            "dias_inactivo": (datetime.utcnow() - ultima).days if ultima else None
        }
        for c, ultima in rows
    ]
