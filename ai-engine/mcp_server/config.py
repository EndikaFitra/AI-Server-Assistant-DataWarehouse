"""
MCP Server Configuration — AIOps
Konfigurasi koneksi ke Data Warehouse dan Ollama.
"""

# ── Data Warehouse Connection ──
WAREHOUSE_CONFIG = {
    "host": "192.168.163.128",
    "port": 5434,
    "database": "warehouse_db",
    "user": "admin",
    "password": "pass",
}

# ── Ollama Configuration ──
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_LLM_MODEL = "qwen3:4b-instruct"
OLLAMA_EMBED_MODEL = "nomic-embed-text-v2-moe:latest"

# ── MCP Server ──
MCP_SERVER_HOST = "0.0.0.0"
MCP_SERVER_PORT = 8000

# ── ChromaDB ──
CHROMA_PERSIST_DIR = "./chroma_data"
CHROMA_COLLECTION_NAME = "aiops_sop_runbook"

# ── Documents Path ──
DOCUMENTS_DIR = "./documents"
