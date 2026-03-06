-- ============================================================
-- TRACTOPARTES — Esquema PostgreSQL completo
-- Ejecutar en Railway o PostgreSQL local
-- ============================================================

-- Extensiones útiles
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ─── ENUMS ────────────────────────────────────────────────────────────────────

CREATE TYPE estado_venta AS ENUM (
    'pendiente', 'confirmada', 'enviada', 'entregada', 'cancelada'
);

CREATE TYPE estado_cotizacion AS ENUM (
    'borrador', 'enviada', 'aceptada', 'rechazada', 'vencida'
);

CREATE TYPE categoria_producto AS ENUM (
    'motor', 'transmision', 'frenos', 'suspension', 'electrico',
    'carroceria', 'hidraulico', 'escape', 'filtros', 'otros'
);

-- ─── CLIENTES ─────────────────────────────────────────────────────────────────

CREATE TABLE clientes (
    id                  SERIAL PRIMARY KEY,
    nombre              VARCHAR(200) NOT NULL,
    empresa             VARCHAR(200),
    telefono            VARCHAR(20) UNIQUE,
    email               VARCHAR(200) UNIQUE,
    ciudad              VARCHAR(100),
    notas               TEXT,
    activo              BOOLEAN DEFAULT TRUE,
    preferencias        TEXT,                          -- JSON: productos frecuentes, marcas, etc.
    ultimo_contacto     TIMESTAMPTZ,
    canal_preferido     VARCHAR(50) DEFAULT 'whatsapp', -- para el agente de IA
    fecha_registro      TIMESTAMPTZ DEFAULT NOW(),
    fecha_actualizacion TIMESTAMPTZ
);

CREATE INDEX ix_clientes_telefono ON clientes(telefono);
CREATE INDEX ix_clientes_email    ON clientes(email);

-- ─── PRODUCTOS ────────────────────────────────────────────────────────────────

CREATE TABLE productos (
    id                  SERIAL PRIMARY KEY,
    nombre              VARCHAR(300) NOT NULL,
    descripcion         TEXT,
    marca               VARCHAR(100),
    modelo_compatible   VARCHAR(300),   -- "Kenworth T680, Peterbilt 579"
    categoria           categoria_producto,
    sku                 VARCHAR(100) UNIQUE NOT NULL,
    precio              NUMERIC(12,2) NOT NULL,
    costo               NUMERIC(12,2),
    stock               INTEGER DEFAULT 0,
    stock_minimo        INTEGER DEFAULT 5,
    ubicacion_bodega    VARCHAR(100),   -- "Estante A - Nivel 3"
    activo              BOOLEAN DEFAULT TRUE,
    tags                TEXT,          -- JSON array: ["filtro","kenworth"]
    imagen_url          VARCHAR(500),
    publicado_ml        BOOLEAN DEFAULT FALSE,
    ml_item_id          VARCHAR(100),  -- ID en Mercado Libre
    fecha_creacion      TIMESTAMPTZ DEFAULT NOW(),
    fecha_actualizacion TIMESTAMPTZ
);

CREATE INDEX ix_productos_sku              ON productos(sku);
CREATE INDEX ix_productos_marca            ON productos(marca);
CREATE INDEX ix_productos_categoria        ON productos(categoria);
CREATE INDEX ix_productos_marca_categoria  ON productos(marca, categoria);

-- ─── COTIZACIONES ─────────────────────────────────────────────────────────────

CREATE TABLE cotizaciones (
    id                  SERIAL PRIMARY KEY,
    cliente_id          INTEGER NOT NULL REFERENCES clientes(id),
    fecha               TIMESTAMPTZ DEFAULT NOW(),
    fecha_vencimiento   TIMESTAMPTZ,
    total               NUMERIC(12,2) NOT NULL DEFAULT 0,
    estado              estado_cotizacion DEFAULT 'borrador',
    notas               TEXT,
    generada_por        VARCHAR(100) DEFAULT 'sistema'  -- 'agente_ia' | 'vendedor'
);

CREATE INDEX ix_cotizaciones_cliente_id ON cotizaciones(cliente_id);
CREATE INDEX ix_cotizaciones_fecha      ON cotizaciones(fecha);
CREATE INDEX ix_cotizaciones_estado     ON cotizaciones(estado);

-- ─── DETALLES COTIZACIÓN ──────────────────────────────────────────────────────

CREATE TABLE detalles_cotizacion (
    id              SERIAL PRIMARY KEY,
    cotizacion_id   INTEGER NOT NULL REFERENCES cotizaciones(id) ON DELETE CASCADE,
    producto_id     INTEGER NOT NULL REFERENCES productos(id),
    cantidad        INTEGER NOT NULL,
    precio          NUMERIC(12,2) NOT NULL,
    subtotal        NUMERIC(12,2) NOT NULL
);

CREATE INDEX ix_det_cotizacion_cotizacion_id ON detalles_cotizacion(cotizacion_id);
CREATE INDEX ix_det_cotizacion_producto_id   ON detalles_cotizacion(producto_id);

-- ─── VENTAS ───────────────────────────────────────────────────────────────────

CREATE TABLE ventas (
    id                      SERIAL PRIMARY KEY,
    cliente_id              INTEGER NOT NULL REFERENCES clientes(id),
    cotizacion_origen_id    INTEGER REFERENCES cotizaciones(id),
    fecha                   TIMESTAMPTZ DEFAULT NOW(),
    total                   NUMERIC(12,2) NOT NULL,
    estado                  estado_venta DEFAULT 'pendiente',
    notas                   TEXT,
    creado_por              VARCHAR(100) DEFAULT 'sistema'  -- 'agente_ia' | 'vendedor'
);

CREATE INDEX ix_ventas_cliente_id ON ventas(cliente_id);
CREATE INDEX ix_ventas_fecha      ON ventas(fecha);
CREATE INDEX ix_ventas_estado     ON ventas(estado);

-- ─── DETALLES VENTA ───────────────────────────────────────────────────────────

CREATE TABLE detalles_venta (
    id              SERIAL PRIMARY KEY,
    venta_id        INTEGER NOT NULL REFERENCES ventas(id) ON DELETE CASCADE,
    producto_id     INTEGER NOT NULL REFERENCES productos(id),
    cantidad        INTEGER NOT NULL,
    precio_unitario NUMERIC(12,2) NOT NULL,
    subtotal        NUMERIC(12,2) NOT NULL
);

CREATE INDEX ix_det_venta_venta_id    ON detalles_venta(venta_id);
CREATE INDEX ix_det_venta_producto_id ON detalles_venta(producto_id);

-- ─── REGISTRO AGENTE IA (FASE 2) ─────────────────────────────────────────────

CREATE TABLE registro_agente (
    id              SERIAL PRIMARY KEY,
    cliente_id      INTEGER REFERENCES clientes(id),
    canal           VARCHAR(50),         -- 'whatsapp' | 'web'
    sesion_id       VARCHAR(200),
    mensaje_usuario TEXT,
    respuesta_agente TEXT,
    intencion       VARCHAR(100),        -- 'consulta_inventario' | 'cotizar' | 'comprar'
    accion_tomada   VARCHAR(200),        -- 'cotizacion_generada:123'
    tokens_usados   INTEGER,
    fecha           TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX ix_registro_agente_cliente_id ON registro_agente(cliente_id);
CREATE INDEX ix_registro_agente_fecha      ON registro_agente(fecha);

-- ─── DATOS DE EJEMPLO ────────────────────────────────────────────────────────

INSERT INTO clientes (nombre, empresa, telefono, email, ciudad, canal_preferido) VALUES
('Juan Méndez',     'Transportes Méndez SA',  '+52 55 1234 5678', 'juan@tmendez.com',  'Ciudad de México', 'whatsapp'),
('Carlos Reyes',    'Fletes Rápidos del Norte','+52 81 9876 5432', 'carlos@fletes.mx',  'Monterrey',        'whatsapp'),
('María González',  'Logística Central MX',   '+52 33 5555 1111', 'maria@logistica.mx','Guadalajara',      'email');

INSERT INTO productos (nombre, marca, modelo_compatible, categoria, sku, precio, costo, stock, stock_minimo, ubicacion_bodega) VALUES
('Filtro de aceite Kenworth T680',    'Kenworth',  'T680, T880',          'filtros',      'KW-FIL-001', 850.00,  420.00, 45, 10, 'A-01'),
('Kit de frenos Peterbilt 579',       'Peterbilt', '579, 567',            'frenos',       'PB-FRE-001', 3200.00, 1800.00, 8,  5, 'B-03'),
('Sensor de presión de aceite',       'Freightliner','Cascadia 2018-2024','motor',        'FL-SEN-001', 650.00,  320.00, 22, 8, 'C-02'),
('Turbocompresor Volvo VNL',          'Volvo',     'VNL 760, VNL 860',    'motor',        'VO-TUR-001', 12500.00,7200.00, 3,  2, 'D-01'),
('Embrague completo International LT','International','LT 2019-2024',     'transmision',  'IN-EMB-001', 8900.00, 5100.00, 6,  3, 'B-01'),
('Bomba de agua universal',           'Universal', 'Múltiples modelos',   'motor',        'UN-BOM-001', 1200.00, 680.00, 15, 5, 'C-03'),
('Filtro de combustible diesel',      'Universal', 'Múltiples modelos',   'filtros',      'UN-FIL-002', 320.00,  150.00, 80, 20,'A-02'),
('Amortiguador delantero Kenworth',   'Kenworth',  'T680, T880, W990',    'suspension',   'KW-AMO-001', 2100.00, 1200.00,12, 4, 'E-01');
