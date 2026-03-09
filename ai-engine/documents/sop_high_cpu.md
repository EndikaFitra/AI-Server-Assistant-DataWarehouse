# SOP: Handling High CPU Usage

## Deskripsi
Standard Operating Procedure untuk menangani insiden CPU usage tinggi pada container di lingkungan AIOps.

## Kriteria Trigger
- CPU usage container > 80% selama lebih dari 5 menit
- Alert dari Prometheus: `container_cpu_usage_seconds_total` meningkat tajam

## Langkah Penanganan

### 1. Identifikasi Container
```bash
docker stats --no-stream
docker top <container_name>
```
Periksa container mana yang menggunakan CPU paling tinggi.

### 2. Analisis Proses
```bash
docker exec <container_name> top -bn1
docker exec <container_name> ps aux --sort=-%cpu
```
Identifikasi proses di dalam container yang paling banyak mengonsumsi CPU.

### 3. Periksa Logs
```bash
docker logs --tail 100 <container_name>
docker logs --since 10m <container_name>
```
Cari error, warning, atau loop yang mungkin menyebabkan spike.

### 4. Tindakan Mitigasi
- **Jika disebabkan oleh traffic tinggi**: Scale horizontal (tambah instance), atau aktifkan rate limiting pada Nginx.
- **Jika disebabkan oleh bug/loop**: Restart container: `docker restart <container_name>`
- **Jika disebabkan oleh query berat (DB)**: Identifikasi dan optimasi query menggunakan `EXPLAIN ANALYZE`.

### 5. Monitoring Pasca-Tindakan
- Pantau metrik CPU via Prometheus selama 15 menit setelah tindakan.
- Pastikan usage kembali di bawah 80%.
- Dokumentasikan insiden di log book.

## Eskalasi
Jika CPU tetap tinggi setelah tindakan di atas, eskalasi ke Tim Infrastructure Lead.
