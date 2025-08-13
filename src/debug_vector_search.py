#!/usr/bin/env python3
"""Debug vector search to see what context is being retrieved"""

from db.neo4j_client import neo4j_client
from utils.embeddings import embedder_instance

def test_vector_search():
    """Test what our vector search returns for the Finance question"""
    
    print("=== Testing Vector Search for 'Who heads the Finance business unit?' ===")
    
    # Test the exact query our embedder would generate
    query_text = "Who heads the Finance business unit?"
    embedding = embedder_instance.embed_text(query_text)
    
    print(f"Query: {query_text}")
    print(f"Embedding length: {len(embedding) if embedding else 0}")
    
    # Test vector similarity search
    vector_search_query = """
    CALL db.index.vector.queryNodes('node_embeddings', 5, $embedding)
    YIELD node, score
    RETURN 
        node.name as name,
        node.labels as labels,
        node.text_content as content,
        score
    ORDER BY score DESC
    """
    
    try:
        results = neo4j_client.execute_query(vector_search_query, {'embedding': embedding})
        print(f"\nTop vector search results:")
        
        for i, result in enumerate(results[:5]):
            print(f"\n{i+1}. {result['name']} (Score: {result['score']:.4f})")
            print(f"   Labels: {result['labels']}")
            print(f"   Content: {result['content'][:200]}...")
            
    except Exception as e:
        print(f"Vector search failed: {e}")

def test_heads_relationships():
    """Test if HEADS relationships exist and are accessible"""
    
    print("\n=== Testing HEADS Relationships ===")
    
    query = """
    MATCH (user)-[:HEADS]->(unit)
    RETURN 
        user.name as user_name,
        user.role as user_role,
        unit.name as unit_name,
        labels(unit) as unit_labels
    """
    
    try:
        results = neo4j_client.execute_query(query)
        print(f"Found {len(results)} HEADS relationships:")
        
        for rel in results:
            print(f"  {rel['user_name']} ({rel['user_role']}) HEADS {rel['unit_name']} ({rel['unit_labels']})")
            
    except Exception as e:
        print(f"HEADS query failed: {e}")

def test_finance_nodes():
    """Test what Finance-related nodes exist"""
    
    print("\n=== Testing Finance-related Nodes ===")
    
    # Search for anything with 'Finance' in name or properties
    query = """
    MATCH (n)
    WHERE n.name CONTAINS 'Finance' 
       OR n.department CONTAINS 'Finance'
       OR any(label in labels(n) WHERE label CONTAINS 'Finance')
    RETURN 
        n.name as name,
        labels(n) as labels,
        n.department as department,
        properties(n) as props
    """
    
    try:
        results = neo4j_client.execute_query(query)
        print(f"Found {len(results)} Finance-related nodes:")
        
        for node in results:
            print(f"  {node['name']} ({node['labels']}) - Dept: {node.get('department', 'N/A')}")
            
    except Exception as e:
        print(f"Finance search failed: {e}")

def test_embedding_content():
    """Test what's in our embeddings"""
    
    print("\n=== Testing Embedding Content ===")
    
    query = """
    MATCH (embedded:EmbeddedNode)
    WHERE embedded.text_content CONTAINS 'Finance' 
       OR embedded.text_content CONTAINS 'heads'
       OR embedded.text_content CONTAINS 'Alex'
    RETURN 
        embedded.name as name,
        embedded.text_content as content
    LIMIT 5
    """
    
    try:
        results = neo4j_client.execute_query(query)
        print(f"Found {len(results)} relevant embeddings:")
        
        for emb in results:
            print(f"\n  {emb['name']}:")
            print(f"    Content: {emb['content']}")
            
    except Exception as e:
        print(f"Embedding content search failed: {e}")

if __name__ == "__main__":
    test_vector_search()
    test_heads_relationships()
    test_finance_nodes()
    test_embedding_content()
    neo4j_client.close()