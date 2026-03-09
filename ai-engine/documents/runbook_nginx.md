# Runbook: Nginx Troubleshooting

## Deskripsi
Panduan troubleshooting untuk masalah umum pada Nginx web server di lingkungan AIOps.

---

## Skenario 1: Nginx Tidak Merespons (Connection Refused)

### Gejala
- HTTP request ke port 8080 mendapat `Connection Refused`
- `nginx_connections_active` bernilai 0
- Metrik `up{job="nginx"}` bernilai 0

### Langkah Diagnosis
```bash
docker ps -a | grep nginx
docker logs aiops-nginx --tail 50
docker exec aiops-nginx nginx -t
```

### Solusi
1. Jika container stopped: `docker start aiops-nginx`
2. Jika config error: Perbaiki `nginx.conf` lalu `docker restart aiops-nginx`
3. Jika port conflict: Cek port 8080 menggunakan `netstat -tlnp | grep 8080`

---

## Skenario 2: High Response Time (Latency Tinggi)

### Gejala
- Response time > 2 detik
- `nginx_connections_active` sangat tinggi (> 500)
- User melaporkan website lambat

### Langkah Diagnosis
```bash
docker exec aiops-nginx cat /var/log/nginx/access.log | tail -20
docker exec aiops-nginx cat /var/log/nginx/error.log | tail -20
docker stats aiops-nginx --no-stream
```

### Solusi
1. **Rate limiting**: Tambahkan limit_req di nginx.conf
2. **Worker tuning**: Naikkan `worker_connections` jika terlalu rendah
3. **Caching**: Aktifkan proxy cache untuk konten statis
4. **Connection pool**: Tambahkan `keepalive` di upstream

---

## Skenario 3: HTTP 502 Bad Gateway

### Gejala
- Response 502 pada endpoint yang di-proxy
- Error log menunjukkan "upstream connection refused"

### Langkah Diagnosis
```bash
docker exec aiops-nginx cat /var/log/nginx/error.log | grep 502
docker ps  # Cek apakah upstream service running
```

### Solusi
1. Pastikan upstream service berjalan
2. Periksa DNS resolution di Docker network
3. Naikkan `proxy_read_timeout` dan `proxy_connect_timeout`

---

## Skenario 4: HTTP 503 Service Unavailable

### Gejala
- Nginx mengembalikan 503
- Semua upstream server down atau overloaded

### Solusi
1. Restart upstream services
2. Jika overload, scale up atau aktifkan circuit breaker
3. Konfigurasi `max_fails` dan `fail_timeout` di upstream block

---

## Monitoring Metrics Penting

| Metric | Normal Range | Alert Threshold |
|--------|-------------|-----------------|
| `nginx_connections_active` | 1-100 | > 500 |
| `nginx_http_requests_total` (rate) | 10-1000 req/s | > 5000 req/s |
| `nginx_connections_handled` == `nginx_connections_accepted` | Harus sama | Jika berbeda, ada dropped connections |
| Container CPU usage | < 50% | > 80% |
| Container Memory usage | < 70% | > 85% |
