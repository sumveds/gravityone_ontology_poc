#!/usr/bin/env python3
"""Test what our retrieval query actually returns"""

from db.neo4j_client import neo4j_client
from utils.embeddings import embedder_instance

def test_retrieval_query():
    """Test the exact retrieval query we're using"""
    
    print("=== Testing Our Retrieval Query ===")
    
    # The exact query from our VectorCypherRetriever
    retrieval_query = """
    MATCH (node)-[:HAS_EMBEDDING]->(embedding:EmbeddedNode)
    RETURN 
        node.name as entity_name,
        labels(node)[0] as entity_type,
        embedding.text_content as full_context,
        CASE WHEN node.role IS NOT NULL THEN node.role ELSE '' END as role,
        CASE WHEN node.department IS NOT NULL THEN node.department ELSE '' END as department
    LIMIT 5
    """
    
    try:
        results = neo4j_client.execute_query(retrieval_query)
        print(f"Retrieval query returned {len(results)} results:")
        
        for i, result in enumerate(results):
            print(f"\n{i+1}. {result['entity_name']} ({result['entity_type']})")
            print(f"   Role: {result['role']}")
            print(f"   Department: {result['department']}")
            print(f"   Full Context: {result['full_context']}")
            
    except Exception as e:
        print(f"Retrieval query failed: {e}")

def test_simple_context_query():
    """Test a simpler approach that directly provides the answer"""
    
    print("\n=== Testing Simpler Context Query ===")
    
    # Query that directly finds who heads Finance
    simple_query = """
    MATCH (user:User)-[:HEADS]->(bu:BusinessUnit {name: 'Finance'})
    RETURN 
        user.name as user_name,
        user.role as user_role,
        bu.name as unit_name,
        'heads' as relationship
    UNION
    MATCH (bu:BusinessUnit {name: 'Finance'})
    MATCH (user:User {user_id: bu.head_id})
    RETURN 
        user.name as user_name,
        user.role as user_role,
        bu.name as unit_name,
        'heads via head_id' as relationship
    """
    
    try:
        results = neo4j_client.execute_query(simple_query)
        print(f"Simple query returned {len(results)} results:")
        
        for result in results:
            print(f"  {result['user_name']} ({result['user_role']}) {result['relationship']} {result['unit_name']}")
            
    except Exception as e:
        print(f"Simple query failed: {e}")

def test_embedding_with_finance():
    """Check embeddings that mention both Finance and heads/Alex"""
    
    print("\n=== Testing Embeddings with Finance Context ===")
    
    query = """
    MATCH (e:EmbeddedNode)
    WHERE e.text_content CONTAINS 'Finance' 
      AND (e.text_content CONTAINS 'Alex' OR e.text_content CONTAINS 'head' OR e.text_content CONTAINS 'Head')
    RETURN 
        e.name as name,
        e.text_content as content
    """
    
    try:
        results = neo4j_client.execute_query(query)
        print(f"Found {len(results)} Finance+Alex/head embeddings:")
        
        for result in results:
            print(f"\n  {result['name']}:")
            print(f"    {result['content']}")
            
    except Exception as e:
        print(f"Embedding query failed: {e}")

if __name__ == "__main__":
    test_retrieval_query()
    test_simple_context_query()
    test_embedding_with_finance()
    neo4j_client.close()