import signal
import sys
from db.neo4j_client import neo4j_client
from nlp.query_converter import query_converter
from utils.logger import logger

def signal_handler(sig, frame):
    print("\n\nExiting gracefully...")
    logger.info("Application terminated by user")
    neo4j_client.close()
    sys.exit(0)

async def initialize_database():
    # Only run once for initial ingestion, or check if KG exists first
    # For demo, let's use a sample file or string.
    # await neo4j_client.ingest_with_graphrag(file_path="sample_domain_data.pdf")
    logger.info("Database initialized and KG built/updated.")

def run_chatbot():
    print("Welcome to Gravity One Chatbot! Type 'exit' to quit.")
    while True:
        query = input("Enter your business question: ").strip()
        if query.lower() == 'exit':
            break

        # print("\n" + "="*60)
        # print(f"Your Question: {query}")
        # print("="*60)

        # --- Use GraphRAG pipeline ---
        try:
            answer = query_converter.search_with_rag(query)
            # print("\nGraphRAG Answer:")
            # print("-" * 40)
            print(f"\nAnswer: {answer}")
            # print(answer)
            # print("-" * 40)
        except Exception as e:
            print(f"\nError with GraphRAG retrieval: {e}")

        # Optional: Also show the Cypher query and raw DB output
        # cypher_query = query_converter.convert_to_cypher(query)
        # print("\nGenerated Cypher Query:")
        # print(cypher_query)
        # try:
        #     results = neo4j_client.execute_query(cypher_query)
        #     if results:
        #         print("\nRaw Cypher Results:")
        #         for i, result in enumerate(results, 1):
        #             print(f"{i}. ", end="")
        #             print(" | ".join(f"{k}: {v}" for k, v in result.items()))
        #     else:
        #         print("No results for this Cypher query.")
        # except Exception as e:
        #     print(f"Cypher query error: {e}")

        print()

import asyncio

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    async def main():
        try:
            await initialize_database()
            run_chatbot()
        except Exception as e:
            logger.error(f"Error: {e}")
        finally:
            neo4j_client.close()
    
    asyncio.run(main())