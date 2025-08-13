from neo4j_graphrag.embeddings import OpenAIEmbeddings
from config.settings import settings
from utils.logger import logger
from typing import List

class Embedder:
    def __init__(self):
        self.embedder = OpenAIEmbeddings(model="text-embedding-3-small")  # Smaller model for efficiency; adjust as needed

    def embed_text(self, text: str) -> List[float]:
        try:
            return self.embedder.embed_query(text)
        except Exception as e:
            logger.error(f"Embedding error: {e}")
            return []

embedder_instance = Embedder()