# SOP: Handling Memory Leak

## Deskripsi
Standard Operating Procedure untuk menangani potensi memory leak pada container di lingkungan AIOps.

## Kriteria Trigger
- Memory usage container > 85% dan terus meningkat secara linear
- `container_memory_usage_bytes` meningkat tanpa ada penurunan selama 30 menit
- OOM (Out of Memory) kill terdeteksi di Docker events

## Langkah Penanganan

### 1. Identifikasi Container
```bash
docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}"
```
Bandingkan memory usage saat ini dengan limit yang dikonfigurasi.

### 2. Analisis Memory Profile
```bash
docker exec <container_name> cat /proc/meminfo
docker exec <container_name> cat /sys/fs/cgroup/memory/memory.usage_in_bytes
```
Periksa distribusi penggunaan memory (cache vs RSS).

### 3. Periksa Trend Historis
Gunakan query Prometheus untuk melihat tren:
```promql
container_memory_usage_bytes{name="<container_name>"}[1h]
rate(container_memory_usage_bytes{name="<container_name>"}[5m])
```
Jika trend terus naik, kemungkinan besar memory leak.

### 4. Tindakan Mitigasi
- **Restart container** sebagai solusi sementara:
  ```bash
  docker restart <container_name>
  ```
- **Set memory limit** di docker-compose.yml:
  ```yaml
  deploy:
    resources:
      limits:
        memory: 512M
  ```
- **Investigasi kode aplikasi**: Periksa apakah ada koneksi DB yang tidak ditutup, cache tanpa eviction, atau goroutine/thread leak.

### 5. Pencegahan
- Konfigurasi memory limit untuk semua container
- Set up alert di Prometheus untuk memory > 80%
- Implementasi health check yang memonitor memory usage

## Eskalasi
Jika memory leak berulang setelah restart, eskalasi ke Tim Development untuk code review.
