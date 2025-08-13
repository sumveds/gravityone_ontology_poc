from neo4j import GraphDatabase
from neo4j_graphrag.embeddings import OpenAIEmbeddings
from neo4j_graphrag.llm import OpenAILLM
from neo4j_graphrag.retrievers import VectorCypherRetriever
from neo4j_graphrag.generation import GraphRAG
from config.settings import settings

import os
import signal
import sys
import threading
import time

LABELS = ["Organisation", "OrganisationGroup", "BusinessUnit", "Owner", "BusinessPlan", 
          "StrategicObjective", "StrategicOutcome", "Objective", "KPI", "Risk", 
          "Output", "Project", "Capability", "Budget"]
EMBED_PROPERTY = "name"

# ==== SETUP ====
driver = GraphDatabase.driver(settings.NEO4J_URI, auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD))
embedder = OpenAIEmbeddings(model="text-embedding-3-small", api_key=settings.OPENAI_API_KEY)
llm = OpenAILLM(model_name="gpt-5", model_params={"temperature": 1}, api_key=settings.OPENAI_API_KEY)

def reset_embeddings():
    """Remove all existing embeddings from nodes"""
    with driver.session() as session:
        result = session.run("""
            MATCH (n) 
            WHERE n.embedding IS NOT NULL 
            REMOVE n.embedding
            RETURN count(n) as cleared_count
        """)
        count = result.single()["cleared_count"]
        print(f"Cleared embeddings from {count} nodes")

def setup_vector_index():
    """Create vector index for embeddings"""
    with driver.session() as session:
        try:
            # Drop existing index if it exists
            session.run("DROP INDEX embedding_index IF EXISTS")
        except:
            pass
        
        # Get the first node label to create index (Neo4j requires a specific label)
        result = session.run("MATCH (n) RETURN DISTINCT labels(n)[0] as label LIMIT 1")
        first_record = result.single()
        
        if first_record and first_record["label"]:
            label = first_record["label"]
            # Create vector index with specific label
            session.run(f"""
                CREATE VECTOR INDEX embedding_index IF NOT EXISTS
                FOR (n:{label}) ON (n.embedding)
                OPTIONS {{
                    indexConfig: {{
                        `vector.dimensions`: 1536,
                        `vector.similarity_function`: 'cosine'
                    }}
                }}
            """)
            print(f"Created vector index 'embedding_index' for label: {label}")
        else:
            print("No nodes found to create index for")
            
        # Also create a general property index as fallback
        try:
            session.run("CREATE INDEX embedding_property IF NOT EXISTS FOR (n) ON (n.embedding)")
            print("Created property index as fallback")
        except:
            pass

def backfill_embeddings():
    with driver.session() as session:
        # Check what nodes exist first
        result = session.run("MATCH (n) RETURN count(n) as total")
        total_nodes = result.single()["total"]
        print(f"Total nodes in database: {total_nodes}")
        
        # Debug: Check what nodes exist and their properties
        result = session.run("""
            MATCH (n)
            WHERE n.name IS NOT NULL
            RETURN id(n) AS id, n.name as name, n.description as description,
                   labels(n)[0] AS label, n.embedding IS NULL as no_embedding
            LIMIT 5
        """)
        debug_nodes = list(result)
        print("Sample nodes found:")
        for node in debug_nodes:
            print(f"  - {node['label']}: {node['name']}, has_embedding: {not node['no_embedding']}")
        
        # Process all nodes that have text content and don't have embeddings
        result = session.run("""
            MATCH (n)
            WHERE n.name IS NOT NULL AND n.embedding IS NULL
            RETURN id(n) AS id, 
                   n.name + CASE WHEN n.description IS NOT NULL 
                                 THEN ': ' + n.description 
                                 ELSE '' END AS text,
                   labels(n)[0] AS label
            LIMIT 1000
        """)
        
        nodes = list(result)
        print(f"Processing {len(nodes)} nodes for embeddings...")
        
        for i, rec in enumerate(nodes):
            node_id, text, label = rec["id"], rec["text"], rec["label"]
            print(f"  {i+1}/{len(nodes)} Processing {label}: {text[:50]}...")
            try:
                embedding = embedder.embed_query(text)
                session.run(
                    "MATCH (n) WHERE id(n) = $id SET n.embedding = $embedding",
                    {"id": node_id, "embedding": embedding}
                )
                print(f"    ✅ Embedded successfully")
            except Exception as e:
                print(f"    ❌ Error: {e}")

class Spinner:
    def __init__(self, message="Processing"):
        self.message = message
        self.spinner_chars = "|/-\\"
        self.idx = 0
        self.stop_spinner = False
        self.spinner_thread = None

    def spin(self):
        while not self.stop_spinner:
            print(f"\r{self.message} {self.spinner_chars[self.idx % len(self.spinner_chars)]}", end="", flush=True)
            self.idx += 1
            time.sleep(0.1)

    def start(self):
        self.stop_spinner = False
        self.spinner_thread = threading.Thread(target=self.spin)
        self.spinner_thread.start()

    def stop(self):
        self.stop_spinner = True
        if self.spinner_thread:
            self.spinner_thread.join()
        print("\r" + " " * (len(self.message) + 2) + "\r", end="", flush=True)

def signal_handler(sig, frame):
    print("\n\nGracefully shutting down...")
    driver.close()
    sys.exit(0)

def start_chatbot():
    # Set up signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    
    # Check if vector index exists
    with driver.session() as session:
        result = session.run("SHOW INDEXES")
        indexes = [record["name"] for record in result if "embedding" in record["name"]]
        print(f"Available indexes: {indexes}")
        
        if not indexes:
            print("❌ No embedding index found. Creating a simple one...")
            # Try to create a simple vector index for Organisation nodes
            try:
                session.run("""
                    CREATE VECTOR INDEX simple_embedding_index IF NOT EXISTS
                    FOR (n:Organisation) ON (n.embedding)
                    OPTIONS {
                        indexConfig: {
                            `vector.dimensions`: 1536,
                            `vector.similarity_function`: 'cosine'
                        }
                    }
                """)
                index_name = "simple_embedding_index"
                print(f"Created simple index: {index_name}")
            except Exception as e:
                print(f"Failed to create index: {e}")
                return
        else:
            index_name = indexes[0]
            print(f"Using existing index: {index_name}")
    
    # Prepare the retriever with a custom query for your business ontology
    retrieval_query = """
    MATCH (n)-[r]-(m)
    WHERE n.embedding IS NOT NULL
    WITH n, r, m, score
    RETURN n.name + CASE 
             WHEN n.description IS NOT NULL THEN ': ' + n.description 
             WHEN n.type IS NOT NULL THEN ' (Type: ' + n.type + ')'
             WHEN n.domain IS NOT NULL THEN ' (Domain: ' + n.domain + ')'
             WHEN n.status IS NOT NULL THEN ' (Status: ' + n.status + ')'
             ELSE '' 
           END AS text,
           type(r) + ' -> ' + coalesce(m.name, m.org_id, m.bu_id, m.project_id, '') AS relationships,
           labels(n)[0] AS node_type,
           score
    ORDER BY score DESC
    LIMIT 5
    """
    
    try:
        retriever = VectorCypherRetriever(
            driver=driver,
            index_name=index_name,
            embedder=embedder,
            retrieval_query=retrieval_query
        )
    except Exception as e:
        print(f"Failed to create retriever: {e}")
        return

    rag = GraphRAG(
        retriever=retriever,
        llm=llm
    )

    print("\nReady! Ask a business question (type 'exit' to quit):")
    while True:
        query = input("\n> ")
        if query.strip().lower() in ("exit", "quit"):
            break
        try:
            spinner = Spinner("🤔 Thinking")
            spinner.start()
            response = rag.search(query_text=query, retriever_config={"top_k": 10})
            spinner.stop()
            print("\n---\nAnswer:\n", response.answer)
        except Exception as e:
            if 'spinner' in locals():
                spinner.stop()
            print("Error answering your question:", e)

if __name__ == "__main__":
    import sys
    
    # Check for reset flag
    if len(sys.argv) > 1 and sys.argv[1] == '--reset':
        print("Step 0: Resetting embeddings...")
        reset_embeddings()
    
    print("Step 1: Setting up vector index...")
    setup_vector_index()
    print("Step 2: Creating embeddings for all eligible nodes in Neo4j ...")
    backfill_embeddings()
    print("Step 3: Starting GraphRAG Q&A chatbot ...")
    start_chatbot()
    driver.close()
