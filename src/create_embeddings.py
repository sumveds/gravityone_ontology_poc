#!/usr/bin/env python3
"""
Embedding Recreation Script for Neo4j Ontology Data

This script extracts all textual content from Neo4j nodes and creates embeddings
for RAG (Retrieval Augmented Generation) functionality.

Run this script before running the main application to ensure embeddings are available.
"""

import sys
import os
import asyncio
from typing import List, Dict, Any
from pathlib import Path

from config.settings import settings
from db.neo4j_client import neo4j_client
from utils.embeddings import embedder_instance
from utils.logger import logger


class EmbeddingRecreator:
    def __init__(self):
        self.client = neo4j_client
        self.embedder = embedder_instance
        self.node_labels = self._get_all_node_labels()
        self.relationship_types = self._get_all_relationship_types()
        
    def _get_all_node_labels(self) -> List[str]:
        """Dynamically fetch all node labels from the database"""
        query = "CALL db.labels() YIELD label RETURN label"
        
        try:
            results = self.client.execute_query(query)
            # Exclude embedding-related labels
            excluded_labels = {'EmbeddedNode', 'EmbeddedRelationship', 'EmbeddedStructure'}
            labels = [result['label'] for result in results if result['label'] not in excluded_labels]
            logger.info(f"Found node labels: {labels}")
            return labels
        except Exception as e:
            logger.error(f"Error fetching node labels: {e}")
            return []
    
    def _get_all_relationship_types(self) -> List[str]:
        """Dynamically fetch all relationship types from the database"""
        query = "CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType"
        
        try:
            results = self.client.execute_query(query)
            # Exclude embedding-related relationship types
            excluded_types = {'HAS_EMBEDDING', 'HAS_REL_EMBEDDING', 'HAS_STRUCTURE_EMBEDDING'}
            rel_types = [result['relationshipType'] for result in results if result['relationshipType'] not in excluded_types]
            logger.info(f"Found relationship types: {rel_types}")
            return rel_types
        except Exception as e:
            logger.error(f"Error fetching relationship types: {e}")
            return []
        
    def extract_node_content(self) -> List[Dict[str, Any]]:
        """Extract all textual content from Neo4j nodes"""
        
        if not self.node_labels:
            logger.warning("No node labels found, skipping node extraction")
            return []
        
        # Build dynamic WHERE clause for all node labels
        label_conditions = " OR ".join([f"n:{label}" for label in self.node_labels])
        
        # Query to get all nodes with their textual properties
        query = f"""
        MATCH (n)
        WHERE {label_conditions}
        RETURN 
            id(n) as node_id,
            labels(n) as labels,
            n.name as name,
            n.description as description,
            n.type as type,
            n.category as category,
            n.focus_area as focus_area,
            n.measure as measure,
            n.treatments as treatments,
            n.role as role,
            n.department as department,
            n.email as email,
            properties(n) as all_properties
        """
        
        try:
            results = self.client.execute_query(query)
            logger.info(f"Extracted {len(results)} nodes for embedding creation")
            return results
        except Exception as e:
            logger.error(f"Error extracting node content: {e}")
            return []
    
    def extract_relationship_content(self) -> List[Dict[str, Any]]:
        """Extract all relationships with their properties and context"""
        
        if not self.node_labels:
            logger.warning("No node labels found, skipping relationship extraction")
            return []
        
        # Build dynamic WHERE clause for source and target nodes
        label_conditions = " OR ".join([f"source:{label}" for label in self.node_labels])
        target_conditions = " OR ".join([f"target:{label}" for label in self.node_labels])
        
        # Query to get all relationships with source and target node context
        query = f"""
        MATCH (source)-[r]->(target)
        WHERE ({label_conditions})
        AND ({target_conditions})
        RETURN 
            id(r) as relationship_id,
            type(r) as relationship_type,
            properties(r) as relationship_properties,
            id(source) as source_node_id,
            labels(source) as source_labels,
            source.name as source_name,
            source.type as source_type,
            id(target) as target_node_id,
            labels(target) as target_labels,
            target.name as target_name,
            target.type as target_type
        """
        
        try:
            results = self.client.execute_query(query)
            logger.info(f"Extracted {len(results)} relationships for embedding creation")
            return results
        except Exception as e:
            logger.error(f"Error extracting relationship content: {e}")
            return []
    
    def extract_graph_structure_content(self) -> List[Dict[str, Any]]:
        """Extract graph structure patterns for contextual embeddings"""
        
        if not self.node_labels:
            logger.warning("No node labels found, skipping graph structure extraction")
            return []
        
        # Build dynamic WHERE clause for nodes
        label_conditions = " OR ".join([f"n:{label}" for label in self.node_labels])
        
        # Query to get nodes with their immediate neighborhood context
        query = f"""
        MATCH (n)
        WHERE {label_conditions}
        OPTIONAL MATCH (n)-[r1]->(connected1)
        OPTIONAL MATCH (n)<-[r2]-(connected2)
        WITH n, 
             collect(DISTINCT {{
                 direction: 'outgoing',
                 relationship: type(r1),
                 target_labels: labels(connected1),
                 target_name: connected1.name,
                 properties: properties(r1)
             }}) as outgoing,
             collect(DISTINCT {{
                 direction: 'incoming', 
                 relationship: type(r2),
                 source_labels: labels(connected2),
                 source_name: connected2.name,
                 properties: properties(r2)
             }}) as incoming
        RETURN 
            id(n) as node_id,
            labels(n) as labels,
            n.name as name,
            outgoing,
            incoming
        """
        
        try:
            results = self.client.execute_query(query)
            logger.info(f"Extracted graph structure for {len(results)} nodes")
            return results
        except Exception as e:
            logger.error(f"Error extracting graph structure: {e}")
            return []
    
    def create_text_representation(self, node: Dict[str, Any]) -> str:
        """Create a comprehensive text representation of a node"""
        
        text_parts = []
        
        # Add node type/labels
        if node.get('labels'):
            text_parts.append(f"Type: {', '.join(node['labels'])}")
        
        # Add core textual fields
        text_fields = ['name', 'description', 'type', 'category', 'focus_area', 
                      'measure', 'treatments', 'role', 'department']
        
        for field in text_fields:
            if node.get(field):
                text_parts.append(f"{field.replace('_', ' ').title()}: {node[field]}")
        
        # Add other relevant properties
        all_props = node.get('all_properties', {})
        excluded_fields = {'node_id', 'created_at', 'updated_at', 'user_id', 'priority_id', 
                          'objective_id', 'kpi_id', 'risk_id', 'strategy_id', 'project_id',
                          'bu_id', 'budget_id', 'benchmark_id', 'output_id', 'baseline',
                          'target', 'actual', 'progress', 'gap', 'probability', 'rating'}
        
        for key, value in all_props.items():
            if (key not in excluded_fields and 
                key not in text_fields and 
                value is not None and 
                str(value).strip()):
                text_parts.append(f"{key.replace('_', ' ').title()}: {value}")
        
        return " | ".join(text_parts)
    
    def create_relationship_text_representation(self, relationship: Dict[str, Any]) -> str:
        """Create a comprehensive text representation of a relationship"""
        
        text_parts = []
        
        # Add relationship type and context
        rel_type = relationship.get('relationship_type', 'UNKNOWN')
        source_name = relationship.get('source_name', 'Unknown')
        target_name = relationship.get('target_name', 'Unknown')
        source_labels = relationship.get('source_labels', [])
        target_labels = relationship.get('target_labels', [])
        
        # Create relationship description
        source_type = ', '.join(source_labels) if source_labels else 'Node'
        target_type = ', '.join(target_labels) if target_labels else 'Node'
        
        text_parts.append(f"Relationship: {rel_type}")
        text_parts.append(f"From: {source_name} ({source_type})")
        text_parts.append(f"To: {target_name} ({target_type})")
        
        # Add relationship properties
        rel_props = relationship.get('relationship_properties', {})
        if rel_props:
            for key, value in rel_props.items():
                if value is not None and str(value).strip():
                    text_parts.append(f"{key.replace('_', ' ').title()}: {value}")
        
        return " | ".join(text_parts)
    
    def create_graph_structure_text_representation(self, structure: Dict[str, Any]) -> str:
        """Create a comprehensive text representation of graph structure context"""
        
        text_parts = []
        
        # Add node information
        name = structure.get('name', 'Unknown')
        labels = structure.get('labels', [])
        node_type = ', '.join(labels) if labels else 'Node'
        
        text_parts.append(f"Node: {name} ({node_type})")
        
        # Add outgoing relationships
        outgoing = structure.get('outgoing', [])
        if outgoing:
            outgoing_desc = []
            for rel in outgoing:
                if rel.get('relationship') and rel.get('target_name'):
                    target_type = ', '.join(rel.get('target_labels', [])) if rel.get('target_labels') else 'Node'
                    outgoing_desc.append(f"{rel['relationship']} → {rel['target_name']} ({target_type})")
            
            if outgoing_desc:
                text_parts.append(f"Connected to: {'; '.join(outgoing_desc)}")
        
        # Add incoming relationships
        incoming = structure.get('incoming', [])
        if incoming:
            incoming_desc = []
            for rel in incoming:
                if rel.get('relationship') and rel.get('source_name'):
                    source_type = ', '.join(rel.get('source_labels', [])) if rel.get('source_labels') else 'Node'
                    incoming_desc.append(f"{rel['source_name']} ({source_type}) → {rel['relationship']}")
            
            if incoming_desc:
                text_parts.append(f"Connected from: {'; '.join(incoming_desc)}")
        
        return " | ".join(text_parts)
    
    def create_vector_indexes(self):
        """Create vector indexes in Neo4j for similarity search"""
        
        indexes = [
            ("node_embeddings", "EmbeddedNode"),
            ("relationship_embeddings", "EmbeddedRelationship"), 
            ("structure_embeddings", "EmbeddedStructure")
        ]
        
        for index_name, label in indexes:
            # Drop existing index if it exists
            drop_query = f"DROP INDEX {index_name} IF EXISTS"
            
            # Create vector index
            create_query = f"""
            CREATE VECTOR INDEX {index_name} IF NOT EXISTS
            FOR (n:{label}) ON (n.embedding)
            OPTIONS {{
                indexConfig: {{
                    `vector.dimensions`: 1536,
                    `vector.similarity_function`: 'cosine'
                }}
            }}
            """
            
            try:
                self.client.execute_query(drop_query)
                self.client.execute_query(create_query)
                logger.info(f"Vector index {index_name} created successfully")
            except Exception as e:
                logger.error(f"Error creating vector index {index_name}: {e}")
    
    def store_node_embeddings(self, nodes_with_embeddings: List[Dict[str, Any]]):
        """Store node embeddings back to Neo4j"""
        
        # Clear existing embedded nodes and their relationships
        clear_query = "MATCH (n:EmbeddedNode) DETACH DELETE n"
        self.client.execute_query(clear_query)
        
        # Create embedded nodes with vector properties
        for node_data in nodes_with_embeddings:
            create_query = """
            CREATE (e:EmbeddedNode {
                original_node_id: $node_id,
                labels: $labels,
                text_content: $text_content,
                embedding: $embedding,
                name: $name,
                created_at: timestamp()
            })
            """
            
            params = {
                'node_id': node_data['node_id'],
                'labels': node_data['labels'],
                'text_content': node_data['text_content'],
                'embedding': node_data['embedding'],
                'name': node_data.get('name', 'Unknown')
            }
            
            try:
                self.client.execute_query(create_query, params)
            except Exception as e:
                logger.error(f"Error storing embedding for node {node_data['node_id']}: {e}")
        
        logger.info(f"Stored {len(nodes_with_embeddings)} node embeddings in Neo4j")
    
    def store_relationship_embeddings(self, relationships_with_embeddings: List[Dict[str, Any]]):
        """Store relationship embeddings back to Neo4j"""
        
        # Clear existing embedded relationships and their relationships
        clear_query = "MATCH (n:EmbeddedRelationship) DETACH DELETE n"
        self.client.execute_query(clear_query)
        
        # Create embedded relationships with vector properties
        for rel_data in relationships_with_embeddings:
            create_query = """
            CREATE (e:EmbeddedRelationship {
                original_relationship_id: $relationship_id,
                relationship_type: $relationship_type,
                source_node_id: $source_node_id,
                target_node_id: $target_node_id,
                text_content: $text_content,
                embedding: $embedding,
                created_at: timestamp()
            })
            """
            
            params = {
                'relationship_id': rel_data['relationship_id'],
                'relationship_type': rel_data['relationship_type'],
                'source_node_id': rel_data['source_node_id'],
                'target_node_id': rel_data['target_node_id'],
                'text_content': rel_data['text_content'],
                'embedding': rel_data['embedding']
            }
            
            try:
                self.client.execute_query(create_query, params)
            except Exception as e:
                logger.error(f"Error storing embedding for relationship {rel_data['relationship_id']}: {e}")
        
        logger.info(f"Stored {len(relationships_with_embeddings)} relationship embeddings in Neo4j")
    
    def store_structure_embeddings(self, structures_with_embeddings: List[Dict[str, Any]]):
        """Store graph structure embeddings back to Neo4j"""
        
        # Clear existing embedded structures and their relationships
        clear_query = "MATCH (n:EmbeddedStructure) DETACH DELETE n"
        self.client.execute_query(clear_query)
        
        # Create embedded structures with vector properties
        for struct_data in structures_with_embeddings:
            create_query = """
            CREATE (e:EmbeddedStructure {
                original_node_id: $node_id,
                labels: $labels,
                text_content: $text_content,
                embedding: $embedding,
                name: $name,
                created_at: timestamp()
            })
            """
            
            params = {
                'node_id': struct_data['node_id'],
                'labels': struct_data['labels'],
                'text_content': struct_data['text_content'],
                'embedding': struct_data['embedding'],
                'name': struct_data.get('name', 'Unknown')
            }
            
            try:
                self.client.execute_query(create_query, params)
            except Exception as e:
                logger.error(f"Error storing embedding for structure {struct_data['node_id']}: {e}")
        
        logger.info(f"Stored {len(structures_with_embeddings)} structure embeddings in Neo4j")
    
    def create_relationships_to_embedded_entities(self):
        """Create relationships between original entities and their embeddings"""
        
        # Link nodes to their embeddings (only if node embeddings exist)
        node_count_query = "MATCH (n:EmbeddedNode) RETURN count(n) as count"
        node_count = self.client.execute_query(node_count_query)[0]['count']
        
        if node_count > 0:
            node_relationship_query = """
            MATCH (original), (embedded:EmbeddedNode)
            WHERE id(original) = embedded.original_node_id
            CREATE (original)-[:HAS_EMBEDDING]->(embedded)
            """
            try:
                self.client.execute_query(node_relationship_query)
                logger.info(f"Created {node_count} node HAS_EMBEDDING relationships")
            except Exception as e:
                logger.error(f"Error creating node HAS_EMBEDDING relationships: {e}")
        
        # Link relationships to their embeddings via source and target nodes (only if relationship embeddings exist)
        rel_count_query = "MATCH (n:EmbeddedRelationship) RETURN count(n) as count"
        rel_count = self.client.execute_query(rel_count_query)[0]['count']
        
        if rel_count > 0:
            # Since we can't create relationships FROM relationships, we link via source/target nodes
            rel_relationship_query = """
            MATCH (source)-[original]->(target), (embedded:EmbeddedRelationship)
            WHERE id(original) = embedded.original_relationship_id
            CREATE (embedded)-[:REPRESENTS_RELATIONSHIP]->(source)
            CREATE (embedded)-[:REPRESENTS_RELATIONSHIP]->(target)
            """
            try:
                self.client.execute_query(rel_relationship_query)
                logger.info(f"Created {rel_count * 2} relationship REPRESENTS_RELATIONSHIP links")
            except Exception as e:
                logger.error(f"Error creating relationship links: {e}")
        
        # Link nodes to their structure embeddings (only if structure embeddings exist)
        struct_count_query = "MATCH (n:EmbeddedStructure) RETURN count(n) as count"
        struct_count = self.client.execute_query(struct_count_query)[0]['count']
        
        if struct_count > 0:
            struct_relationship_query = """
            MATCH (original), (embedded:EmbeddedStructure)
            WHERE id(original) = embedded.original_node_id
            CREATE (original)-[:HAS_STRUCTURE_EMBEDDING]->(embedded)
            """
            try:
                self.client.execute_query(struct_relationship_query)
                logger.info(f"Created {struct_count} structure HAS_STRUCTURE_EMBEDDING relationships")
            except Exception as e:
                logger.error(f"Error creating structure relationships: {e}")
    
    async def recreate_all_embeddings(self):
        """Main method to recreate all embeddings"""
        
        logger.info("Starting comprehensive embedding recreation process...")
        
        # Extract all content types
        logger.info("Extracting node content...")
        nodes = self.extract_node_content()
        
        logger.info("Extracting relationship content...")
        relationships = self.extract_relationship_content()
        
        logger.info("Extracting graph structure content...")
        structures = self.extract_graph_structure_content()
        
        if not nodes and not relationships and not structures:
            logger.error("No content found for embedding creation")
            return
        
        # Process node embeddings
        nodes_with_embeddings = []
        if nodes:
            logger.info(f"Processing {len(nodes)} nodes...")
            for i, node in enumerate(nodes):
                try:
                    text_content = self.create_text_representation(node)
                    
                    if not text_content.strip():
                        logger.warning(f"Empty text content for node {node['node_id']}")
                        continue
                    
                    embedding = self.embedder.embed_text(text_content)
                    
                    if not embedding:
                        logger.warning(f"Failed to create embedding for node {node['node_id']}")
                        continue
                    
                    nodes_with_embeddings.append({
                        'node_id': node['node_id'],
                        'labels': node['labels'],
                        'text_content': text_content,
                        'embedding': embedding,
                        'name': node.get('name')
                    })
                    
                    if (i + 1) % 10 == 0:
                        logger.info(f"Processed {i + 1}/{len(nodes)} nodes")
                        
                except Exception as e:
                    logger.error(f"Error processing node {node['node_id']}: {e}")
        
        # Process relationship embeddings
        relationships_with_embeddings = []
        if relationships:
            logger.info(f"Processing {len(relationships)} relationships...")
            for i, relationship in enumerate(relationships):
                try:
                    text_content = self.create_relationship_text_representation(relationship)
                    
                    if not text_content.strip():
                        logger.warning(f"Empty text content for relationship {relationship['relationship_id']}")
                        continue
                    
                    embedding = self.embedder.embed_text(text_content)
                    
                    if not embedding:
                        logger.warning(f"Failed to create embedding for relationship {relationship['relationship_id']}")
                        continue
                    
                    relationships_with_embeddings.append({
                        'relationship_id': relationship['relationship_id'],
                        'relationship_type': relationship['relationship_type'],
                        'source_node_id': relationship['source_node_id'],
                        'target_node_id': relationship['target_node_id'],
                        'text_content': text_content,
                        'embedding': embedding
                    })
                    
                    if (i + 1) % 10 == 0:
                        logger.info(f"Processed {i + 1}/{len(relationships)} relationships")
                        
                except Exception as e:
                    logger.error(f"Error processing relationship {relationship['relationship_id']}: {e}")
        
        # Process structure embeddings
        structures_with_embeddings = []
        if structures:
            logger.info(f"Processing {len(structures)} graph structures...")
            for i, structure in enumerate(structures):
                try:
                    text_content = self.create_graph_structure_text_representation(structure)
                    
                    if not text_content.strip():
                        logger.warning(f"Empty text content for structure {structure['node_id']}")
                        continue
                    
                    embedding = self.embedder.embed_text(text_content)
                    
                    if not embedding:
                        logger.warning(f"Failed to create embedding for structure {structure['node_id']}")
                        continue
                    
                    structures_with_embeddings.append({
                        'node_id': structure['node_id'],
                        'labels': structure['labels'],
                        'text_content': text_content,
                        'embedding': embedding,
                        'name': structure.get('name')
                    })
                    
                    if (i + 1) % 10 == 0:
                        logger.info(f"Processed {i + 1}/{len(structures)} structures")
                        
                except Exception as e:
                    logger.error(f"Error processing structure {structure['node_id']}: {e}")
        
        # Create vector indexes
        logger.info("Creating vector indexes...")
        self.create_vector_indexes()
        
        # Store all embeddings
        if nodes_with_embeddings:
            logger.info("Storing node embeddings...")
            self.store_node_embeddings(nodes_with_embeddings)
        
        if relationships_with_embeddings:
            logger.info("Storing relationship embeddings...")
            self.store_relationship_embeddings(relationships_with_embeddings)
        
        if structures_with_embeddings:
            logger.info("Storing structure embeddings...")
            self.store_structure_embeddings(structures_with_embeddings)
        
        # Create relationships to embedded entities
        logger.info("Creating relationships to embedded entities...")
        self.create_relationships_to_embedded_entities()
        
        # Summary statistics
        total_embeddings = len(nodes_with_embeddings) + len(relationships_with_embeddings) + len(structures_with_embeddings)
        logger.info(f"Embedding recreation completed! Created {total_embeddings} total embeddings:")
        logger.info(f"  - Node embeddings: {len(nodes_with_embeddings)}")
        logger.info(f"  - Relationship embeddings: {len(relationships_with_embeddings)}")
        logger.info(f"  - Structure embeddings: {len(structures_with_embeddings)}")
        
        # Node type breakdown
        if nodes_with_embeddings:
            label_counts = {}
            for node in nodes_with_embeddings:
                for label in node['labels']:
                    label_counts[label] = label_counts.get(label, 0) + 1
            
            logger.info("Node embedding summary by type:")
            for label, count in sorted(label_counts.items()):
                logger.info(f"  {label}: {count} embeddings")
        
        # Relationship type breakdown
        if relationships_with_embeddings:
            rel_type_counts = {}
            for rel in relationships_with_embeddings:
                rel_type = rel['relationship_type']
                rel_type_counts[rel_type] = rel_type_counts.get(rel_type, 0) + 1
            
            logger.info("Relationship embedding summary by type:")
            for rel_type, count in sorted(rel_type_counts.items()):
                logger.info(f"  {rel_type}: {count} embeddings")


async def main():
    """Main function to run the embedding recreation"""
    
    # Verify environment
    if not settings.OPENAI_API_KEY:
        logger.error("OPENAI_API_KEY not found in environment variables")
        return
    
    if not settings.NEO4J_URI or not settings.NEO4J_PASSWORD:
        logger.error("Neo4j connection settings not found in environment variables")
        return
    
    try:
        # Create recreator and run
        recreator = EmbeddingRecreator()
        await recreator.recreate_all_embeddings()
        
    except Exception as e:
        logger.error(f"Fatal error during embedding recreation: {e}")
        raise
    finally:
        # Clean up
        neo4j_client.close()


if __name__ == "__main__":
    print("🚀 Starting embedding recreation for Neo4j ontology data...")
    print("This will create embeddings for all nodes and store them for RAG functionality.")
    print("=" * 60)
    
    asyncio.run(main())
    
    print("=" * 60)
    print("✅ Embedding recreation completed!")
    print("You can now run your main application with embeddings available.")