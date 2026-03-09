-- ==============================================
-- PostgreSQL Target — Initial Schema
-- Database simulasi yang akan dimonitor oleh cAdvisor
-- ==============================================

-- Tabel simulasi: Data pengguna (contoh workload)
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabel simulasi: Log aktivitas
CREATE TABLE IF NOT EXISTS activity_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    details TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Seed data untuk simulasi
INSERT INTO users (username, email) VALUES
    ('admin', 'admin@aiops-lab.local'),
    ('operator', 'operator@aiops-lab.local'),
    ('monitor', 'monitor@aiops-lab.local')
ON CONFLICT (username) DO NOTHING;

INSERT INTO activity_logs (user_id, action, details) VALUES
    (1, 'LOGIN', 'Admin logged in from 192.168.1.1'),
    (2, 'DEPLOY', 'Operator deployed service v1.2.3'),
    (3, 'ALERT_ACK', 'Monitor acknowledged CPU alert');

-- Index untuk performa query
CREATE INDEX IF NOT EXISTS idx_activity_logs_user_id ON activity_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_activity_logs_created_at ON activity_logs(created_at);
