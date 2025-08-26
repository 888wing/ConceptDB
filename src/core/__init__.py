"""Core concept management and processing modules"""

from .concept import Concept, ConceptMetadata

# Make ML dependencies optional for testing
try:
    from .storage import ConceptStorage
    from .semantic_engine import SemanticEngine
    from .relationship_engine import RelationshipEngine
    __all__ = [
        "Concept",
        "ConceptMetadata",
        "ConceptStorage",
        "SemanticEngine",
        "RelationshipEngine",
    ]
except ImportError:
    # Core components only
    __all__ = [
        "Concept", 
        "ConceptMetadata",
    ]