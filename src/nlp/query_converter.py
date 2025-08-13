from openai import OpenAI
from config.settings import settings
from utils.logger import logger

from neo4j_graphrag.retrievers import VectorCypherRetriever
from neo4j_graphrag.generation import GraphRAG
from neo4j_graphrag.llm import OpenAILLM
from db.neo4j_client import neo4j_client
from utils.embeddings import embedder_instance

class QueryConverter:
    def __init__(self):
        try:
            self.client = OpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None
        except Exception as e:
            logger.warning(f"Failed to initialize OpenAI client: {e}")
            self.client = None

    def convert_to_cypher(self, natural_query: str) -> str:
        if not self.client:
            logger.warning("No API key; using hardcoded mapping")
            return self._hardcoded_mapping(natural_query)

        prompt = f"""
        Convert the following natural language query into a Cypher query for a Neo4j knowledge graph with entities: Priority, Objective, KPI, Risk, Strategy, Project, BusinessUnit (BU), Budget, Output, Benchmark, and relationships: HAS_OBJECTIVE, MEASURED_BY, CASCADED_TO, DELIVERED_BY, LINKED_TO, ENABLES, OWNED_BY, ALLOCATED_TO, BENCHMARKED_BY, PRODUCES.
        Query: "{natural_query}"
        Return only the Cypher query string.
        """
        response = self.client.chat.completions.create(
            model="gpt-4o",  # Adjusted to valid model name
            messages=[{"role": "user", "content": prompt}]
        )
        cypher_query = response.choices[0].message.content.strip()
        # Remove markdown code blocks if present
        if "```cypher" in cypher_query:
            cypher_query = cypher_query.split("```cypher")[1].split("```")[0].strip()
        elif "```" in cypher_query:
            cypher_query = cypher_query.split("```")[1].split("```")[0].strip()
        cypher_query = cypher_query.strip()
        logger.info(f"Converted '{natural_query}' to Cypher: {cypher_query}")
        return cypher_query

    def _hardcoded_mapping(self, natural_query: str) -> str:
        # Simple mapping for fallback; expand as needed
        mappings = {
            "What is the total planned budget for Operations BU?": "MATCH (bu:BU {name: 'Operations'})<-[:OWNED_BY]-(pr:Project)<-[:ALLOCATED_TO]-(b:Budget) RETURN bu.name AS BusinessUnit, sum(b.planned) AS TotalPlannedBudget",
            "Which projects are off track?": "MATCH (pr:Project {status: 'Delayed'}) RETURN pr.name AS Project, pr.progress AS Progress"
        }
        return mappings.get(natural_query, "MATCH (n) RETURN n LIMIT 1")  # Fallback

    def search_with_rag(self, natural_query: str) -> str:
        if not self.client:
            return self._hardcoded_mapping(natural_query)

        # Updated schema with all relationship types including HEADS
        schema = """
        Node labels: Priority, Objective, KPI, Risk, Strategy, Project, BusinessUnit, Budget, Output, Benchmark, User
        Relationship types: HAS_OBJECTIVE, MEASURED_BY, CASCADED_TO, HAS_RISK, ENABLES, DELIVERS, OWNED_BY, HAS_BUDGET, BENCHMARKED_BY, PRODUCES, OWNS, HEADS, CONTRIBUTES_TO
        """

        llm = OpenAILLM(model_name="gpt-4o", model_params={"temperature": 0.0})
        
        # Use VectorCypherRetriever with retrieval query that returns the embedded content
        # The 'node' variable represents the EmbeddedNode from vector search
        retrieval_query = """
        RETURN 
            node.name as entity_name,
            node.text_content as full_context
        """
        
        retriever = VectorCypherRetriever(
            driver=neo4j_client.driver,
            index_name="node_embeddings",
            retrieval_query=retrieval_query,
            embedder=embedder_instance.embedder
        )

        rag = GraphRAG(
            retriever=retriever,
            llm=llm
        )

        response = rag.search(
            query_text=natural_query
        )
        # logger.info(f"RAG response for '{natural_query}': {response.answer}")
        return response.answer

query_converter = QueryConverter()