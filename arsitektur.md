# Arsitektur Sistem AIOps

## Diagram Arsitektur Keseluruhan

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                              USER/ADMIN                                              │
└──────────────────────────────────────────────┬──────────────────────────────────────────────────────┘
                                               │
                                               │ HTTP Requests
                                               ▼
┌───────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                           FRONTEND (Vite + React)                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │  • DashboardTab.jsx    → Menampilkan metrik dan visualisasi                                    │  │
│  │  • ChatTab.jsx         → Interface chat dengan AI Assistant                                   │  │
│  │  • Sidebar.jsx         → Navigasi antar tab                                                     │  │
│  │                                                                                                  │  │
│  │  Komunikasi: HTTP ke AI Backend API (localhost:8001)                                           │  │
│  └─────────────────────────────────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────┬───────────────────────────────────────────────────────┘
                                               │
                    ┌──────────────────────────┴───────────────────────────┐
                    │                  REST API (FastAPI)                    │
                    │                   localhost:8001                       │
                    │  ┌─────────────────────────────────────────────────┐   │
                    │  │  /health          → Health check                  │   │
                    │  │  /api/chat        → Chat endpoint (POST)           │   │
                    │  │  /api/chat/reset  → Reset conversation (POST)     │   │
                    │  │  /api/status      → System status summary (GET)   │   │
                    │  └─────────────────────────────────────────────────┘   │
                    └──────────────────────────┬──────────────────────────────┘
                                               │
                    ┌──────────────────────────┴──────────────────────────────┐
                    │                         AI AGENT                            │
                    │                    (AIOpsAgent - agent.py)                 │
                    │                                                                       │
                    │  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   │
                    │  │  RAG (Chroma)│   │ MCP Tools    │   │  LLM (Ollama)│   │
                    │  │              │   │              │   │              │   │
                    │  │ • retriever  │   │ • query_     │   │ • qwen3:4b   │   │
                    │  │ • documents  │   │   historical │   │ • nomic-embed│   │
                    │  │   SOP/Runbook│   │   metrics    │   │   -text-v2   │   │
                    │  └──────┬───────┘   │ • get_service│   └──────┬───────┘   │
                    │         │           │   _summary   │          │           │
                    │         │           │ • detect_    │          │           │
                    │         │           │   anomalies │          │           │
                    │         └───────────┴──────┬───────┘          │           │
                    │                             │                  │           │
                    │                             ▼                  ▼           │
                    │  ┌─────────────────────────────────────────────────────────┐ │
                    │  │              Orchestration Flow                           │ │
                    │  │  1. Determine Intent (RAG/Metrics/Anomaly/Summary)       │ │
                    │  │  2. Gather Context (RAG + MCP Tools)                     │ │
                    │  │  3. Build Prompt → Send to Ollama                        │ │
                    │  │  4. Return Response to User                               │ │
                    │  └─────────────────────────────────────────────────────────┘ │
                    └─────────────────────────────┬───────────────────────────────────┘
                                                  │
           ┌──────────────────────────────────────┴───────────────────────────────────────┐
           │                                       │                                        │
           ▼                                       ▼                                        ▼
┌─────────────────────────────┐   ┌─────────────────────────────┐   ┌─────────────────────────────┐
│      RAG SYSTEM             │   │     MCP SERVER              │   │     OLLAMA (External)       │
│   (Vector Database)        │   │   (Data Tools)              │   │   (LLM Inference)          │
│                             │   │                             │   │                             │
│ • ChromaDB                 │   │ • query_historical_metrics  │   │ • qwen3:4b-instruct         │
│   - Persistent storage     │   │   → Query ke warehouse      │   │   (Chat/Reasoning)          │
│   - Collection:            │   │                             │   │                             │
│     aiop_sop_runbook       │   │ • get_service_summary       │   │ • nomic-embed-text-v2-moe  │
│                             │   │   → Latest metrics per svc  │   │   (Embeddings for RAG)     │
│ • Documents:               │   │                             │   │                             │
│   - SOP/Runbook            │   │ • detect_anomalies          │   │   localhost:11434           │
│   - Nginx runbook          │   │   → CPU/Memory/Service down │   │                             │
│   - SOP High CPU           │   │                             │   │                             │
│   - SOP Memory Leak        │   │   localhost:8000 (SSE)      │   │                             │
└──────────────┬──────────────┘   └──────────────┬──────────────┘   └─────────────────────────────┘
               │                                  │
               │                                  │ SQL Queries
               │                                  ▼
               │                    ┌─────────────────────────────────────────┐
               │                    │        DATA WAREHOUSE                   │
               │                    │     (PostgreSQL - Star Schema)         │
               │                    │                                         │
               │                    │  ┌─────────────┐  ┌─────────────┐       │
               │                    │  │  DIM TABLES │  │ FACT TABLE  │       │
               │                    │  ├─────────────┤  ├─────────────┤       │
               │                    │  │ dim_time    │  │ fact_metrics│       │
               │                    │  │ dim_service │  │             │       │
               │                    │  │ dim_metric  │  │             │       │
               │                    │  └─────────────┘  └─────────────┘       │
               │                    │                                         │
               │                    │  Port: 5434                             │
               │                    │  DB: warehouse_db                       │
               │                    └─────────────────────────────────────────┘
               │
               │ ETL Pipeline
               ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    DATA ENGINEERING                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────────────────────────────┐ │
│  │  etl_prometheus.py                                                                              │ │
│  │  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                                      │ │
│  │  │   EXTRACT   │───▶│   TRANSFORM  │───▶│    LOAD     │                                      │ │
│  │  │              │    │              │    │              │                                      │ │
│  │  │ Prometheus   │    │ Resolve      │    │ Insert ke    │                                      │ │
│  │  │ HTTP API     │    │ service name │    │ Star Schema  │                                      │ │
│  │  │              │    │ Map labels   │    │              │                                      │ │
│  │  │ Query metrics│    │ to dimension │    │ bulk insert  │                                      │ │
│  │  └──────────────┘    └──────────────┘    └──────────────┘                                      │ │
│  │                                                                                                  │ │
│  │  Runs: Every 60 seconds (configurable)                                                         │ │
│  └─────────────────────────────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────┬───────────────────────────────────────────────────────┘
                                              │
                                              │ Scrapes Metrics
                                              ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    MONITORING STACK (Docker Compose)                                 │
│                                                                                                       │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐                        │
│  │   NGINX      │   │   POSTGRES   │   │  CADVISOR    │   │  PROMETHEUS  │                        │
│  │  (Target)    │   │  (Target DB)  │   │  (Metrics)   │   │  (TSDB)      │                        │
│  │              │   │              │   │              │   │              │                        │
│  │ Port: 8080   │   │ Port: 5433   │   │ Port: 8081   │   │ Port: 9090   │                        │
│  │ container:   │   │ container:    │   │ container:   │   │ container:   │                        │
│  │ aiops-nginx  │   │ aiops-postgres│  │ aiops-cadvisor│  │ aiops-pro-   │                        │
│  │              │   │  -target     │   │              │   │  metheus     │                        │
│  └──────┬───────┘   └──────┬───────┘   └──────┬───────┘   └──────┬───────┘                        │
│         │                  │                  │                  │                                 │
│         │                  │                  │                  │                                 │
│         ▼                  │                  │                  │                                 │
│  ┌──────────────┐         │                  │                  │                                 │
│  │   NGINX      │         │                  │                  │                                 │
│  │  EXPORTER    │         │                  │                  │                                 │
│  │              │         │                  │                  │                                 │
│  │ Port: 9113   │         │                  │                  │                                 │
│  │ Scrape:      │         │                  │                  │                                 │
│  │ /stub_status │         │                  │                  │                                 │
│  └──────────────┘         │                  │                  │                                 │
│         │                  │                  │                  │                                 │
│         │                  │                  │                  │                                 │
│         └──────────────────┴──────────────────┴──────────────────┘                                 │
│                                                 │                                                      │
│                                                 │ Scrapes Metrics                                      │
│                                                 ▼                                                      │
│                                    Prometheus scrapes from:                                           │
│                                    • nginx-exporter (port 9113)                                       │
│                                    • cadvisor (port 8081)                                             │
│                                    • postgres-target (port 5433) via exporter                        │
│                                    • prometheus self-monitoring                                       │
└────────────────────────────────────────────────────────────────────────────────────────────────────────┘

```

## Komponen Detail

### 1. Frontend (frontend-vite)
- **Tech Stack**: React + Vite
- **Port**: 5173 (dev)
- **Fitur**:
  - Dashboard dengan visualisasi metrik
  - Chat interface untuk interaksi dengan AI
  - Navigasi antar tab

### 2. AI Engine (ai-engine)
| File | Fungsi |
|------|--------|
| `api.py` | FastAPI REST API - endpoint untuk frontend |
| `agent.py` | AIOpsAgent - orchestrasi RAG + MCP + LLM |
| `rag/retriever.py` | Semantic search menggunakan ChromaDB + Ollama embeddings |
| `rag/ingest.py` | Ingest dokumen SOP/Runbook ke ChromaDB |
| `mcp_server/server.py` | MCP tools: query metrics, detect anomalies |
| `mcp_server/config.py` | Konfigurasi koneksi |

### 3. Data Engineering (data-engineering)
| File | Fungsi |
|------|--------|
| `etl_prometheus.py` | ETL Pipeline: Extract → Transform → Load |
| `ddl/warehouse_schema.sql` | Star Schema definition |

### 4. Infrastructure (Docker Compose)
| Service | Port | Deskripsi |
|---------|------|-----------|
| nginx | 8080 | Target web server yang di-monitor |
| postgres-target | 5433 | Target database |
| cadvisor | 8081 | Container metrics collector |
| prometheus | 9090 | Time-series database |
| nginx-exporter | 9113 | Nginx metrics exporter |
| postgres-warehouse | 5434 | Data warehouse (PostgreSQL) |

## Alur Data

```
1. MONITORING → PROMETHEUS
   - cAdvisor mengcollect container metrics
   - nginx-exporter mengekspos nginx metrics
   - Prometheus scrape semua metrics

2. ETL PIPELINE
   - Extract: Query metrics dari Prometheus API
   - Transform: Map ke service name, prepare star schema
   - Load: Insert ke PostgreSQL Data Warehouse

3. MCP TOOLS → DATA WAREHOUSE
   - query_historical_metrics: Ambil metrik historis
   - get_service_summary: Ringkasan status service
   - detect_anomalies: Deteksi CPU/Memory tinggi

4. RAG → CHROMADB
   - Ingest SOP/Runbook documents ke ChromaDB
   - Retrieval menggunakan semantic search

5. AI AGENT ORCHESTRATION
   - User chat → API → Agent
   - Agent determine intent → gather context (RAG/MCP)
   - Build prompt → Ollama LLM
   - Return response

```

## Technology Stack

| Layer | Technology |
|-------|------------|
| Frontend | React, Vite, CSS |
| API | FastAPI (Python) |
| AI Agent | Custom orchestration |
| LLM | Ollama (qwen3:4b-instruct) |
| Embeddings | Ollama (nomic-embed-text-v2-moe) |
| Vector DB | ChromaDB |
| Data Warehouse | PostgreSQL (Star Schema) |
| Monitoring | Prometheus, cAdvisor |
| ETL | Custom Python |
| Web Server | Nginx |

## Port Summary

| Service | Port |
|---------|------|
| Frontend (Vite) | 5173 |
| AI API (FastAPI) | 8001 |
| MCP Server (SSE) | 8000 |
| Ollama | 11434 |
| Prometheus | 9090 |
| Nginx (target) | 8080 |
| cAdvisor | 8081 |
| nginx-exporter | 9113 |
| postgres-warehouse | 5434 |

