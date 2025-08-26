"""Relationship Engine for managing concept relationships and graph operations"""

import networkx as nx
from typing import List, Dict, Tuple, Optional, Set, Any
from loguru import logger

from .concept import Concept
from .storage import ConceptStorage


class RelationshipEngine:
    """Engine for managing and analyzing concept relationships
    
    This class handles:
    - Relationship creation and management
    - Graph-based operations
    - Relationship discovery
    - Path finding between concepts
    """
    
    RELATIONSHIP_TYPES = ["is_a", "part_of", "related_to", "opposite_of"]
    
    def __init__(self, storage: ConceptStorage = None):
        """Initialize the relationship engine
        
        Args:
            storage: ConceptStorage instance for data persistence
        """
        self.storage = storage or ConceptStorage()
        self.graph = nx.DiGraph()
        self._load_relationships()
        
        logger.info("RelationshipEngine initialized")
    
    def _load_relationships(self):
        """Load all relationships from storage into the graph"""
        try:
            # Get all concepts (paginated for large datasets)
            page = 1
            page_size = 100
            
            while True:
                concepts = self.storage.get_all_concepts(page, page_size)
                if not concepts:
                    break
                
                for concept in concepts:
                    # Add node
                    self.graph.add_node(
                        concept.id,
                        name=concept.name,
                        description=concept.description,
                        strength=concept.strength
                    )
                    
                    # Add edges for relationships
                    for parent_id in concept.parent_ids:
                        self.graph.add_edge(concept.id, parent_id, type="is_a")
                    
                    for child_id in concept.child_ids:
                        self.graph.add_edge(child_id, concept.id, type="part_of")
                    
                    for related_id in concept.related_ids:
                        self.graph.add_edge(concept.id, related_id, type="related_to")
                    
                    for opposite_id in concept.opposite_ids:
                        self.graph.add_edge(concept.id, opposite_id, type="opposite_of")
                
                page += 1
            
            logger.info(f"Loaded {self.graph.number_of_nodes()} nodes and "
                       f"{self.graph.number_of_edges()} edges")
            
        except Exception as e:
            logger.error(f"Failed to load relationships: {e}")
    
    def add_relationship(self,
                        concept1_id: str,
                        concept2_id: str,
                        relationship_type: str) -> bool:
        """Add a relationship between two concepts
        
        Args:
            concept1_id: ID of the first concept
            concept2_id: ID of the second concept
            relationship_type: Type of relationship
            
        Returns:
            True if successful, False otherwise
        """
        if relationship_type not in self.RELATIONSHIP_TYPES:
            logger.error(f"Invalid relationship type: {relationship_type}")
            return False
        
        try:
            # Get concepts from storage
            concept1 = self.storage.get_concept(concept1_id)
            concept2 = self.storage.get_concept(concept2_id)
            
            if not concept1 or not concept2:
                logger.error("One or both concepts not found")
                return False
            
            # Update concept relationships
            concept1.add_relationship(concept2_id, relationship_type)
            
            # For bidirectional relationships
            if relationship_type == "related_to":
                concept2.add_relationship(concept1_id, relationship_type)
            elif relationship_type == "opposite_of":
                concept2.add_relationship(concept1_id, relationship_type)
            elif relationship_type == "is_a":
                # concept1 is_a concept2, so concept2 has concept1 as child
                if concept1_id not in concept2.child_ids:
                    concept2.child_ids.append(concept1_id)
            elif relationship_type == "part_of":
                # concept1 part_of concept2, so concept2 has concept1 as part
                if concept1_id not in concept2.parent_ids:
                    concept2.parent_ids.append(concept1_id)
            
            # Update in storage
            self.storage.update_concept(concept1)
            self.storage.update_concept(concept2)
            
            # Update graph
            self.graph.add_edge(concept1_id, concept2_id, type=relationship_type)
            
            logger.info(f"Added relationship: {concept1.name} {relationship_type} {concept2.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add relationship: {e}")
            return False
    
    def remove_relationship(self,
                           concept1_id: str,
                           concept2_id: str,
                           relationship_type: str) -> bool:
        """Remove a relationship between two concepts
        
        Args:
            concept1_id: ID of the first concept
            concept2_id: ID of the second concept
            relationship_type: Type of relationship to remove
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get concepts from storage
            concept1 = self.storage.get_concept(concept1_id)
            concept2 = self.storage.get_concept(concept2_id)
            
            if not concept1 or not concept2:
                logger.error("One or both concepts not found")
                return False
            
            # Remove relationships
            concept1.remove_relationship(concept2_id, relationship_type)
            
            # Handle bidirectional relationships
            if relationship_type in ["related_to", "opposite_of"]:
                concept2.remove_relationship(concept1_id, relationship_type)
            elif relationship_type == "is_a":
                if concept1_id in concept2.child_ids:
                    concept2.child_ids.remove(concept1_id)
            elif relationship_type == "part_of":
                if concept1_id in concept2.parent_ids:
                    concept2.parent_ids.remove(concept1_id)
            
            # Update in storage
            self.storage.update_concept(concept1)
            self.storage.update_concept(concept2)
            
            # Update graph
            if self.graph.has_edge(concept1_id, concept2_id):
                self.graph.remove_edge(concept1_id, concept2_id)
            
            logger.info(f"Removed relationship: {concept1_id} {relationship_type} {concept2_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove relationship: {e}")
            return False
    
    def get_related_concepts(self,
                            concept_id: str,
                            relationship_type: Optional[str] = None,
                            depth: int = 1) -> List[str]:
        """Get concepts related to a given concept
        
        Args:
            concept_id: ID of the concept
            relationship_type: Specific relationship type to filter (optional)
            depth: How many levels deep to traverse
            
        Returns:
            List of related concept IDs
        """
        if concept_id not in self.graph:
            return []
        
        related = set()
        
        # BFS to find related concepts up to specified depth
        visited = {concept_id}
        current_level = {concept_id}
        
        for _ in range(depth):
            next_level = set()
            
            for node in current_level:
                # Get neighbors
                for neighbor in self.graph.neighbors(node):
                    if neighbor not in visited:
                        # Check relationship type if specified
                        if relationship_type:
                            edge_data = self.graph.get_edge_data(node, neighbor)
                            if edge_data and edge_data.get("type") == relationship_type:
                                next_level.add(neighbor)
                                related.add(neighbor)
                        else:
                            next_level.add(neighbor)
                            related.add(neighbor)
                        
                        visited.add(neighbor)
            
            current_level = next_level
            
            if not current_level:
                break
        
        return list(related)
    
    def find_path(self,
                 concept1_id: str,
                 concept2_id: str) -> Optional[List[str]]:
        """Find shortest path between two concepts
        
        Args:
            concept1_id: Starting concept ID
            concept2_id: Target concept ID
            
        Returns:
            List of concept IDs forming the path, or None if no path exists
        """
        try:
            if concept1_id not in self.graph or concept2_id not in self.graph:
                return None
            
            path = nx.shortest_path(self.graph, concept1_id, concept2_id)
            return path
            
        except nx.NetworkXNoPath:
            return None
        except Exception as e:
            logger.error(f"Failed to find path: {e}")
            return None
    
    def discover_relationships(self,
                              similarity_threshold: float = 0.7) -> List[Tuple[str, str, float]]:
        """Automatically discover potential relationships based on similarity
        
        Args:
            similarity_threshold: Minimum similarity for relationship discovery
            
        Returns:
            List of tuples (concept1_id, concept2_id, similarity_score)
        """
        discovered = []
        
        try:
            # Get all concepts
            all_concepts = []
            page = 1
            while True:
                concepts = self.storage.get_all_concepts(page, 100)
                if not concepts:
                    break
                all_concepts.extend(concepts)
                page += 1
            
            # Compare each pair of concepts
            for i, concept1 in enumerate(all_concepts):
                if concept1.vector is None:
                    continue
                
                for concept2 in all_concepts[i+1:]:
                    if concept2.vector is None:
                        continue
                    
                    # Skip if already related
                    if self.graph.has_edge(concept1.id, concept2.id):
                        continue
                    
                    # Calculate similarity
                    similarity = self.storage.semantic_engine.calculate_similarity(
                        concept1.vector,
                        concept2.vector
                    )
                    
                    if similarity >= similarity_threshold:
                        discovered.append((concept1.id, concept2.id, similarity))
            
            # Sort by similarity
            discovered.sort(key=lambda x: x[2], reverse=True)
            
            logger.info(f"Discovered {len(discovered)} potential relationships")
            return discovered
            
        except Exception as e:
            logger.error(f"Failed to discover relationships: {e}")
            return []
    
    def get_concept_hierarchy(self, root_concept_id: str) -> Dict[str, Any]:
        """Get hierarchical structure starting from a root concept
        
        Args:
            root_concept_id: ID of the root concept
            
        Returns:
            Hierarchical dictionary structure
        """
        def build_hierarchy(node_id: str, visited: Set[str]) -> Dict[str, Any]:
            if node_id in visited:
                return {"id": node_id, "children": []}
            
            visited.add(node_id)
            
            concept = self.storage.get_concept(node_id)
            if not concept:
                return {"id": node_id, "children": []}
            
            hierarchy = {
                "id": node_id,
                "name": concept.name,
                "description": concept.description,
                "children": []
            }
            
            # Get child concepts (part_of relationships)
            for child_id in concept.child_ids:
                if child_id in self.graph:
                    child_hierarchy = build_hierarchy(child_id, visited)
                    hierarchy["children"].append(child_hierarchy)
            
            return hierarchy
        
        return build_hierarchy(root_concept_id, set())
    
    def calculate_centrality(self) -> Dict[str, float]:
        """Calculate centrality scores for all concepts
        
        Returns:
            Dictionary mapping concept IDs to centrality scores
        """
        try:
            # Use PageRank as centrality measure
            centrality = nx.pagerank(self.graph)
            return centrality
        except Exception as e:
            logger.error(f"Failed to calculate centrality: {e}")
            return {}
    
    def get_graph_stats(self) -> Dict[str, Any]:
        """Get statistics about the concept graph
        
        Returns:
            Dictionary with graph statistics
        """
        stats = {
            "total_concepts": self.graph.number_of_nodes(),
            "total_relationships": self.graph.number_of_edges(),
            "relationship_types": {}
        }
        
        # Count relationships by type
        for _, _, data in self.graph.edges(data=True):
            rel_type = data.get("type", "unknown")
            stats["relationship_types"][rel_type] = \
                stats["relationship_types"].get(rel_type, 0) + 1
        
        # Graph metrics
        if self.graph.number_of_nodes() > 0:
            stats["density"] = nx.density(self.graph)
            stats["is_connected"] = nx.is_weakly_connected(self.graph)
            
            # Find strongly connected components
            components = list(nx.strongly_connected_components(self.graph))
            stats["num_components"] = len(components)
            stats["largest_component_size"] = max(len(c) for c in components) if components else 0
        
        return stats
    
    def export_graph(self, format: str = "json") -> Any:
        """Export the concept graph in various formats
        
        Args:
            format: Export format (json, gexf, graphml)
            
        Returns:
            Graph data in specified format
        """
        if format == "json":
            from networkx.readwrite import json_graph
            return json_graph.node_link_data(self.graph)
        elif format == "gexf":
            import io
            stream = io.StringIO()
            nx.write_gexf(self.graph, stream)
            return stream.getvalue()
        elif format == "graphml":
            import io
            stream = io.StringIO()
            nx.write_graphml(self.graph, stream)
            return stream.getvalue()
        else:
            raise ValueError(f"Unsupported format: {format}")