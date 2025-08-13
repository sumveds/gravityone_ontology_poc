#!/usr/bin/env python3
"""Debug script to check relationship extraction"""

from db.neo4j_client import neo4j_client

def test_simple_relationship_query():
    """Test a simple relationship query"""
    
    print("=== Testing Simple Relationship Query ===")
    
    # Simple query to get all relationships
    simple_query = """
    MATCH (source)-[r]->(target)
    RETURN 
        id(r) as relationship_id,
        type(r) as relationship_type,
        labels(source) as source_labels,
        source.name as source_name,
        labels(target) as target_labels,
        target.name as target_name
    LIMIT 10
    """
    
    try:
        results = neo4j_client.execute_query(simple_query)
        print(f"Found {len(results)} relationships")
        
        for i, rel in enumerate(results[:3]):
            print(f"\n{i+1}. {rel['relationship_type']}")
            print(f"   From: {rel['source_name']} ({rel['source_labels']})")
            print(f"   To: {rel['target_name']} ({rel['target_labels']})")
            
    except Exception as e:
        print(f"Error: {e}")

def test_heads_relationship():
    """Test specifically for HEADS relationship"""
    
    print("\n=== Testing HEADS Relationship ===")
    
    query = """
    MATCH (user:User)-[:HEADS]->(bu:BusinessUnit)
    RETURN user.name as user_name, user.role as user_role, bu.name as bu_name
    """
    
    try:
        results = neo4j_client.execute_query(query)
        print(f"Found {len(results)} HEADS relationships")
        
        for rel in results:
            print(f"   {rel['user_name']} ({rel['user_role']}) HEADS {rel['bu_name']}")
            
    except Exception as e:
        print(f"Error: {e}")

def test_dynamic_labels():
    """Test dynamic label fetching"""
    
    print("\n=== Testing Dynamic Labels ===")
    
    # Get labels
    labels_query = "CALL db.labels() YIELD label RETURN label"
    labels_results = neo4j_client.execute_query(labels_query)
    excluded_labels = {'EmbeddedNode', 'EmbeddedRelationship', 'EmbeddedStructure'}
    labels = [result['label'] for result in labels_results if result['label'] not in excluded_labels]
    
    print(f"Found labels: {labels}")
    
    # Test the problematic WHERE clause construction
    label_conditions = " OR ".join([f"source:{label}" for label in labels])
    target_conditions = " OR ".join([f"target:{label}" for label in labels])
    
    print(f"Source conditions: ({label_conditions})")
    print(f"Target conditions: ({target_conditions})")
    
    # Test the actual query that's failing
    test_query = f"""
    MATCH (source)-[r]->(target)
    WHERE ({label_conditions})
    AND ({target_conditions})
    RETURN count(r) as relationship_count
    """
    
    print(f"\nTesting query:")
    print(test_query)
    
    try:
        results = neo4j_client.execute_query(test_query)
        print(f"Query result: {results[0]['relationship_count']} relationships")
    except Exception as e:
        print(f"Query failed: {e}")

if __name__ == "__main__":
    test_simple_relationship_query()
    test_heads_relationship()
    test_dynamic_labels()
    neo4j_client.close()