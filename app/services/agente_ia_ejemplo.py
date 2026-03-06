"""
FASE 2 — Ejemplo de integración del Agente de IA con la API.
Este archivo muestra cómo el agente conectará con el sistema.
No se ejecuta en Fase 1 — es una guía para el desarrollo futuro.

Requiere: openai, langchain, requests
"""

import os
import requests
from datetime import datetime, timedelta

TRACTOPARTES_API = os.getenv("TRACTOPARTES_API_URL", "http://localhost:8000")
_token = None
_token_expiry = None


# ─── Cliente HTTP para la API ─────────────────────────────────────────────────

def get_token():
    """Obtiene y cachea el JWT del agente."""
    global _token, _token_expiry
    if _token and _token_expiry and datetime.utcnow() < _token_expiry:
        return _token

    response = requests.post(f"{TRACTOPARTES_API}/auth/login", json={
        "username": "agente_ia",
        "password": os.getenv("AGENTE_IA_PASSWORD")
    })
    data = response.json()
    _token = data["access_token"]
    _token_expiry = datetime.utcnow() + timedelta(hours=23)
    return _token


def api(method: str, endpoint: str, **kwargs):
    """Wrapper para todas las llamadas a la API con JWT automático."""
    headers = {"Authorization": f"Bearer {get_token()}"}
    url = f"{TRACTOPARTES_API}{endpoint}"
    return requests.request(method, url, headers=headers, **kwargs).json()


# ─── Herramientas del Agente ──────────────────────────────────────────────────

def buscar_producto(query: str) -> list:
    """El agente busca productos disponibles."""
    return api("GET", f"/productos?buscar={query}&solo_disponibles=true")


def ver_historial_cliente(cliente_id: int) -> dict:
    """Qué ha comprado este cliente antes."""
    return api("GET", f"/clientes/{cliente_id}/historial")


def generar_cotizacion(cliente_id: int, productos: list) -> dict:
    """
    Genera una cotización automáticamente.
    productos = [{"producto_id": 1, "cantidad": 2}, ...]
    """
    return api("POST", "/cotizaciones", json={
        "cliente_id": cliente_id,
        "detalles": productos,
        "generada_por": "agente_ia"
    })


def confirmar_venta(cotizacion_id: int) -> dict:
    """Convierte la cotización en venta cuando el cliente acepta."""
    return api("POST", f"/cotizaciones/{cotizacion_id}/convertir-venta")


def obtener_clientes_inactivos(dias: int = 60) -> list:
    """Clientes que no compran hace X días — para proactividad del agente."""
    return api("GET", f"/analytics/clientes/sin-compras-recientes?dias_inactivo={dias}")


def productos_sugeridos_para(producto_id: int) -> list:
    """Qué otros productos se compran junto con este."""
    todos = api("GET", "/analytics/productos-juntos?limite=50")
    # Filtrar los que incluyen este producto
    return [p for p in todos if str(producto_id) in str(p)]


# ─── Flujo Completo de Ejemplo ────────────────────────────────────────────────

def flujo_cotizacion_whatsapp(
    mensaje_cliente: str,
    telefono_cliente: str
) -> str:
    """
    Simula el flujo completo del agente cuando recibe un mensaje de WhatsApp.
    
    Ejemplo:
    mensaje = "Hola, necesito 4 filtros de aceite para mi Kenworth T680"
    → El agente busca, cotiza y responde.
    """

    # 1. Buscar cliente por teléfono
    clientes = api("GET", f"/clientes?buscar={telefono_cliente}")
    if not clientes:
        return "Hola, no encontré tu número registrado. ¿Me das tu nombre y empresa?"

    cliente = clientes[0]
    cliente_id = cliente["id"]

    # 2. Buscar historial (memoria del cliente)
    historial = ver_historial_cliente(cliente_id)
    productos_frecuentes = []
    if historial["historial"]:
        # Extraer SKUs que más compra
        for compra in historial["historial"][:5]:
            for p in compra["productos"]:
                productos_frecuentes.append(p["nombre"])

    # 3. Buscar producto mencionado en el mensaje
    # (En producción: LLM extrae la intención y el producto del mensaje)
    productos_encontrados = buscar_producto("filtro aceite kenworth")

    if not productos_encontrados:
        return "Lo siento, no tenemos ese producto en inventario. ¿Te puedo ayudar con otro?"

    # 4. Generar cotización automáticamente
    cotizacion = generar_cotizacion(
        cliente_id=cliente_id,
        productos=[{"producto_id": productos_encontrados[0]["id"], "cantidad": 4}]
    )

    # 5. Formatear respuesta para WhatsApp
    respuesta = f"""
✅ *Cotización #{cotizacion['id']}* para {cliente['nombre']}

📦 Productos:
"""
    for detalle in cotizacion["detalles"]:
        respuesta += f"  • {detalle['nombre_producto']} x{detalle['cantidad']} — ${detalle['subtotal']:,.2f}\n"

    respuesta += f"""
💰 *Total: ${cotizacion['total']:,.2f} MXN*
📅 Válida hasta: {cotizacion['fecha_vencimiento'][:10] if cotizacion.get('fecha_vencimiento') else 'N/A'}

¿Confirmas el pedido? Responde *SÍ* para proceder.
"""
    return respuesta.strip()


# ─── Ejemplo de uso ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=== SIMULACIÓN DEL AGENTE DE IA ===\n")

    # Simular mensaje de WhatsApp
    respuesta = flujo_cotizacion_whatsapp(
        mensaje_cliente="Necesito 4 filtros de aceite para mi Kenworth T680",
        telefono_cliente="+52 55 1234 5678"
    )
    print("RESPUESTA DEL AGENTE:")
    print(respuesta)

    print("\n=== CLIENTES INACTIVOS (para contactar proactivamente) ===")
    inactivos = obtener_clientes_inactivos(dias=60)
    for c in inactivos[:3]:
        print(f"  • {c['nombre']} ({c['empresa']}) — {c['dias_inactivo']} días sin comprar")
        print(f"    Tel: {c['telefono']} | Canal: {c['canal_preferido']}")
