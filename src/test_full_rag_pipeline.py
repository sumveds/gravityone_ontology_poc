#!/usr/bin/env python3
"""Test the full RAG pipeline to see what's happening"""

from neo4j_graphrag.retrievers import VectorCypherRetriever
from neo4j_graphrag.generation import GraphRAG
from neo4j_graphrag.llm import OpenAILLM
from db.neo4j_client import neo4j_client
from utils.embeddings import embedder_instance
from config.settings import settings

def test_rag_pipeline():
    """Test the complete RAG pipeline step by step"""
    
    print("=== Testing Complete RAG Pipeline ===")
    
    query_text = "Who heads the Finance business unit?"
    print(f"Query: {query_text}")
    
    # Create the same components as our main code
    schema = """
    Node labels: Priority, Objective, KPI, Risk, Strategy, Project, BusinessUnit, Budget, Output, Benchmark, User
    Relationship types: HAS_OBJECTIVE, MEASURED_BY, CASCADED_TO, HAS_RISK, ENABLES, DELIVERS, OWNED_BY, HAS_BUDGET, BENCHMARKED_BY, PRODUCES, OWNS, HEADS, CONTRIBUTES_TO
    """
    
    llm = OpenAILLM(model_name="gpt-4o", model_params={"temperature": 0.0})
    
    # Test current retrieval query
    retrieval_query = """
    RETURN 
        node.name as entity_name,
        labels(node)[0] as entity_type,
        CASE WHEN node.role IS NOT NULL THEN node.role ELSE '' END as role,
        CASE WHEN node.department IS NOT NULL THEN node.department ELSE '' END as department,
        CASE WHEN node.head_id IS NOT NULL THEN node.head_id ELSE '' END as head_id,
        CASE WHEN node.user_id IS NOT NULL THEN node.user_id ELSE '' END as user_id,
        CASE WHEN node.description IS NOT NULL THEN node.description ELSE '' END as description
    """
    
    print(f"\nRetrieval query:\n{retrieval_query}")
    
    try:
        retriever = VectorCypherRetriever(
            driver=neo4j_client.driver,
            index_name="node_embeddings",
            retrieval_query=retrieval_query,
            embedder=embedder_instance.embedder
        )
        
        # Test retriever directly
        print("\n=== Testing Retriever Directly ===")
        retrieval_results = retriever.search(query_text=query_text, top_k=5)
        
        print(f"Retriever returned {len(retrieval_results.items)} results:")
        for i, item in enumerate(retrieval_results.items):
            print(f"\n{i+1}. Content: {item.content}")
            print(f"   Metadata: {item.metadata}")
        
        # Test full RAG
        print("\n=== Testing Full RAG ===")
        rag = GraphRAG(
            retriever=retriever,
            llm=llm
        )
        
        response = rag.search(query_text=query_text)
        print(f"RAG Response: {response.answer}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

def test_direct_approach():
    """Test a direct approach with embedded content"""
    
    print("\n=== Testing Direct Approach ===")
    
    # Create a retrieval query that specifically looks for Finance heads info
    direct_query = """
    WITH node
    MATCH (bu:BusinessUnit {name: 'Finance'})
    MATCH (user:User {user_id: bu.head_id})
    RETURN 
        'Finance business unit is headed by ' + user.name + ' who is a ' + user.role + ' in the ' + user.department + ' department.' as answer,
        node.name as matched_node
    UNION
    RETURN 
        node.name as entity_name,
        labels(node)[0] as entity_type,
        CASE WHEN node.role IS NOT NULL THEN 'Role: ' + node.role ELSE '' END as role_info,
        CASE WHEN node.department IS NOT NULL THEN 'Department: ' + node.department ELSE '' END as dept_info,
        CASE WHEN node.head_id IS NOT NULL THEN 'Head ID: ' + node.head_id ELSE '' END as head_info
    """
    
    try:
        retriever = VectorCypherRetriever(
            driver=neo4j_client.driver,
            index_name="node_embeddings",
            retrieval_query=direct_query,
            embedder=embedder_instance.embedder
        )
        
        retrieval_results = retriever.search(query_text="Who heads the Finance business unit?", top_k=3)
        
        print(f"Direct approach returned {len(retrieval_results.items)} results:")
        for i, item in enumerate(retrieval_results.items):
            print(f"\n{i+1}. Content: {item.content}")
            
    except Exception as e:
        print(f"Direct approach error: {e}")

if __name__ == "__main__":
    test_rag_pipeline()
    test_direct_approach() 
    neo4j_client.close()