"""
AI Agent — AIOps Infrastructure Reliability
Orchestrator yang menggabungkan:
- RAG (ChromaDB) untuk SOP/Runbook lookup
- MCP tools untuk query Data Warehouse
- Ollama LLM (qwen3:4b-instruct) untuk reasoning

Agent ini dipanggil oleh api.py untuk melayani pertanyaan user.
"""

import os
import sys
import json

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from mcp_server.config import OLLAMA_BASE_URL, OLLAMA_LLM_MODEL
from rag.retriever import RAGRetriever


class AIOpsAgent:
    def __init__(self):
        self.retriever = RAGRetriever()
        self.system_prompt = """Kamu adalah AIOps Assistant, sebuah AI yang membantu tim operasional infrastruktur.

Tugasmu:
1. Menjawab pertanyaan tentang status dan performa infrastruktur berdasarkan DATA METRIK yang diberikan.
2. Mendeteksi anomali dan memberikan analisis berdasarkan data historis.
3. Memberikan solusi dan rekomendasi berdasarkan SOP/Runbook internal yang tersedia.
4. Menjelaskan konsep monitoring dan infrastruktur dengan bahasa yang mudah dipahami.

Aturan:
- Selalu gunakan data faktual yang diberikan dalam konteks, DILARANG KERAS mengarang data.
- Jika tidak ada data yang relevan, katakan dengan jujur.
- Berikan jawaban dalam Bahasa Indonesia.
- Sertakan langkah-langkah konkret jika diminta solusi.
- Format jawaban menggunakan markdown untuk keterbacaan yang baik.
"""
        self.conversation_history = []

        # Persistent HTTP session with retry logic for Ollama
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[502, 503, 504],
            allowed_methods=["POST"],
        )
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=1,
            pool_maxsize=1,
        )
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def _call_ollama(self, messages: list) -> str:
        """Kirim request ke Ollama API dengan retry logic."""
        try:
            resp = self.session.post(
                f"{OLLAMA_BASE_URL}/api/chat",
                json={
                    "model": OLLAMA_LLM_MODEL,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,
                        "top_p": 0.9,
                        "num_predict": 2048,
                    },
                },
                timeout=(10, 300),  # (connect_timeout, read_timeout)
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("message", {}).get("content", "Maaf, saya tidak bisa menghasilkan respons.")

        except requests.ConnectionError as e:
            return f"❌ Tidak dapat terhubung ke Ollama di `{OLLAMA_BASE_URL}`. Pastikan Ollama sedang berjalan.\n\n```\n{e}\n```"
        except requests.Timeout:
            return "❌ Ollama timeout — model membutuhkan waktu terlalu lama. Coba pertanyaan yang lebih singkat."
        except requests.RequestException as e:
            return f"❌ Error berkomunikasi dengan Ollama: {str(e)}"

    def _call_mcp_tool(self, tool_name: str, params: dict) -> str:
        """Panggil MCP tool secara langsung (internal call, tanpa melalui MCP client)."""
        # Import tools langsung untuk internal use
        from mcp_server.server import query_historical_metrics, get_service_summary, detect_anomalies

        tool_map = {
            "query_historical_metrics": query_historical_metrics,
            "get_service_summary": get_service_summary,
            "detect_anomalies": detect_anomalies,
        }

        tool_fn = tool_map.get(tool_name)
        if not tool_fn:
            return json.dumps({"error": f"Unknown tool: {tool_name}"})

        return tool_fn(**params)

    def _determine_intent(self, query: str) -> dict:
        """Tentukan intent user dan tool yang perlu dipanggil."""
        query_lower = query.lower()

        intent = {
            "needs_rag": False,
            "needs_metrics": False,
            "needs_anomaly": False,
            "needs_summary": False,
            "service_filter": "",
        }

        # Keywords untuk RAG (SOP/Runbook)
        rag_keywords = [
            "sop", "runbook", "cara", "bagaimana", "solusi", "langkah",
            "prosedur", "troubleshoot", "perbaiki", "handle", "atasi",
            "penanganan", "panduan", "guide",
        ]
        if any(kw in query_lower for kw in rag_keywords):
            intent["needs_rag"] = True

        # Keywords untuk anomaly detection
        anomaly_keywords = [
            "anomali", "anomaly", "masalah", "problem", "error", "down",
            "spike", "tinggi", "high", "warning", "alert", "deteksi",
        ]
        if any(kw in query_lower for kw in anomaly_keywords):
            intent["needs_anomaly"] = True

        # Keywords untuk historical metrics
        metrics_keywords = [
            "metrik", "metric", "cpu", "memory", "network", "disk",
            "traffic", "request", "connection", "data", "historis",
            "trend", "grafik", "usage", "performa", "performance",
        ]
        if any(kw in query_lower for kw in metrics_keywords):
            intent["needs_metrics"] = True

        # Keywords untuk summary
        summary_keywords = [
            "status", "ringkasan", "summary", "overview", "semua service",
            "kondisi", "keadaan", "saat ini", "current",
        ]
        if any(kw in query_lower for kw in summary_keywords):
            intent["needs_summary"] = True

        # Detect service filter
        services = ["nginx", "postgres", "cadvisor", "prometheus"]
        for svc in services:
            if svc in query_lower:
                intent["service_filter"] = svc
                break

        # Default: jika tidak ada intent terdeteksi, coba RAG
        if not any([intent["needs_rag"], intent["needs_metrics"],
                    intent["needs_anomaly"], intent["needs_summary"]]):
            intent["needs_rag"] = True

        import logging
        logger = logging.getLogger("aiops.agent")
        
        # Log hasil akhir penentuan intent dan tool yang akan dipanggil
        logger.info(f"Analyzed query: '{query}'")
        tools_to_call = []
        if intent["needs_rag"]: tools_to_call.append("RAG (SOP/Runbook)")
        if intent["needs_summary"]: tools_to_call.append("get_service_summary")
        if intent["needs_metrics"]: tools_to_call.append("query_historical_metrics")
        if intent["needs_anomaly"]: tools_to_call.append("detect_anomalies")
        
        logger.info(f"Tools that will be called: {', '.join(tools_to_call)}")
        if intent["service_filter"]:
            logger.info(f"Service filter applied: {intent['service_filter']}")

        return intent

    def process_query(self, query: str) -> str:
        """
        Proses pertanyaan user — orkestrasi RAG + MCP + LLM.

        Returns:
            Jawaban AI dalam format string (markdown).
        """
        import logging
        logger = logging.getLogger("aiops.agent")

        # 1. Determine intent
        intent = self._determine_intent(query)
        logger.info(f"Intent detected: {intent}")

        # 2. Gather context dari berbagai sumber
        context_parts = []

        # ── ALWAYS fetch service summary as baseline context ──
        # This ensures the AI always knows the current server state
        try:
            summary = self._call_mcp_tool("get_service_summary", {})
            context_parts.append(f"### Status Service Terkini:\n```json\n{summary}\n```")
            logger.info("Service summary fetched successfully")
        except Exception as e:
            logger.error(f"Service summary failed: {e}")
            context_parts.append(f"[Service Summary Error: {e}]")

        # RAG context
        if intent["needs_rag"]:
            try:
                rag_results = self.retriever.retrieve(query, top_k=3)
                rag_context = self.retriever.format_context(rag_results)
                context_parts.append(f"### Dokumen SOP/Runbook Relevan:\n{rag_context}")
            except Exception as e:
                logger.error(f"RAG retrieval failed: {e}")
                context_parts.append(f"[RAG Error: {e}]")

        # Historical metrics (only if intent requires it, since we already have summary)
        if intent["needs_metrics"]:
            try:
                params = {"hours_back": 1, "limit": 20}
                if intent["service_filter"]:
                    params["service_name"] = intent["service_filter"]
                metrics = self._call_mcp_tool("query_historical_metrics", params)
                context_parts.append(f"### Data Metrik Historis:\n```json\n{metrics}\n```")
            except Exception as e:
                logger.error(f"Historical metrics failed: {e}")
                context_parts.append(f"[Metrics Error: {e}]")

        # Anomaly detection
        if intent["needs_anomaly"]:
            try:
                params = {"hours_back": 1}
                if intent["service_filter"]:
                    params["service_name"] = intent["service_filter"]
                anomalies = self._call_mcp_tool("detect_anomalies", params)
                context_parts.append(f"### Hasil Deteksi Anomali:\n```json\n{anomalies}\n```")
            except Exception as e:
                logger.error(f"Anomaly detection failed: {e}")
                context_parts.append(f"[Anomaly Detection Error: {e}]")

        # 3. Build prompt
        full_context = "\n\n".join(context_parts) if context_parts else "Tidak ada data konteks tersedia."

        messages = [
            {"role": "system", "content": self.system_prompt},
        ]

        # Add conversation history (last 6 messages for context window management)
        for msg in self.conversation_history[-6:]:
            messages.append(msg)

        # User message with context
        user_message = f"""Pertanyaan User: {query}

Berikut adalah data dan konteks yang tersedia untuk menjawab pertanyaan di atas:

{full_context}

INSTRUKSI PENTING:
1. Jika terdapat "Dokumen SOP/Runbook Relevan" pada konteks di atas, Anda WAJIB menggunakan langkah-langkah dari dokumen tersebut sebagai referensi utama untuk memberikan solusi atau panduan.
2. Sebutkan sumber dokumen (SOP/Runbook) yang Anda gunakan saat memformulasikan jawaban.
3. Gunakan sisa data (Status Service, Metrik Historis, Anomali) untuk memberikan konteks spesifik terhadap masalah yang sedang terjadi.
4. Berikan jawaban yang komprehensif, terstruktur, dan format dengan Markdown."""

        messages.append({"role": "user", "content": user_message})

        # 4. Call LLM
        response = self._call_ollama(messages)

        # 5. Update conversation history
        self.conversation_history.append({"role": "user", "content": query})
        self.conversation_history.append({"role": "assistant", "content": response})

        return response

    def reset_conversation(self):
        """Reset riwayat percakapan."""
        self.conversation_history = []


# Quick test
if __name__ == "__main__":
    agent = AIOpsAgent()

    test_queries = [
        "Apa status semua service saat ini?",
        "Bagaimana cara menangani CPU tinggi pada Nginx?",
        "Apakah ada anomali di infrastruktur dalam 1 jam terakhir?",
    ]

    for q in test_queries:
        print(f"\n{'=' * 60}")
        print(f"Q: {q}")
        print(f"{'=' * 60}")
        answer = agent.process_query(q)
        print(answer)
