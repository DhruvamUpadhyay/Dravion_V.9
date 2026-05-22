"""
DRAVION v.9 — Semantic Memory (ChromaDB)

Long-term knowledge store with vector similarity search.
"""
import os
import uuid
os.environ["ANONYMIZED_TELEMETRY"] = "False"
from core.config import config
from core.logger import log


class SemanticMemory:
    def __init__(self):
        self.collection = None
        persist_dir = os.path.join(config.data_dir, "chroma")

        try:
            import chromadb
            from chromadb.utils import embedding_functions

            self.client = chromadb.PersistentClient(path=persist_dir)
            self.embedding_func = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name="all-MiniLM-L6-v2"
            )
            self.collection = self.client.get_or_create_collection(
                name="dravion_memory",
                embedding_function=self.embedding_func
            )
            log.info("semantic_memory_ready", backend="chromadb")
        except Exception as e:
            log.warning("semantic_memory_unavailable", error=str(e))

    def store(self, text: str, metadata: dict = None):
        if not self.collection:
            return
        try:
            self.collection.add(
                documents=[text],
                metadatas=[metadata or {}],
                ids=[str(uuid.uuid4())]
            )
        except Exception as e:
            log.error("semantic_store_error", error=str(e))

    def search(self, query: str, n_results: int = 3) -> list:
        if not self.collection:
            return []
        try:
            results = self.collection.query(query_texts=[query], n_results=n_results)
            if results and results["documents"]:
                return [
                    {"document": doc, "metadata": meta}
                    for doc, meta in zip(results["documents"][0], results["metadatas"][0])
                ]
            return []
        except Exception as e:
            log.error("semantic_search_error", error=str(e))
            return []
