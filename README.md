# AIOps - AI-Powered Operations Dashboard

AIOps is an intelligent operations dashboard that combines AI agents with infrastructure monitoring to provide automated troubleshooting and insights.
(This project is only demo)

## Architecture Overview

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Frontend   │────▶│  AI Engine   │────▶│   Ollama     │
│  (Vite+React)│     │  (FastAPI)   │     │   (LLM)      │
└──────────────┘     └──────┬───────┘     └──────────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │  Chroma  │ │   MCP    │ │   PostgreSQL
        │   (RAG)  │ │  Server  │ │ Warehouse
        └──────────┘ └──────────┘ └──────────┘
```

## Tech Stack

| Component | Technology |
|-----------|------------|
| Frontend | React, Vite |
| API | FastAPI |
| AI Agent | Custom orchestration |
| LLM | Ollama (qwen3:4b-instruct) |
| Embeddings | Ollama (nomic-embed-text-v2-moe) |
| Vector DB | ChromaDB |
| Data Warehouse | PostgreSQL (Star Schema) |
| Monitoring | Prometheus, cAdvisor |
| ETL | Custom Python |

## Prerequisites

- **Ollama** must be running with models:
  - `qwen3:4b-instruct`
  - `nomic-embed-text-v2-moe`
- **Docker & Docker Compose**
- **Python 3.10+**

## Quick Start

### 1. Start Infrastructure (Docker Compose)

```bash
docker-compose up -d
```

This starts:
- Nginx (port 8080)
- PostgreSQL Target (port 5433)
- cAdvisor (port 8081)
- Prometheus (port 9090)
- nginx-exporter (port 9113)
- PostgreSQL Warehouse (port 5434)

### 2. Install Python Dependencies

```bash
cd ai-engine
pip install -r requirements.txt

cd ../data-engineering
pip install -r requirements.txt
```

### 3. Install Frontend Dependencies

```bash
cd frontend-vite
npm install
```

### 4. Start Ollama

Make sure Ollama is running and models are installed:

```bash
# Start Ollama server
ollama serve

# In another terminal, pull required models
ollama pull qwen3:4b-instruct
ollama pull nomic-embed-text-v2-moe
```

### 5. Run ETL Pipeline

```bash
cd data-engineering
python etl_prometheus.py
```

### 6. Run AI Engine

```bash
cd ai-engine
python -m uvicorn api:app --host 0.0.0.0 --port 8001
```

### 7. Run Frontend

```bash
cd frontend-vite
npm run dev
```

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

## Project Structure

```
.
├── .gitignore                 # Git ignore rules
├── README.md                  # This file
├── docker-compose.yml         # Infrastructure stack
│
├── ai-engine/                 # AI & RAG Engine
│   ├── api.py                 # FastAPI REST API
│   ├── agent.py               # AIOps Agent orchestration
│   ├── requirements.txt       # Python dependencies
│   ├── rag/
│   │   ├── retriever.py       # ChromaDB semantic search
│   │   └── ingest.py          # Document ingestion
│   ├── mcp_server/
│   │   ├── server.py          # MCP tools server
│   │   └── config.py          # Configuration
│   └── documents/             # SOP/Runbook documents
│
├── data-engineering/          # ETL & Data Pipeline
│   ├── etl_prometheus.py      # Prometheus → Warehouse ETL
│   ├── load_simulator.py     # Load testing simulator
│   ├── requirements.txt       # Python dependencies
│   └── ddl/
│       └── warehouse_schema.sql  # Star Schema DDL
│
├── frontend-vite/             # React Frontend
│   ├── src/
│   │   ├── App.jsx            # Main app component
│   │   ├── components/        # React components
│   │   │   ├── DashboardTab.jsx
│   │   │   ├── ChatTab.jsx
│   │   │   ├── Header.jsx
│   │   │   └── Sidebar.jsx
│   │   └── styles/            # CSS styles
│   └── package.json           # Node dependencies
│
└── infrastructure/            # Infrastructure configs
    ├── nginx/
    │   └── nginx.conf         # Nginx configuration
    ├── postgres/
    │   └── init.sql           # Target DB init script
    └── prometheus/
        └── prometheus.yml     # Prometheus scrape config
```

## Usage

### Chat with AI Assistant

Access the frontend at `http://localhost:5173` and use the Chat tab to ask questions like:
- "What should I do if CPU is high?"
- "Show me service status summary"
- "Detect any anomalies in the system"

### View Dashboard

Navigate to the Dashboard tab to see real-time metrics visualization.

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/api/chat` | POST | Chat with AI |
| `/api/chat/reset` | POST | Reset conversation |
| `/api/status` | GET | System status summary |

## MCP Tools

The MCP server provides:
- `query_historical_metrics` - Query metrics from warehouse
- `get_service_summary` - Get latest metrics per service
- `detect_anomalies` - Detect CPU/Memory anomalies

## License

MIT

