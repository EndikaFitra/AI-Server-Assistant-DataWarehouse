-- ==============================================
-- Data Warehouse Schema — Star Schema
-- Database: warehouse_db (postgres-warehouse)
-- ==============================================

-- ── DIMENSION TABLES ──

-- Dimensi waktu untuk analisis time-series
CREATE TABLE IF NOT EXISTS dim_time (
    time_id SERIAL PRIMARY KEY,
    full_timestamp TIMESTAMP NOT NULL UNIQUE,
    date DATE NOT NULL,
    hour SMALLINT NOT NULL,
    minute SMALLINT NOT NULL,
    day_of_week SMALLINT NOT NULL,       -- 0=Sunday, 6=Saturday
    day_name VARCHAR(10) NOT NULL,
    is_weekend BOOLEAN NOT NULL DEFAULT FALSE
);

-- Dimensi service/container yang dimonitor
CREATE TABLE IF NOT EXISTS dim_service (
    service_id SERIAL PRIMARY KEY,
    service_name VARCHAR(100) NOT NULL UNIQUE,
    service_type VARCHAR(50) NOT NULL,    -- 'web_server', 'database', 'monitoring'
    container_name VARCHAR(100),
    description TEXT
);

-- Dimensi jenis metrik
CREATE TABLE IF NOT EXISTS dim_metric (
    metric_id SERIAL PRIMARY KEY,
    metric_name VARCHAR(200) NOT NULL UNIQUE,
    metric_type VARCHAR(50) NOT NULL,     -- 'gauge', 'counter', 'histogram'
    unit VARCHAR(50),                     -- 'bytes', 'seconds', 'percent', 'count'
    description TEXT
);

-- ── FACT TABLE ──

-- Fakta metrik: menyimpan semua data monitoring historis
CREATE TABLE IF NOT EXISTS fact_metrics (
    id BIGSERIAL PRIMARY KEY,
    time_id INTEGER NOT NULL REFERENCES dim_time(time_id),
    service_id INTEGER NOT NULL REFERENCES dim_service(service_id),
    metric_id INTEGER NOT NULL REFERENCES dim_metric(metric_id),
    value DOUBLE PRECISION NOT NULL,
    collected_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ── INDEXES untuk performa query ──
CREATE INDEX IF NOT EXISTS idx_fact_metrics_time ON fact_metrics(time_id);
CREATE INDEX IF NOT EXISTS idx_fact_metrics_service ON fact_metrics(service_id);
CREATE INDEX IF NOT EXISTS idx_fact_metrics_metric ON fact_metrics(metric_id);
CREATE INDEX IF NOT EXISTS idx_fact_metrics_collected ON fact_metrics(collected_at);
CREATE INDEX IF NOT EXISTS idx_dim_time_timestamp ON dim_time(full_timestamp);
CREATE INDEX IF NOT EXISTS idx_dim_time_date ON dim_time(date);

-- ── SEED: Dimension Data ──

-- Services yang dimonitor
INSERT INTO dim_service (service_name, service_type, container_name, description) VALUES
    ('nginx', 'web_server', 'aiops-nginx', 'Nginx reverse proxy / web server'),
    ('postgres-target', 'database', 'aiops-postgres-target', 'PostgreSQL application database'),
    ('postgres-warehouse', 'database', 'aiops-postgres-warehouse', 'PostgreSQL data warehouse'),
    ('cadvisor', 'monitoring', 'aiops-cadvisor', 'Container metrics collector'),
    ('prometheus', 'monitoring', 'aiops-prometheus', 'Time-series monitoring system')
ON CONFLICT (service_name) DO NOTHING;

-- Metrik yang dikumpulkan
INSERT INTO dim_metric (metric_name, metric_type, unit, description) VALUES
    ('container_cpu_usage_seconds_total', 'counter', 'seconds', 'Total CPU time consumed by container'),
    ('container_memory_usage_bytes', 'gauge', 'bytes', 'Current memory usage of container'),
    ('container_memory_cache', 'gauge', 'bytes', 'Memory cache used by container'),
    ('container_network_receive_bytes_total', 'counter', 'bytes', 'Total bytes received over network'),
    ('container_network_transmit_bytes_total', 'counter', 'bytes', 'Total bytes transmitted over network'),
    ('container_fs_usage_bytes', 'gauge', 'bytes', 'Filesystem usage in bytes'),
    ('nginx_connections_active', 'gauge', 'count', 'Active client connections on Nginx'),
    ('nginx_connections_accepted', 'counter', 'count', 'Total accepted client connections'),
    ('nginx_connections_handled', 'counter', 'count', 'Total handled client connections'),
    ('nginx_http_requests_total', 'counter', 'count', 'Total number of HTTP requests'),
    ('up', 'gauge', 'boolean', 'Whether the target is up (1) or down (0)')
ON CONFLICT (metric_name) DO NOTHING;

-- ── VIEW: Ringkasan metrik terbaru per service ──
CREATE OR REPLACE VIEW vw_latest_metrics AS
SELECT
    ds.service_name,
    dm.metric_name,
    dm.unit,
    fm.value,
    dt.full_timestamp
FROM fact_metrics fm
JOIN dim_service ds ON fm.service_id = ds.service_id
JOIN dim_metric dm ON fm.metric_id = dm.metric_id
JOIN dim_time dt ON fm.time_id = dt.time_id
WHERE dt.full_timestamp >= NOW() - INTERVAL '1 hour'
ORDER BY dt.full_timestamp DESC;

-- ── VIEW: Rata-rata metrik per jam per service ──
CREATE OR REPLACE VIEW vw_hourly_avg_metrics AS
SELECT
    ds.service_name,
    dm.metric_name,
    dm.unit,
    dt.date,
    dt.hour,
    AVG(fm.value) AS avg_value,
    MAX(fm.value) AS max_value,
    MIN(fm.value) AS min_value,
    COUNT(*) AS sample_count
FROM fact_metrics fm
JOIN dim_service ds ON fm.service_id = ds.service_id
JOIN dim_metric dm ON fm.metric_id = dm.metric_id
JOIN dim_time dt ON fm.time_id = dt.time_id
GROUP BY ds.service_name, dm.metric_name, dm.unit, dt.date, dt.hour
ORDER BY dt.date DESC, dt.hour DESC;
