"""
LLM Query Processor
Advanced natural language to SQL/Concept query processing
Phase 1-2: Enhanced semantic understanding with LLM integration
"""

import os
import re
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass
import asyncio

logger = logging.getLogger(__name__)

# Optional OpenAI integration
try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False
    logger.warning("OpenAI not installed. Using fallback NL processing.")


class QueryIntent(Enum):
    """Query intent types"""
    SEARCH = "search"
    AGGREGATE = "aggregate"
    FILTER = "filter"
    RELATIONSHIP = "relationship"
    COMPARISON = "comparison"
    SEMANTIC = "semantic"
    HYBRID = "hybrid"


@dataclass
class ParsedQuery:
    """Structured representation of parsed query"""
    original_query: str
    intent: QueryIntent
    entities: List[str]
    conditions: Dict[str, Any]
    semantic_components: List[str]
    confidence: float
    suggested_route: str  # 'postgres', 'concepts', or 'both'


class LLMQueryProcessor:
    """Advanced query processor with LLM capabilities"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-3.5-turbo"):
        """
        Initialize LLM query processor
        
        Args:
            api_key: OpenAI API key (optional)
            model: Model to use for processing
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self.use_llm = HAS_OPENAI and self.api_key
        
        if self.use_llm:
            openai.api_key = self.api_key
            logger.info(f"LLM Query Processor initialized with {model}")
        else:
            logger.info("LLM Query Processor using fallback pattern matching")
            
        # Enhanced pattern library for fallback
        self.patterns = self._initialize_patterns()
        
    def _initialize_patterns(self) -> Dict[str, List[Tuple[str, str]]]:
        """Initialize enhanced pattern matching for fallback"""
        return {
            'search': [
                (r'find (?:all )?(\w+) (?:where|with) (.+)', 'SELECT * FROM {0} WHERE {1}'),
                (r'search for (\w+) (?:that|which) (.+)', 'SELECT * FROM {0} WHERE {1}'),
                (r'get (?:all )?(\w+) (?:having|containing) (.+)', 'SELECT * FROM {0} WHERE {1}'),
                (r'show (?:me )?(\w+) (?:where|with) (.+)', 'SELECT * FROM {0} WHERE {1}'),
            ],
            'semantic': [
                (r'(?:similar|related) to (.+)', None),
                (r'concepts? (?:like|about) (.+)', None),
                (r'(?:might|could|possibly) (.+)', None),
                (r'(?:recommend|suggest) (.+)', None),
            ],
            'aggregate': [
                (r'count (?:of )?(\w+)', 'SELECT COUNT(*) FROM {0}'),
                (r'average (\w+) (?:of|for) (\w+)', 'SELECT AVG({0}) FROM {1}'),
                (r'sum (?:of )?(\w+) (?:in|from) (\w+)', 'SELECT SUM({0}) FROM {1}'),
                (r'(?:max|maximum) (\w+) (?:in|from) (\w+)', 'SELECT MAX({0}) FROM {1}'),
            ],
            'relationship': [
                (r'(\w+) connected to (\w+)', None),
                (r'relationship between (\w+) and (\w+)', None),
                (r'how (?:is|are) (\w+) related to (\w+)', None),
                (r'path from (\w+) to (\w+)', None),
            ]
        }
        
    async def process_query(self, query: str) -> ParsedQuery:
        """
        Process natural language query into structured format
        
        Args:
            query: Natural language query
            
        Returns:
            ParsedQuery object with structured information
        """
        if self.use_llm:
            return await self._process_with_llm(query)
        else:
            return await self._process_with_patterns(query)
            
    async def _process_with_llm(self, query: str) -> ParsedQuery:
        """Process query using LLM"""
        try:
            # Prepare prompt for LLM
            prompt = self._create_analysis_prompt(query)
            
            # Call OpenAI API
            response = await self._call_openai(prompt)
            
            # Parse LLM response
            return self._parse_llm_response(query, response)
            
        except Exception as e:
            logger.error(f"LLM processing failed: {e}, falling back to patterns")
            return await self._process_with_patterns(query)
            
    def _create_analysis_prompt(self, query: str) -> str:
        """Create prompt for LLM query analysis"""
        return f"""Analyze this database query and return a JSON response:

Query: "{query}"

Determine:
1. Intent (search/aggregate/filter/relationship/comparison/semantic/hybrid)
2. Main entities mentioned
3. Filter conditions
4. Whether it needs semantic/conceptual search
5. Confidence score (0-1)
6. Suggested routing (postgres/concepts/both)

If it's a SQL-like query, also provide the SQL translation.

Response format:
{{
    "intent": "search",
    "entities": ["users", "products"],
    "conditions": {{"status": "active", "age": ">18"}},
    "semantic_components": ["similar", "related"],
    "needs_semantic": true,
    "confidence": 0.85,
    "suggested_route": "both",
    "sql_query": "SELECT * FROM users WHERE status = 'active'"
}}"""

    async def _call_openai(self, prompt: str) -> str:
        """Call OpenAI API"""
        try:
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a database query analyzer. Always respond with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                max_tokens=500
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            raise
            
    def _parse_llm_response(self, original_query: str, response: str) -> ParsedQuery:
        """Parse LLM response into ParsedQuery"""
        try:
            data = json.loads(response)
            
            return ParsedQuery(
                original_query=original_query,
                intent=QueryIntent(data.get('intent', 'search')),
                entities=data.get('entities', []),
                conditions=data.get('conditions', {}),
                semantic_components=data.get('semantic_components', []),
                confidence=data.get('confidence', 0.5),
                suggested_route=data.get('suggested_route', 'postgres')
            )
        except Exception as e:
            logger.error(f"Failed to parse LLM response: {e}")
            # Fallback to basic parsing
            return ParsedQuery(
                original_query=original_query,
                intent=QueryIntent.SEARCH,
                entities=[],
                conditions={},
                semantic_components=[],
                confidence=0.3,
                suggested_route='postgres'
            )
            
    async def _process_with_patterns(self, query: str) -> ParsedQuery:
        """Process query using pattern matching (fallback)"""
        query_lower = query.lower()
        
        # Detect intent
        intent = self._detect_intent(query_lower)
        
        # Extract entities
        entities = self._extract_entities(query_lower)
        
        # Extract conditions
        conditions = self._extract_conditions(query_lower)
        
        # Detect semantic components
        semantic_components = self._detect_semantic_components(query_lower)
        
        # Calculate confidence
        confidence = self._calculate_confidence(
            query_lower, intent, entities, semantic_components
        )
        
        # Determine routing
        suggested_route = self._determine_route(
            intent, semantic_components, confidence
        )
        
        return ParsedQuery(
            original_query=query,
            intent=intent,
            entities=entities,
            conditions=conditions,
            semantic_components=semantic_components,
            confidence=confidence,
            suggested_route=suggested_route
        )
        
    def _detect_intent(self, query: str) -> QueryIntent:
        """Detect query intent from patterns"""
        # Check for aggregate keywords
        if any(kw in query for kw in ['count', 'sum', 'average', 'avg', 'max', 'min']):
            return QueryIntent.AGGREGATE
            
        # Check for relationship keywords
        if any(kw in query for kw in ['related', 'connected', 'relationship', 'path']):
            return QueryIntent.RELATIONSHIP
            
        # Check for semantic keywords
        if any(kw in query for kw in ['similar', 'like', 'recommend', 'suggest', 'might']):
            return QueryIntent.SEMANTIC
            
        # Check for comparison
        if any(op in query for op in ['>', '<', '>=', '<=', 'greater', 'less', 'between']):
            return QueryIntent.COMPARISON
            
        # Check for filter
        if any(kw in query for kw in ['where', 'filter', 'having', 'with']):
            return QueryIntent.FILTER
            
        # Default to search
        return QueryIntent.SEARCH
        
    def _extract_entities(self, query: str) -> List[str]:
        """Extract potential entity names from query"""
        entities = []
        
        # Common entity patterns
        patterns = [
            r'from (\w+)',
            r'(?:table|collection) (\w+)',
            r'(\w+) where',
            r'select .* from (\w+)',
            r'(\w+s)\b',  # Plural nouns often indicate entities
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, query)
            entities.extend(matches)
            
        # Remove duplicates and common words
        common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'with', 'from', 'where'}
        entities = list(set(e for e in entities if e not in common_words))
        
        return entities
        
    def _extract_conditions(self, query: str) -> Dict[str, Any]:
        """Extract filter conditions from query"""
        conditions = {}
        
        # Pattern for key-value conditions
        patterns = [
            r'(\w+)\s*=\s*["\']?([^"\']+)["\']?',
            r'(\w+)\s+is\s+([^\s]+)',
            r'(\w+)\s+(?:greater|more)\s+than\s+(\d+)',
            r'(\w+)\s+(?:less)\s+than\s+(\d+)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, query)
            for key, value in matches:
                # Try to parse value type
                if value.isdigit():
                    conditions[key] = int(value)
                elif value.replace('.', '', 1).isdigit():
                    conditions[key] = float(value)
                elif value.lower() in ['true', 'false']:
                    conditions[key] = value.lower() == 'true'
                else:
                    conditions[key] = value
                    
        return conditions
        
    def _detect_semantic_components(self, query: str) -> List[str]:
        """Detect semantic/conceptual components in query"""
        semantic_keywords = [
            'similar', 'related', 'like', 'about', 'concerning',
            'might', 'could', 'possibly', 'probably', 'seems',
            'recommend', 'suggest', 'find me', 'show me',
            'concept', 'idea', 'theme', 'topic'
        ]
        
        found = [kw for kw in semantic_keywords if kw in query]
        return found
        
    def _calculate_confidence(
        self, 
        query: str, 
        intent: QueryIntent,
        entities: List[str],
        semantic_components: List[str]
    ) -> float:
        """Calculate confidence score for query parsing"""
        confidence = 0.5  # Base confidence
        
        # Increase confidence based on clear indicators
        if intent != QueryIntent.SEARCH:
            confidence += 0.1
            
        if entities:
            confidence += min(len(entities) * 0.1, 0.2)
            
        if semantic_components:
            confidence += min(len(semantic_components) * 0.1, 0.2)
            
        # Check for SQL-like structure
        if any(kw in query for kw in ['select', 'from', 'where', 'insert', 'update']):
            confidence += 0.2
            
        return min(confidence, 0.95)
        
    def _determine_route(
        self,
        intent: QueryIntent,
        semantic_components: List[str],
        confidence: float
    ) -> str:
        """Determine optimal routing for query"""
        # Semantic queries go to concepts
        if intent == QueryIntent.SEMANTIC or len(semantic_components) >= 2:
            if confidence >= 0.7:
                return 'concepts'
            else:
                return 'both'
                
        # Relationship queries might need both
        if intent == QueryIntent.RELATIONSHIP:
            return 'both'
            
        # High confidence SQL-like queries go to postgres
        if confidence >= 0.8 and not semantic_components:
            return 'postgres'
            
        # Low confidence queries check both
        if confidence < 0.6:
            return 'both'
            
        # Default to postgres for structured queries
        return 'postgres'
        
    async def translate_to_sql(self, parsed_query: ParsedQuery) -> Optional[str]:
        """
        Translate parsed query to SQL
        
        Args:
            parsed_query: Parsed query object
            
        Returns:
            SQL query string or None if not translatable
        """
        if parsed_query.intent == QueryIntent.SEMANTIC:
            # Semantic queries don't translate directly to SQL
            return None
            
        # Build SQL based on intent
        if parsed_query.intent == QueryIntent.SEARCH:
            return self._build_search_sql(parsed_query)
        elif parsed_query.intent == QueryIntent.AGGREGATE:
            return self._build_aggregate_sql(parsed_query)
        elif parsed_query.intent == QueryIntent.FILTER:
            return self._build_filter_sql(parsed_query)
        else:
            return None
            
    def _build_search_sql(self, parsed_query: ParsedQuery) -> str:
        """Build search SQL query"""
        if not parsed_query.entities:
            return None
            
        table = parsed_query.entities[0]
        
        if parsed_query.conditions:
            conditions = []
            for key, value in parsed_query.conditions.items():
                if isinstance(value, str):
                    conditions.append(f"{key} = '{value}'")
                else:
                    conditions.append(f"{key} = {value}")
            where_clause = " AND ".join(conditions)
            return f"SELECT * FROM {table} WHERE {where_clause}"
        else:
            return f"SELECT * FROM {table} LIMIT 10"
            
    def _build_aggregate_sql(self, parsed_query: ParsedQuery) -> str:
        """Build aggregate SQL query"""
        # Simple aggregate query builder
        query = parsed_query.original_query.lower()
        
        if 'count' in query:
            if parsed_query.entities:
                return f"SELECT COUNT(*) FROM {parsed_query.entities[0]}"
        elif 'sum' in query:
            # Extract column and table
            match = re.search(r'sum (?:of )?(\w+) (?:in|from) (\w+)', query)
            if match:
                return f"SELECT SUM({match.group(1)}) FROM {match.group(2)}"
        elif 'average' in query or 'avg' in query:
            match = re.search(r'(?:average|avg) (\w+) (?:of|for|in|from) (\w+)', query)
            if match:
                return f"SELECT AVG({match.group(1)}) FROM {match.group(2)}"
                
        return None
        
    def _build_filter_sql(self, parsed_query: ParsedQuery) -> str:
        """Build filter SQL query"""
        return self._build_search_sql(parsed_query)  # Similar logic