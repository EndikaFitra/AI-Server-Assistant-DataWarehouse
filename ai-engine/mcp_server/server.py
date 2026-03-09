"""
MCP Server (SSE Transport) — AIOps
Server MCP yang menyediakan tool `query_historical_metrics()`
untuk membaca Data Warehouse via SQL.

Transport: Server-Sent Events (SSE)

Usage:
    python -m mcp_server.server
    # Server akan berjalan di http://localhost:8000/sse
"""

import os
import sys
import json
from datetime import datetime, timezone

import psycopg2
import psycopg2.extras
from mcp.server.fastmcp import FastMCP

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mcp_server.config import WAREHOUSE_CONFIG, MCP_SERVER_HOST, MCP_SERVER_PORT


# ── Init MCP Server ──
mcp = FastMCP(
    "AIOps Data Warehouse",
)


def get_db_connection():
    """Buat koneksi baru ke Data Warehouse."""
    return psycopg2.connect(**WAREHOUSE_CONFIG)


# ── MCP Tools ──

@mcp.tool()
def query_historical_metrics(
    service_name: str = "",
    metric_name: str = "",
    hours_back: int = 1,
    limit: int = 50,
) -> str:
    """
    Query metrik historis dari Data Warehouse AIOps.

    Parameters:
        service_name: Nama service (e.g. 'nginx', 'postgres-target'). Kosongkan untuk semua.
        metric_name: Nama metrik (e.g. 'container_cpu_usage_seconds_total'). Kosongkan untuk semua.
        hours_back: Berapa jam ke belakang data diambil (default: 1).
        limit: Batas jumlah hasil (default: 50).

    Returns:
        JSON string berisi data metrik historis.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Build query dinamis
        conditions = ["dt.full_timestamp >= NOW() - INTERVAL '%s hours'"]
        params = [hours_back]

        if service_name:
            conditions.append("ds.service_name = %s")
            params.append(service_name)

        if metric_name:
            conditions.append("dm.metric_name = %s")
            params.append(metric_name)

        where_clause = " AND ".join(conditions)

        query = f"""
            SELECT
                ds.service_name,
                dm.metric_name,
                dm.unit,
                fm.value,
                dt.full_timestamp,
                dt.day_name,
                dt.hour
            FROM fact_metrics fm
            JOIN dim_service ds ON fm.service_id = ds.service_id
            JOIN dim_metric dm ON fm.metric_id = dm.metric_id
            JOIN dim_time dt ON fm.time_id = dt.time_id
            WHERE {where_clause}
            ORDER BY dt.full_timestamp DESC
            LIMIT %s
        """
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()

        # Convert datetime objects to string
        results = []
        for row in rows:
            record = dict(row)
            for key, val in record.items():
                if isinstance(val, datetime):
                    record[key] = val.isoformat()
            results.append(record)

        cursor.close()
        conn.close()

        return json.dumps({
            "status": "success",
            "count": len(results),
            "query_params": {
                "service_name": service_name or "all",
                "metric_name": metric_name or "all",
                "hours_back": hours_back,
            },
            "data": results,
        }, indent=2, default=str)

    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": str(e),
        })


@mcp.tool()
def get_service_summary() -> str:
    """
    Ambil ringkasan status semua service yang dimonitor.
    Mengembalikan metrik terbaru per service.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        query = """
            SELECT
                ds.service_name,
                ds.service_type,
                dm.metric_name,
                dm.unit,
                fm.value,
                dt.full_timestamp
            FROM fact_metrics fm
            JOIN dim_service ds ON fm.service_id = ds.service_id
            JOIN dim_metric dm ON fm.metric_id = dm.metric_id
            JOIN dim_time dt ON fm.time_id = dt.time_id
            WHERE fm.id IN (
                SELECT MAX(fm2.id)
                FROM fact_metrics fm2
                JOIN dim_service ds2 ON fm2.service_id = ds2.service_id
                JOIN dim_metric dm2 ON fm2.metric_id = dm2.metric_id
                GROUP BY ds2.service_id, dm2.metric_id
            )
            ORDER BY ds.service_name, dm.metric_name
        """

        cursor.execute(query)
        rows = cursor.fetchall()

        results = []
        for row in rows:
            record = dict(row)
            for key, val in record.items():
                if isinstance(val, datetime):
                    record[key] = val.isoformat()
            results.append(record)

        cursor.close()
        conn.close()

        return json.dumps({
            "status": "success",
            "count": len(results),
            "data": results,
        }, indent=2, default=str)

    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": str(e),
        })


@mcp.tool()
def detect_anomalies(
    service_name: str = "",
    hours_back: int = 1,
    cpu_threshold: float = 80.0,
    memory_threshold_bytes: float = 500_000_000,
) -> str:
    """
    Deteksi anomali pada metrik infrastruktur.
    Memeriksa CPU usage tinggi, memory usage tinggi, dan service downtime.

    Parameters:
        service_name: Filter service tertentu (opsional).
        hours_back: Rentang waktu analisis dalam jam (default: 1).
        cpu_threshold: Threshold CPU dalam persen (default: 80).
        memory_threshold_bytes: Threshold memory dalam bytes (default: 500MB).
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        anomalies = []

        # 1. Cek high memory usage
        mem_query = """
            SELECT ds.service_name, fm.value, dt.full_timestamp
            FROM fact_metrics fm
            JOIN dim_service ds ON fm.service_id = ds.service_id
            JOIN dim_metric dm ON fm.metric_id = dm.metric_id
            JOIN dim_time dt ON fm.time_id = dt.time_id
            WHERE dm.metric_name = 'container_memory_usage_bytes'
              AND dt.full_timestamp >= NOW() - INTERVAL '%s hours'
              AND fm.value > %s
        """
        mem_params = [hours_back, memory_threshold_bytes]
        if service_name:
            mem_query += " AND ds.service_name = %s"
            mem_params.append(service_name)

        cursor.execute(mem_query, mem_params)
        for row in cursor.fetchall():
            anomalies.append({
                "type": "HIGH_MEMORY",
                "service": row["service_name"],
                "value_bytes": row["value"],
                "value_mb": round(row["value"] / 1_000_000, 2),
                "threshold_mb": round(memory_threshold_bytes / 1_000_000, 2),
                "timestamp": row["full_timestamp"].isoformat(),
                "severity": "WARNING" if row["value"] < memory_threshold_bytes * 1.5 else "CRITICAL",
            })

        # 2. Cek service down (up = 0)
        down_query = """
            SELECT ds.service_name, fm.value, dt.full_timestamp
            FROM fact_metrics fm
            JOIN dim_service ds ON fm.service_id = ds.service_id
            JOIN dim_metric dm ON fm.metric_id = dm.metric_id
            JOIN dim_time dt ON fm.time_id = dt.time_id
            WHERE dm.metric_name = 'up'
              AND fm.value = 0
              AND dt.full_timestamp >= NOW() - INTERVAL '%s hours'
        """
        down_params = [hours_back]
        if service_name:
            down_query += " AND ds.service_name = %s"
            down_params.append(service_name)

        cursor.execute(down_query, down_params)
        for row in cursor.fetchall():
            anomalies.append({
                "type": "SERVICE_DOWN",
                "service": row["service_name"],
                "timestamp": row["full_timestamp"].isoformat(),
                "severity": "CRITICAL",
            })

        cursor.close()
        conn.close()

        return json.dumps({
            "status": "success",
            "anomaly_count": len(anomalies),
            "analysis_window_hours": hours_back,
            "anomalies": anomalies,
        }, indent=2, default=str)

    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": str(e),
        })


# ── Run Server ──
if __name__ == "__main__":
    print("=" * 60)
    print("  AIOps MCP Server (SSE Transport)")
    print(f"  Endpoint: http://{MCP_SERVER_HOST}:{MCP_SERVER_PORT}/sse")
    print("=" * 60)

    mcp.run(transport="sse")
