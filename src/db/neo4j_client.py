from neo4j import GraphDatabase, Driver
from neo4j_graphrag.experimental.pipeline.kg_builder import SimpleKGPipeline
from neo4j_graphrag.llm import OpenAILLM
from neo4j_graphrag.embeddings import OpenAIEmbeddings
from config.settings import settings
from utils.logger import logger
from typing import Any, Optional, List

class Neo4jClient:
    def __init__(self):
        self.driver: Driver = GraphDatabase.driver(
            settings.NEO4J_URI, auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
        )
        self._verify_connection()

    def _verify_connection(self) -> None:
        with self.driver.session() as session:
            session.run("RETURN 1 AS test")
        logger.info("Neo4j connection established")

    def close(self) -> None:
        self.driver.close()
        logger.info("Neo4j connection closed")

    def execute_query(self, query: str, params: dict = None) -> List[dict]:
        with self.driver.session() as session:
            result = session.run(query, params or {})
            return [dict(record) for record in result]

    async def ingest_with_graphrag(self, file_path: str = None, text_content: str = None):
        """
        Ingests data using GraphRAG's SimpleKGPipeline to build/enhance the KG.
        Supports file (e.g., PDF with entity descriptions) or direct text.
        This adds nodes, relationships, and embeddings to the existing Neo4j graph.
        """
        
        try:
            llm = OpenAILLM(model_name="gpt-4o", model_params={"temperature": 0.0, "response_format": {"type": "json_object"}})
            embedder = OpenAIEmbeddings(model="text-embedding-3-small")

            # Define schema based on our ontology (node labels and rel types)
            node_labels = [
                "Priority", "Objective", "KPI", "Risk", "Strategy", "Project", "BU", "Budget", "Output", "Benchmark"
            ]
            rel_types = [
                "HAS_OBJECTIVE", "MEASURED_BY", "CASCADED_TO", "DELIVERED_BY", "LINKED_TO", "ENABLES", "OWNED_BY",
                "ALLOCATED_TO", "BENCHMARKED_BY", "PRODUCES"
            ]

            # Custom prompt template for entity extraction aligned to our domain
            prompt_template = '''
            You are a strategic planning expert extracting entities and relationships from text about organizational priorities, objectives, KPIs, risks, strategies, projects, business units, budgets, outputs, and benchmarks.
            Extract nodes with types from: {node_labels}
            Extract relationships from: {rel_types}
            Include attributes like name, description, status, progress, etc., as properties.
            Return as JSON: {{"nodes": [ {{"id": "unique_id", "label": "NodeType", "properties": {{"name": "value", ...}} }} ], "relationships": [ {{"type": "REL_TYPE", "start_node_id": "id", "end_node_id": "id", "properties": {{...}} }} ] }}
            Use only the provided schema. Reuse node IDs for relationships. If text is empty, return empty JSON.
            '''.format(node_labels=', '.join(node_labels), rel_types=', '.join(rel_types))

            pipeline = SimpleKGPipeline(
                driver=self.driver,
                llm=llm,
                embedder=embedder,
                from_pdf=bool(file_path)
            )

            if file_path:
                result = await pipeline.run_async(file_path=file_path)
            elif text_content:
                # For text content, create pipeline with from_pdf=False
                text_pipeline = SimpleKGPipeline(
                    driver=self.driver,
                    llm=llm,
                    embedder=embedder,
                    from_pdf=False
                )
                result = await text_pipeline.run_async(text=text_content)
            else:
                raise ValueError("Provide file_path or text_content for ingestion.")

            logger.info("GraphRAG ingestion completed; KG enhanced with new nodes/rels/embeddings.")
        except Exception as e:
            logger.error(f"GraphRAG ingestion error: {e}")
            raise

    def _chunk_text(self, text: str, chunk_size: int = 2000, overlap: int = 400) -> List[str]:
        """Simple text chunker for direct ingestion."""
        chunks = []
        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunks.append(text[start:end])
            start = end - overlap
        return chunks

# Singleton instance
neo4j_client = Neo4jClient()