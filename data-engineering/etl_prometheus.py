"""
ETL Pipeline — Prometheus ➜ Data Warehouse
Menarik metrik dari Prometheus HTTP API, transformasi ke
Star Schema, dan load ke PostgreSQL Data Warehouse.

Usage:
    python etl_prometheus.py                     # Sekali jalan
    python etl_prometheus.py --interval 60       # Loop setiap 60 detik
    python etl_prometheus.py --init-schema       # Init schema terlebih dahulu
"""

import argparse
import sys
import time
import os
from datetime import datetime, timezone

import requests
import psycopg2

# ── Konfigurasi ──
PROMETHEUS_URL = "http://192.168.163.128:9090"

WAREHOUSE_CONFIG = {
    "host": "192.168.163.128",
    "port": 5434,
    "database": "warehouse_db",
    "user": "admin",
    "password": "pass",
}

# Metrik yang akan dikumpulkan dari Prometheus
METRICS_TO_COLLECT = [
    # cAdvisor container metrics
    "container_cpu_usage_seconds_total",
    "container_memory_usage_bytes",
    "container_memory_cache",
    "container_network_receive_bytes_total",
    "container_network_transmit_bytes_total",
    "container_fs_usage_bytes",
    # Nginx metrics
    "nginx_connections_active",
    "nginx_connections_accepted",
    "nginx_connections_handled",
    "nginx_http_requests_total",
    # Service availability
    "up",
]

# Mapping container name → service name
CONTAINER_SERVICE_MAP = {
    "aiops-nginx": "nginx",
    "aiops-postgres-target": "postgres-target",
    "aiops-postgres-warehouse": "postgres-warehouse",
    "aiops-cadvisor": "cadvisor",
    "aiops-prometheus": "prometheus",
}


class ETLPipeline:
    def __init__(self, prometheus_url: str, db_config: dict):
        self.prometheus_url = prometheus_url.rstrip("/")
        self.db_config = db_config
        self.conn = None

    def connect_warehouse(self):
        """Koneksi ke Data Warehouse."""
        try:
            self.conn = psycopg2.connect(**self.db_config)
            self.conn.autocommit = False
            print("✅ Connected to Data Warehouse")
        except psycopg2.Error as e:
            print(f"❌ Failed to connect to warehouse: {e}")
            sys.exit(1)

    def close(self):
        """Tutup koneksi."""
        if self.conn:
            self.conn.close()
            print("🔌 Warehouse connection closed")

    # ── EXTRACT ──

    def query_prometheus(self, query: str, time_param: str = None) -> list:
        """Query instant dari Prometheus API."""
        url = f"{self.prometheus_url}/api/v1/query"
        params = {"query": query}
        if time_param:
            params["time"] = time_param

        try:
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            if data.get("status") != "success":
                print(f"   ⚠️  Prometheus query failed: {data.get('error', 'unknown')}")
                return []

            return data.get("data", {}).get("result", [])

        except requests.RequestException as e:
            print(f"   ❌ Prometheus request error: {e}")
            return []

    def extract_metrics(self) -> list:
        """Extract semua metrik dari Prometheus."""
        print("\n📥 EXTRACT: Pulling metrics from Prometheus...")
        all_results = []

        for metric_name in METRICS_TO_COLLECT:
            results = self.query_prometheus(metric_name)
            for r in results:
                r["__metric_name__"] = metric_name
            all_results.extend(results)
            if results:
                print(f"   ✅ {metric_name}: {len(results)} series")
            else:
                print(f"   ⏭️  {metric_name}: no data")

        print(f"   📊 Total extracted: {len(all_results)} data points")
        return all_results

    # ── TRANSFORM ──

    def resolve_service_name(self, labels: dict) -> str:
        """Resolve nama service dari labels Prometheus."""
        # Coba dari container name
        container = labels.get("name", labels.get("container_label_com_docker_compose_service", ""))
        if container in CONTAINER_SERVICE_MAP:
            return CONTAINER_SERVICE_MAP[container]

        # Coba dari job label
        job = labels.get("job", "")
        if job in ("nginx", "nginx-health"):
            return "nginx"
        if job == "cadvisor":
            return "cadvisor"
        if job == "prometheus":
            return "prometheus"

        # Coba dari instance
        instance = labels.get("instance", "")
        for svc_name in CONTAINER_SERVICE_MAP.values():
            if svc_name in instance:
                return svc_name

        return labels.get("job", "unknown")

    def transform_metrics(self, raw_data: list) -> list:
        """Transform data mentah ke format Star Schema."""
        print("\n🔄 TRANSFORM: Converting to Star Schema format...")
        transformed = []

        for item in raw_data:
            labels = item.get("metric", {})
            value_pair = item.get("value", [])

            if len(value_pair) < 2:
                continue

            timestamp = datetime.fromtimestamp(float(value_pair[0]), tz=timezone.utc)
            try:
                value = float(value_pair[1])
            except (ValueError, TypeError):
                continue

            metric_name = item.get("__metric_name__", labels.get("__name__", "unknown"))
            service_name = self.resolve_service_name(labels)

            transformed.append({
                "timestamp": timestamp,
                "service_name": service_name,
                "metric_name": metric_name,
                "value": value,
            })

        print(f"   📊 Transformed: {len(transformed)} records")
        return transformed

    # ── LOAD ──

    def ensure_time_dimension(self, cursor, timestamp: datetime) -> int:
        """Insert atau ambil time_id dari dim_time."""
        cursor.execute(
            "SELECT time_id FROM dim_time WHERE full_timestamp = %s",
            (timestamp,)
        )
        row = cursor.fetchone()
        if row:
            return row[0]

        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        dow = timestamp.weekday()

        cursor.execute(
            """
            INSERT INTO dim_time (full_timestamp, date, hour, minute, day_of_week, day_name, is_weekend)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (full_timestamp) DO UPDATE SET full_timestamp = EXCLUDED.full_timestamp
            RETURNING time_id
            """,
            (
                timestamp,
                timestamp.date(),
                timestamp.hour,
                timestamp.minute,
                dow,
                day_names[dow],
                dow >= 5,
            )
        )
        return cursor.fetchone()[0]

    def get_dimension_id(self, cursor, table: str, name_col: str, name_val: str, id_col: str) -> int:
        """Ambil ID dari dimension table."""
        cursor.execute(f"SELECT {id_col} FROM {table} WHERE {name_col} = %s", (name_val,))
        row = cursor.fetchone()
        return row[0] if row else None

    def load_to_warehouse(self, transformed_data: list):
        """Load data transformasi ke Data Warehouse."""
        print("\n📤 LOAD: Inserting into Data Warehouse...")

        if not transformed_data:
            print("   ⏭️  No data to load.")
            return

        cursor = self.conn.cursor()
        loaded = 0
        skipped = 0

        try:
            for record in transformed_data:
                # Resolve dimension IDs
                time_id = self.ensure_time_dimension(cursor, record["timestamp"])

                service_id = self.get_dimension_id(
                    cursor, "dim_service", "service_name",
                    record["service_name"], "service_id"
                )
                if not service_id:
                    skipped += 1
                    continue

                metric_id = self.get_dimension_id(
                    cursor, "dim_metric", "metric_name",
                    record["metric_name"], "metric_id"
                )
                if not metric_id:
                    skipped += 1
                    continue

                # Insert fact
                cursor.execute(
                    """
                    INSERT INTO fact_metrics (time_id, service_id, metric_id, value, collected_at)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (time_id, service_id, metric_id, record["value"], datetime.now(timezone.utc))
                )
                loaded += 1

            self.conn.commit()
            print(f"   ✅ Loaded: {loaded} records | Skipped: {skipped}")

        except psycopg2.Error as e:
            self.conn.rollback()
            print(f"   ❌ Load error: {e}")

        finally:
            cursor.close()

    # ── RUN ──

    def run_once(self):
        """Jalankan satu siklus ETL."""
        print("=" * 60)
        print(f"  ETL Cycle — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)

        raw_data = self.extract_metrics()
        transformed = self.transform_metrics(raw_data)
        self.load_to_warehouse(transformed)

        print("\n✅ ETL cycle completed.\n")

    def run_loop(self, interval_seconds: int):
        """Jalankan ETL dalam loop."""
        print(f"🔁 Starting ETL loop (interval: {interval_seconds}s)")
        print("   Press Ctrl+C to stop.\n")

        try:
            while True:
                self.run_once()
                print(f"⏳ Next cycle in {interval_seconds} seconds...")
                time.sleep(interval_seconds)
        except KeyboardInterrupt:
            print("\n\n🛑 ETL loop stopped by user.")


def init_warehouse_schema():
    """Jalankan DDL schema jika belum ada."""
    ddl_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ddl", "warehouse_schema.sql")

    if not os.path.exists(ddl_path):
        print(f"⚠️  DDL file not found: {ddl_path}")
        return

    print("🏗️  Initializing warehouse schema...")
    conn = psycopg2.connect(**WAREHOUSE_CONFIG)
    conn.autocommit = True
    cursor = conn.cursor()

    with open(ddl_path, "r") as f:
        cursor.execute(f.read())

    cursor.close()
    conn.close()
    print("✅ Warehouse schema initialized.\n")


def main():
    parser = argparse.ArgumentParser(description="AIOps ETL: Prometheus → Data Warehouse")
    parser.add_argument("--interval", type=int, default=0,
                        help="Loop interval in seconds (0 = run once)")
    parser.add_argument("--init-schema", action="store_true",
                        help="Initialize warehouse schema before ETL")
    parser.add_argument("--prometheus-url", type=str, default=PROMETHEUS_URL,
                        help=f"Prometheus base URL (default: {PROMETHEUS_URL})")

    args = parser.parse_args()

    if args.init_schema:
        init_warehouse_schema()

    etl = ETLPipeline(args.prometheus_url, WAREHOUSE_CONFIG)
    etl.connect_warehouse()

    try:
        if args.interval > 0:
            etl.run_loop(args.interval)
        else:
            etl.run_once()
    finally:
        etl.close()


if __name__ == "__main__":
    main()
