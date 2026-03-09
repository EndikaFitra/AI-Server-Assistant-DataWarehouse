import { useState, useEffect } from 'react';
import './DashboardTab.css';

const AI_API_URL = 'http://localhost:8001';

/**
 * Derive stat card values from the raw service metrics array.
 * Each entry has: service_name, service_type, metric_name, unit, value, full_timestamp
 */
function computeStats(services) {
    // 1. Unique monitored services
    const uniqueServices = new Set(services.map((s) => s.service_name));
    const totalServices = uniqueServices.size;

    // 2. Detect services with "up" metric = 0 (down) or memory/cpu = 0 (down indicator)
    const upMetrics = services.filter((s) => s.metric_name === 'up');
    const downServices = upMetrics.filter((s) => Number(s.value) === 0);
    const downCount = downServices.length;

    // If no "up" metrics found, fall back to checking if any value is 0 for key metrics
    let systemStatus = 'Healthy';
    if (downCount > 0) {
        systemStatus = `${downCount} Down`;
    } else if (upMetrics.length === 0 && services.length === 0) {
        systemStatus = 'No Data';
    }

    // 3. Active Alerts — count anomalies:
    //    - Services down (up = 0)
    //    - High memory (> 500MB)
    //    - Any metric with unusually high values
    let alertCount = downCount;
    services.forEach((s) => {
        if (
            s.metric_name === 'container_memory_usage_bytes' &&
            Number(s.value) > 500_000_000
        ) {
            alertCount++;
        }
    });

    // 4. Uptime — percentage of services that are "up"
    let uptimeStr = '—';
    if (upMetrics.length > 0) {
        const upCount = upMetrics.filter((s) => Number(s.value) === 1).length;
        const uptimePct = ((upCount / upMetrics.length) * 100).toFixed(1);
        uptimeStr = `${uptimePct}%`;
    }

    return [
        {
            label: 'Monitored Services',
            value: String(totalServices),
            icon: '🖥️',
            variant: 'blue',
        },
        {
            label: 'System Status',
            value: systemStatus,
            icon: downCount > 0 ? '⚠️' : '✅',
            variant: downCount > 0 ? 'red' : 'green',
        },
        {
            label: 'Active Alerts',
            value: String(alertCount),
            icon: '🔔',
            variant: alertCount > 0 ? 'red' : 'yellow',
        },
        {
            label: 'Uptime',
            value: uptimeStr,
            icon: '⏱️',
            variant: 'orange',
        },
    ];
}

export default function DashboardTab() {
    const [services, setServices] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetch(`${AI_API_URL}/api/status`)
            .then((r) => r.json())
            .then((data) => {
                if (data.data) {
                    try {
                        const parsed =
                            typeof data.data === 'string' ? JSON.parse(data.data) : data.data;
                        setServices(parsed.data || []);
                    } catch {
                        setServices([]);
                    }
                }
                setLoading(false);
            })
            .catch(() => setLoading(false));
    }, []);

    const statusCards = loading
        ? [
            { label: 'Monitored Services', value: '…', icon: '🖥️', variant: 'blue' },
            { label: 'System Status', value: '…', icon: '✅', variant: 'green' },
            { label: 'Active Alerts', value: '…', icon: '🔔', variant: 'yellow' },
            { label: 'Uptime', value: '…', icon: '⏱️', variant: 'orange' },
        ]
        : computeStats(services);

    return (
        <div className="dashboard">
            {/* Stat Cards */}
            <div className="dashboard__stats">
                {statusCards.map((card, i) => (
                    <div
                        key={i}
                        className={`grafana-panel dashboard__stat-card dashboard__stat-card--${card.variant} animate-fade-in-up`}
                        style={{ animationDelay: `${i * 0.06}s` }}
                    >
                        <span className="dashboard__stat-icon">{card.icon}</span>
                        <span className="grafana-stat-label">{card.label}</span>
                        <span className="grafana-stat-value">{card.value}</span>
                    </div>
                ))}
            </div>

            {/* Service Metrics Table */}
            <div
                className="grafana-panel dashboard__table-panel animate-fade-in-up"
                style={{ animationDelay: '0.25s' }}
            >
                <div className="grafana-panel-header">
                    <span>Latest Metrics</span>
                    <span className="panel-tag">
                        <span
                            className="sidebar__status-dot"
                            style={{ width: 6, height: 6 }}
                        />
                        Live
                    </span>
                </div>

                {loading ? (
                    <div className="dashboard__loading">
                        <div className="spinner" />
                        <span className="dashboard__loading-text">
                            Syncing with Data Warehouse…
                        </span>
                    </div>
                ) : services.length > 0 ? (
                    <div style={{ overflowX: 'auto' }}>
                        <table className="grafana-table">
                            <thead>
                                <tr>
                                    <th>Service Name</th>
                                    <th>Type</th>
                                    <th>Metric Evaluated</th>
                                    <th style={{ textAlign: 'right' }}>Current Value</th>
                                </tr>
                            </thead>
                            <tbody>
                                {services.slice(0, 20).map((svc, i) => (
                                    <tr key={i}>
                                        <td
                                            className="dashboard__service-name"
                                            style={{ fontFamily: 'var(--font-sans)' }}
                                        >
                                            {svc.service_name}
                                        </td>
                                        <td style={{ color: 'var(--grafana-text-muted)' }}>
                                            {svc.service_type || '—'}
                                        </td>
                                        <td>
                                            <span className="dashboard__metric-badge">
                                                {svc.metric_name}
                                            </span>
                                        </td>
                                        <td
                                            className="dashboard__metric-value"
                                            style={{ textAlign: 'right' }}
                                        >
                                            {typeof svc.value === 'number'
                                                ? svc.value.toLocaleString(undefined, {
                                                    maximumFractionDigits: 2,
                                                })
                                                : svc.value}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                ) : (
                    <div className="dashboard__empty">
                        <span className="dashboard__empty-icon">📭</span>
                        <p className="dashboard__empty-title">Data Metrik Kosong</p>
                        <p className="dashboard__empty-desc">
                            Jalankan ETL pipeline untuk menarik data dari API Prometheus.
                        </p>
                    </div>
                )}
            </div>
        </div>
    );
}
