# 🚛 Tractopartes API

Sistema backend para gestión de ventas e inventario de refacciones para tractocamiones.
Construido con FastAPI + PostgreSQL. Diseñado para escalar con un **agente de IA** en WhatsApp y Web.

---

## 🏗️ Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CLIENTES FINALES                            │
│         WhatsApp Bot          │         Panel Web / App             │
└──────────────┬────────────────┴──────────────┬──────────────────────┘
               │                               │
               ▼                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     AGENTE DE IA (Fase 2)                           │
│   LangChain / OpenAI   │   Memoria de cliente   │   Tool calls      │
└──────────────────────────────────┬──────────────────────────────────┘
                                   │ HTTP (JWT)
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      TRACTOPARTES API                               │
│                     FastAPI  •  Python                              │
│                                                                     │
│  /productos   /clientes   /ventas   /cotizaciones   /analytics      │
└──────────────────────────────────┬──────────────────────────────────┘
                                   │ SQLAlchemy ORM
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   PostgreSQL (Railway)                              │
│  clientes │ productos │ ventas │ detalles │ cotizaciones │ agente   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🗄️ Diagrama de Base de Datos

```
CLIENTES ──────────────────────────────────────────────────────┐
│ id, nombre, empresa, telefono, email, ciudad                  │
│ canal_preferido, preferencias (JSON)                          │
│ ultimo_contacto, fecha_registro                               │
└──┬──────────────────────────────────────────┐                 │
   │ 1:N                                      │ 1:N             │
   ▼                                          ▼                 │
VENTAS                                   COTIZACIONES ──────────┘
│ id, cliente_id, total, estado          │ id, cliente_id, total, estado
│ creado_por, cotizacion_origen_id       │ generada_por, fecha_vencimiento
└────────────┬───────────────────        └──────────────┬──────────────
             │ 1:N                                      │ 1:N
             ▼                                          ▼
    DETALLES_VENTA                          DETALLES_COTIZACION
    │ venta_id, producto_id                 │ cotizacion_id, producto_id
    │ cantidad, precio_unitario             │ cantidad, precio
    └──────────┬──────────                  └─────────────┬────────────
               │ N:1                                      │ N:1
               └─────────────────┬────────────────────────┘
                                  ▼
                             PRODUCTOS
                             │ id, nombre, sku, marca
                             │ categoria, precio, costo
                             │ stock, stock_minimo
                             │ ubicacion_bodega, modelo_compatible
                             │ tags (JSON), publicado_ml
```

---

## 📁 Estructura del Proyecto

```
tractopartes/
├── app/
│   ├── main.py                  ← Punto de entrada FastAPI
│   ├── core/
│   │   ├── database.py          ← Conexión PostgreSQL
│   │   └── security.py          ← JWT + autenticación
│   ├── models/
│   │   └── models.py            ← Modelos SQLAlchemy (tablas)
│   ├── schemas/
│   │   └── schemas.py           ← Schemas Pydantic (validación)
│   ├── routers/
│   │   ├── auth.py              ← Login / token
│   │   ├── productos.py         ← CRUD inventario
│   │   ├── clientes.py          ← CRUD clientes + historial
│   │   ├── ventas.py            ← Registro de ventas
│   │   ├── cotizaciones.py      ← Generación de cotizaciones
│   │   └── analytics.py         ← Reportes e inteligencia de negocio
│   └── services/                ← (Fase 2) lógica del agente IA
├── scripts/
│   └── schema.sql               ← SQL puro para PostgreSQL
├── requirements.txt
├── railway.toml
├── Procfile
└── .env.example
```

---

## 📋 Endpoints de la API

### 🔐 Autenticación
| Método | Endpoint       | Descripción              |
|--------|---------------|--------------------------|
| POST   | /auth/login   | Obtener token JWT        |
| GET    | /auth/me      | Info del usuario actual  |

### 📦 Productos
| Método | Endpoint                    | Descripción                        |
|--------|----------------------------|------------------------------------|
| GET    | /productos                  | Listar con filtros (búsqueda, cat) |
| GET    | /productos/{id}             | Detalle completo                   |
| GET    | /productos/sku/{sku}        | Búsqueda rápida por SKU            |
| POST   | /productos                  | Crear producto                     |
| PATCH  | /productos/{id}             | Actualizar campos                  |
| PATCH  | /productos/{id}/stock       | Ajustar inventario                 |
| DELETE | /productos/{id}             | Desactivar producto                |

### 👥 Clientes
| Método | Endpoint                       | Descripción                  |
|--------|-------------------------------|------------------------------|
| GET    | /clientes                      | Listar con estadísticas       |
| GET    | /clientes/{id}                 | Detalle con totales           |
| GET    | /clientes/{id}/historial       | Historial de compras          |
| POST   | /clientes                      | Registrar cliente             |
| PATCH  | /clientes/{id}                 | Actualizar datos              |

### 💰 Ventas
| Método | Endpoint                        | Descripción                       |
|--------|--------------------------------|-----------------------------------|
| GET    | /ventas                         | Listar ventas con filtros         |
| GET    | /ventas/{id}                    | Detalle de venta                  |
| POST   | /ventas                         | Registrar venta (descuenta stock) |
| PATCH  | /ventas/{id}/estado             | Cambiar estado                    |

### 📄 Cotizaciones
| Método | Endpoint                                  | Descripción                    |
|--------|-----------------------------------------|--------------------------------|
| GET    | /cotizaciones                             | Listar cotizaciones            |
| GET    | /cotizaciones/{id}                        | Detalle                        |
| POST   | /cotizaciones                             | Generar cotización             |
| PATCH  | /cotizaciones/{id}/estado                 | Cambiar estado                 |
| POST   | /cotizaciones/{id}/convertir-venta        | Convertir a venta real         |

### 📊 Analytics
| Método | Endpoint                                  | Descripción                          |
|--------|------------------------------------------|--------------------------------------|
| GET    | /analytics/top-productos                  | Más vendidos (por período)           |
| GET    | /analytics/top-clientes                   | Clientes que más compran             |
| GET    | /analytics/inventario/resumen             | Estado del inventario                |
| GET    | /analytics/inventario/rotacion            | Qué productos rotan más rápido       |
| GET    | /analytics/productos-juntos               | Cross-selling: qué se vende junto    |
| GET    | /analytics/ventas/por-mes                 | Tendencia mensual de ventas          |
| GET    | /analytics/clientes/sin-compras-recientes | Clientes inactivos (para contactar)  |

---

## 🚀 Despliegue en Railway — Paso a Paso

### Paso 1: Preparar el repositorio

```bash
# En tu computadora, abrir terminal
cd tractopartes
git init
git add .
git commit -m "Initial commit: Tractopartes API"
```

### Paso 2: Subir a GitHub

```bash
# Crear repositorio en github.com, luego:
git remote add origin https://github.com/tu-usuario/tractopartes-api.git
git push -u origin main
```

### Paso 3: Crear proyecto en Railway

1. Ir a [railway.app](https://railway.app) → Crear cuenta
2. Click **"New Project"** → **"Deploy from GitHub repo"**
3. Seleccionar tu repositorio `tractopartes-api`
4. Railway detectará automáticamente que es Python/FastAPI

### Paso 4: Agregar PostgreSQL

1. En tu proyecto Railway, click **"+ New"** → **"Database"** → **"PostgreSQL"**
2. Railway crea la base de datos y agrega automáticamente `DATABASE_URL`

### Paso 5: Configurar variables de entorno

En Railway → tu servicio → **"Variables"**, agregar:

```
SECRET_KEY=genera-uno-con: python -c "import secrets; print(secrets.token_hex(32))"
ADMIN_PASSWORD=tu-password-seguro
VENDEDOR_PASSWORD=otro-password
AGENTE_IA_PASSWORD=password-para-el-agente
ALLOWED_ORIGINS=https://tu-frontend.com
```

### Paso 6: Desplegar

Railway desplegará automáticamente. En el panel verás los logs en tiempo real.

Tu API estará disponible en: `https://tu-proyecto.railway.app`

Documentación interactiva: `https://tu-proyecto.railway.app/docs`

---

## 💻 Desarrollo Local

```bash
# 1. Clonar y entrar al proyecto
cd tractopartes

# 2. Crear entorno virtual
python -m venv venv
source venv/bin/activate   # Mac/Linux
# venv\Scripts\activate    # Windows

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus datos de PostgreSQL local

# 5. Iniciar servidor de desarrollo
uvicorn app.main:app --reload --port 8000

# API disponible en: http://localhost:8000
# Documentación:    http://localhost:8000/docs
```

### Usando el schema SQL directamente (alternativa)

```bash
# Si prefieres crear las tablas con SQL puro:
psql -h localhost -U postgres -d tractopartes -f scripts/schema.sql
```

---

## 🔑 Cómo usar la API

### 1. Obtener token
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'

# Respuesta:
# {"access_token": "eyJ...", "token_type": "bearer"}
```

### 2. Consultar inventario
```bash
curl http://localhost:8000/productos?buscar=filtro&solo_disponibles=true \
  -H "Authorization: Bearer eyJ..."
```

### 3. Registrar cliente
```bash
curl -X POST http://localhost:8000/clientes \
  -H "Authorization: Bearer eyJ..." \
  -H "Content-Type: application/json" \
  -d '{
    "nombre": "Pedro Castillo",
    "empresa": "Transportes PC",
    "telefono": "+52 55 9999 8888",
    "ciudad": "Guadalajara"
  }'
```

### 4. Generar cotización
```bash
curl -X POST http://localhost:8000/cotizaciones \
  -H "Authorization: Bearer eyJ..." \
  -H "Content-Type: application/json" \
  -d '{
    "cliente_id": 1,
    "generada_por": "vendedor",
    "detalles": [
      {"producto_id": 1, "cantidad": 3},
      {"producto_id": 7, "cantidad": 10}
    ]
  }'
```

---

## 🤖 Integración con Agente de IA (Fase 2)

El sistema ya está preparado. El agente necesitará:

### Credenciales
El agente usará el usuario `agente_ia` creado en `security.py`.
Obtiene su token con `POST /auth/login` y lo renueva cada 24 horas.

### Flujo típico del agente

```python
# Pseudocódigo de lo que hará el agente

# 1. Cliente escribe en WhatsApp: "Necesito filtros para mi Kenworth T680"
# 2. Agente consulta inventario:
GET /productos?buscar=filtro&marca=kenworth

# 3. Encuentra productos disponibles, genera cotización:
POST /cotizaciones
{
  "cliente_id": 42,
  "generada_por": "agente_ia",
  "detalles": [{"producto_id": 1, "cantidad": 2}]
}

# 4. Envía la cotización por WhatsApp al cliente
# 5. Cliente acepta → agente convierte a venta:
POST /cotizaciones/123/convertir-venta

# 6. Registra la interacción:
POST /registro_agente  (tabla preparada en la DB)
```

### Endpoints más usados por el agente

```python
ENDPOINTS_AGENTE = {
    "buscar_producto":      "GET  /productos?buscar={query}",
    "verificar_stock":      "GET  /productos/sku/{sku}",
    "historial_cliente":    "GET  /clientes/{id}/historial",
    "generar_cotizacion":   "POST /cotizaciones",
    "confirmar_venta":      "POST /cotizaciones/{id}/convertir-venta",
    "clientes_inactivos":   "GET  /analytics/clientes/sin-compras-recientes",
    "productos_sugeridos":  "GET  /analytics/productos-juntos",
}
```

### Variables de entorno que necesitará el agente en Fase 2

```bash
OPENAI_API_KEY=sk-...
TRACTOPARTES_API_URL=https://tu-proyecto.railway.app
TRACTOPARTES_AGENTE_TOKEN=  # Se obtiene con login
WHATSAPP_TOKEN=...
WHATSAPP_PHONE_ID=...
```

---

## 📈 Queries de Analytics para Mercado Libre

Para decidir qué publicar en Mercado Libre:

```bash
# Top 10 productos más vendidos en los últimos 90 días
GET /analytics/top-productos?dias=90&limite=10

# Productos que rotan más rápido (demanda alta, stock se agota pronto)
GET /analytics/inventario/rotacion?dias=30

# Productos frecuentemente comprados juntos (para crear kits)
GET /analytics/productos-juntos?limite=20
```

---

## 🔒 Seguridad en Producción

- [ ] Cambiar todas las contraseñas del `.env`
- [ ] Generar `SECRET_KEY` con `python -c "import secrets; print(secrets.token_hex(32))"`
- [ ] Configurar `ALLOWED_ORIGINS` con tu dominio exacto (no `*`)
- [ ] Activar SSL en Railway (automático con el dominio de Railway)
- [ ] En Fase 2: migrar usuarios a tabla en base de datos con roles granulares
