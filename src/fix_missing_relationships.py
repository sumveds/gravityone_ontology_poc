#!/usr/bin/env python3
"""Fix missing business relationships in Neo4j"""

from db.neo4j_client import neo4j_client

def check_existing_relationships():
    """Check what business relationships currently exist"""
    
    print("=== Checking Current Business Relationships ===")
    
    # Check for business relationships (not embedding ones)
    query = """
    MATCH (source)-[r]->(target)
    WHERE NOT r:HAS_EMBEDDING 
    AND NOT r:HAS_STRUCTURE_EMBEDDING
    AND NOT r:REPRESENTS_RELATIONSHIP
    RETURN 
        type(r) as rel_type,
        source.name as source_name,
        labels(source)[0] as source_type,
        target.name as target_name,
        labels(target)[0] as target_type
    ORDER BY rel_type
    """
    
    results = neo4j_client.execute_query(query)
    print(f"Found {len(results)} business relationships")
    
    for rel in results:
        print(f"  {rel['rel_type']}: {rel['source_name']} ({rel['source_type']}) -> {rel['target_name']} ({rel['target_type']})")
    
    return results

def recreate_missing_relationships():
    """Recreate the missing business relationships"""
    
    print("\n=== Recreating Missing Business Relationships ===")
    
    # Check if users and business units exist
    check_query = """
    MATCH (u:User {name: 'Alex Lee'}), (bu:BusinessUnit {name: 'Finance'})
    RETURN u.name as user_name, bu.name as bu_name
    """
    
    check_results = neo4j_client.execute_query(check_query)
    if not check_results:
        print("❌ Alex Lee or Finance BusinessUnit not found!")
        return
    
    print(f"✅ Found: {check_results[0]['user_name']} and {check_results[0]['bu_name']}")
    
    # Recreate all the business relationships from your original data
    relationships = [
        # Priority-Objective relationships
        ("MATCH (p:Priority {priority_id: 'p1'}), (o:Objective {objective_id: 'o1'}) CREATE (p)-[:HAS_OBJECTIVE {weight: 1.0}]->(o)", "p1 -> o1"),
        ("MATCH (p:Priority {priority_id: 'p2'}), (o:Objective {objective_id: 'o2'}) CREATE (p)-[:HAS_OBJECTIVE {weight: 0.8}]->(o)", "p2 -> o2"),
        ("MATCH (p:Priority {priority_id: 'p4'}), (o:Objective {objective_id: 'o3'}) CREATE (p)-[:HAS_OBJECTIVE {weight: 1.0}]->(o)", "p4 -> o3"),
        
        # Objective-KPI relationships
        ("MATCH (o:Objective {objective_id: 'o1'}), (k:KPI {kpi_id: 'k1'}) CREATE (o)-[:MEASURED_BY]->(k)", "o1 -> k1"),
        ("MATCH (o:Objective {objective_id: 'o2'}), (k:KPI {kpi_id: 'k2'}) CREATE (o)-[:MEASURED_BY]->(k)", "o2 -> k2"),
        
        # KPI cascade
        ("MATCH (k1:KPI {kpi_id: 'k1'}), (k3:KPI {kpi_id: 'k3'}) CREATE (k1)-[:CASCADED_TO]->(k3)", "k1 -> k3"),
        
        # Risk relationships
        ("MATCH (o:Objective {objective_id: 'o1'}), (r:Risk {risk_id: 'r1'}) CREATE (o)-[:HAS_RISK]->(r)", "o1 -> r1"),
        ("MATCH (k:KPI {kpi_id: 'k2'}), (r:Risk {risk_id: 'r2'}) CREATE (k)-[:HAS_RISK]->(r)", "k2 -> r2"),
        
        # Strategy relationships
        ("MATCH (s:Strategy {strategy_id: 's1'}), (o:Objective {objective_id: 'o1'}) CREATE (s)-[:ENABLES]->(o)", "s1 -> o1"),
        ("MATCH (s:Strategy {strategy_id: 's2'}), (o:Objective {objective_id: 'o2'}) CREATE (s)-[:ENABLES]->(o)", "s2 -> o2"),
        
        # Project delivery relationships
        ("MATCH (pr:Project {project_id: 'pr1'}), (o:Objective {objective_id: 'o1'}) CREATE (pr)-[:DELIVERS {contribution: 0.7}]->(o)", "pr1 -> o1"),
        ("MATCH (pr:Project {project_id: 'pr2'}), (o:Objective {objective_id: 'o2'}) CREATE (pr)-[:DELIVERS {contribution: 0.5}]->(o)", "pr2 -> o2"),
        ("MATCH (pr:Project {project_id: 'pr3'}), (o:Objective {objective_id: 'o1'}) CREATE (pr)-[:DELIVERS {contribution: 0.6}]->(o)", "pr3 -> o1"),
        
        # Project ownership
        ("MATCH (pr:Project {project_id: 'pr1'}), (bu:BusinessUnit {bu_id: 'bu1'}) CREATE (pr)-[:OWNED_BY]->(bu)", "pr1 -> bu1"),
        ("MATCH (pr:Project {project_id: 'pr2'}), (bu:BusinessUnit {bu_id: 'bu2'}) CREATE (pr)-[:OWNED_BY]->(bu)", "pr2 -> bu2"),
        ("MATCH (pr:Project {project_id: 'pr3'}), (bu:BusinessUnit {bu_id: 'bu1'}) CREATE (pr)-[:OWNED_BY]->(bu)", "pr3 -> bu1"),
        
        # Budget relationships
        ("MATCH (pr:Project {project_id: 'pr1'}), (b:Budget {budget_id: 'b1'}) CREATE (pr)-[:HAS_BUDGET]->(b)", "pr1 -> b1"),
        ("MATCH (pr:Project {project_id: 'pr2'}), (b:Budget {budget_id: 'b2'}) CREATE (pr)-[:HAS_BUDGET]->(b)", "pr2 -> b2"),
        ("MATCH (pr:Project {project_id: 'pr3'}), (b:Budget {budget_id: 'b3'}) CREATE (pr)-[:HAS_BUDGET]->(b)", "pr3 -> b3"),
        
        # Benchmark relationships
        ("MATCH (k:KPI {kpi_id: 'k1'}), (bm:Benchmark {benchmark_id: 'bm1'}) CREATE (k)-[:BENCHMARKED_BY]->(bm)", "k1 -> bm1"),
        ("MATCH (k:KPI {kpi_id: 'k2'}), (bm:Benchmark {benchmark_id: 'bm2'}) CREATE (k)-[:BENCHMARKED_BY]->(bm)", "k2 -> bm2"),
        
        # Output relationships
        ("MATCH (k:KPI {kpi_id: 'k1'}), (out:Output {output_id: 'out1'}) CREATE (k)-[:PRODUCES]->(out)", "k1 -> out1"),
        ("MATCH (pr:Project {project_id: 'pr2'}), (out:Output {output_id: 'out2'}) CREATE (pr)-[:PRODUCES]->(out)", "pr2 -> out2"),
        
        # User ownership relationships
        ("MATCH (u:User {user_id: 'u1'}), (p:Priority {priority_id: 'p1'}) CREATE (u)-[:OWNS]->(p)", "u1 -> p1"),
        ("MATCH (u:User {user_id: 'u2'}), (p:Priority {priority_id: 'p2'}) CREATE (u)-[:OWNS]->(p)", "u2 -> p2"),
        
        # CRITICAL: User-BusinessUnit HEADS relationships
        ("MATCH (u:User {user_id: 'u1'}), (bu:BusinessUnit {bu_id: 'bu1'}) CREATE (u)-[:HEADS]->(bu)", "u1 HEADS bu1"),
        ("MATCH (u:User {user_id: 'u3'}), (bu:BusinessUnit {bu_id: 'bu2'}) CREATE (u)-[:HEADS]->(bu)", "u3 HEADS bu2"),
        
        # Business unit contributions
        ("MATCH (bu:BusinessUnit {bu_id: 'bu1'}), (o:Objective {objective_id: 'o1'}) CREATE (bu)-[:CONTRIBUTES_TO]->(o)", "bu1 -> o1"),
        ("MATCH (bu:BusinessUnit {bu_id: 'bu2'}), (o:Objective {objective_id: 'o2'}) CREATE (bu)-[:CONTRIBUTES_TO]->(o)", "bu2 -> o2"),
        ("MATCH (bu:BusinessUnit {bu_id: 'bu1'}), (p:Priority {priority_id: 'p1'}) CREATE (bu)-[:CONTRIBUTES_TO]->(p)", "bu1 -> p1"),
        ("MATCH (bu:BusinessUnit {bu_id: 'bu2'}), (p:Priority {priority_id: 'p2'}) CREATE (bu)-[:CONTRIBUTES_TO]->(p)", "bu2 -> p2"),
    ]
    
    success_count = 0
    for query, desc in relationships:
        try:
            neo4j_client.execute_query(query)
            print(f"✅ Created: {desc}")
            success_count += 1
        except Exception as e:
            print(f"❌ Failed: {desc} - {e}")
    
    print(f"\n✅ Successfully created {success_count}/{len(relationships)} relationships")

if __name__ == "__main__":
    existing = check_existing_relationships()
    
    if len(existing) < 10:  # We expect many more business relationships
        print(f"\n⚠️  Only {len(existing)} business relationships found. Expected 20+")
        print("Recreating missing relationships...")
        recreate_missing_relationships()
        print("\n=== After Recreation ===")
        check_existing_relationships()
    else:
        print(f"\n✅ {len(existing)} relationships found - looks good!")
    
    neo4j_client.close()