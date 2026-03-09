"""
Load Simulator — AIOps Infrastructure
Mengirim HTTP requests secara masif ke Nginx untuk
mensimulasikan traffic dan membuat CPU/Memory spike.

Usage:
    python load_simulator.py                   # Default: 50 concurrent, 200 total
    python load_simulator.py --workers 100 --total 500
    python load_simulator.py --mode spike       # Mode burst traffic
"""

import argparse
import random
import time
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

# ── Konfigurasi ──
NGINX_BASE_URL = "http://192.168.163.128:8080"

ENDPOINTS = [
    {"path": "/", "weight": 50, "label": "homepage"},
    {"path": "/health", "weight": 20, "label": "health-check"},
    {"path": "/heavy", "weight": 15, "label": "heavy-compute"},
    {"path": "/slow", "weight": 10, "label": "slow-endpoint"},
    {"path": "/error", "weight": 5, "label": "error-endpoint"},
]


def weighted_random_endpoint():
    """Pilih endpoint berdasarkan bobot (weight)."""
    total = sum(e["weight"] for e in ENDPOINTS)
    rand = random.randint(1, total)
    cumulative = 0
    for ep in ENDPOINTS:
        cumulative += ep["weight"]
        if rand <= cumulative:
            return ep
    return ENDPOINTS[0]


def send_request(request_id: int) -> dict:
    """Kirim satu HTTP request ke random endpoint."""
    endpoint = weighted_random_endpoint()
    url = f"{NGINX_BASE_URL}{endpoint['path']}"
    start = time.time()

    try:
        response = requests.get(url, timeout=10)
        elapsed = round(time.time() - start, 3)
        return {
            "id": request_id,
            "endpoint": endpoint["label"],
            "status": response.status_code,
            "time_ms": elapsed * 1000,
            "success": True,
        }
    except requests.RequestException as e:
        elapsed = round(time.time() - start, 3)
        return {
            "id": request_id,
            "endpoint": endpoint["label"],
            "status": 0,
            "time_ms": elapsed * 1000,
            "success": False,
            "error": str(e),
        }


def run_normal_load(workers: int, total_requests: int):
    """Mode normal: kirim request secara concurrent."""
    print(f"\n🚀 Starting NORMAL load: {total_requests} requests with {workers} workers")
    print(f"   Target: {NGINX_BASE_URL}")
    print("-" * 60)

    results = {"total": 0, "success": 0, "failed": 0, "status_codes": {}}
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(send_request, i): i
            for i in range(total_requests)
        }

        for future in as_completed(futures):
            result = future.result()
            results["total"] += 1

            if result["success"]:
                results["success"] += 1
                code = str(result["status"])
                results["status_codes"][code] = results["status_codes"].get(code, 0) + 1
            else:
                results["failed"] += 1

            # Progress setiap 50 request
            if results["total"] % 50 == 0:
                elapsed = round(time.time() - start_time, 1)
                rps = round(results["total"] / max(elapsed, 0.1), 1)
                print(f"   ⏳ Progress: {results['total']}/{total_requests} "
                      f"({rps} req/s) — ✅ {results['success']} ❌ {results['failed']}")

    total_time = round(time.time() - start_time, 2)
    rps = round(results["total"] / max(total_time, 0.1), 1)

    print("-" * 60)
    print(f"✅ Completed in {total_time}s — {rps} req/s")
    print(f"   Success: {results['success']} | Failed: {results['failed']}")
    print(f"   Status codes: {results['status_codes']}")


def run_spike_load(duration_seconds: int = 30, workers: int = 200):
    """Mode spike: burst traffic intens selama durasi tertentu."""
    print(f"\n⚡ Starting SPIKE load: {workers} workers for {duration_seconds}s")
    print(f"   Target: {NGINX_BASE_URL}")
    print("-" * 60)

    results = {"total": 0, "success": 0, "failed": 0}
    start_time = time.time()
    request_id = 0

    with ThreadPoolExecutor(max_workers=workers) as executor:
        while time.time() - start_time < duration_seconds:
            # Submit batch of requests
            batch_size = workers
            futures = []
            for _ in range(batch_size):
                request_id += 1
                futures.append(executor.submit(send_request, request_id))

            for future in as_completed(futures):
                result = future.result()
                results["total"] += 1
                if result["success"]:
                    results["success"] += 1
                else:
                    results["failed"] += 1

            elapsed = round(time.time() - start_time, 1)
            rps = round(results["total"] / max(elapsed, 0.1), 1)
            print(f"   ⚡ [{elapsed}s/{duration_seconds}s] "
                  f"Total: {results['total']} ({rps} req/s) — "
                  f"✅ {results['success']} ❌ {results['failed']}")

    total_time = round(time.time() - start_time, 2)
    rps = round(results["total"] / max(total_time, 0.1), 1)

    print("-" * 60)
    print(f"⚡ Spike finished in {total_time}s — {rps} req/s")
    print(f"   Total requests: {results['total']}")
    print(f"   Success: {results['success']} | Failed: {results['failed']}")


def main():
    global NGINX_BASE_URL
    
    parser = argparse.ArgumentParser(description="AIOps Load Simulator")
    parser.add_argument("--mode", choices=["normal", "spike"], default="normal",
                        help="Mode simulasi: 'normal' atau 'spike' (default: normal)")
    parser.add_argument("--workers", type=int, default=50,
                        help="Jumlah concurrent workers (default: 50)")
    parser.add_argument("--total", type=int, default=200,
                        help="Total requests untuk mode normal (default: 200)")
    parser.add_argument("--duration", type=int, default=30,
                        help="Durasi spike dalam detik (default: 30)")
    parser.add_argument("--url", type=str, default=NGINX_BASE_URL,
                        help=f"Base URL Nginx (default: {NGINX_BASE_URL})")

    args = parser.parse_args()

    NGINX_BASE_URL = args.url

    print("=" * 60)
    print("  AIOps Load Simulator")
    print("=" * 60)

    try:
        if args.mode == "normal":
            run_normal_load(args.workers, args.total)
        elif args.mode == "spike":
            run_spike_load(args.duration, args.workers)
    except KeyboardInterrupt:
        print("\n\n🛑 Load simulation interrupted by user.")
        sys.exit(0)


if __name__ == "__main__":
    main()
