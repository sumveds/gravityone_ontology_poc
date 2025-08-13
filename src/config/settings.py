import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

class Settings:
    NEO4J_URI: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER: str = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD: str = os.getenv("NEO4J_PASSWORD", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"

settings = Settings()