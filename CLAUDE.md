# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ConceptDB is an **Evolutionary Concept-Type Database** that starts as a 10% enhancement layer and gradually evolves to 100% concept-based operations. This is NOT another vector database - it's a new database category designed for the AI era.

**Core Philosophy**: Start practical (10% concepts + 90% PostgreSQL), evolve gradually, prove value at each stage.

## Evolution Strategy (演化路徑)

### Phase 1: Enhancement Layer (10% Conceptualization) - CURRENT FOCUS
- **Architecture**: PostgreSQL (90%) + ConceptDB Layer (10%)
- **Value**: Add semantic search to existing data without migration
- **Risk**: Minimal - it's just an add-on layer
- **Timeline**: Weeks 1-4 (MVP)

### Phase 2: Hybrid Database (30% Conceptualization)
- **Architecture**: Intelligent routing between precise and concept storage
- **Value**: Best of both worlds - accuracy + understanding
- **Timeline**: Months 2-3

### Phase 3: Concept-First (70% Conceptualization)
- **Architecture**: ConceptDB primary, PostgreSQL for critical data
- **Value**: AI-native data operations
- **Timeline**: Months 4-6

### Phase 4: Pure Concept Database (100%)
- **Architecture**: Full conceptual storage and operations
- **Value**: Complete paradigm shift in data understanding
- **Timeline**: Year 2+

## Current Architecture (Phase 1)

### Dual-Layer Storage Architecture

```python
# Current implementation focus
architecture = {
    "Precise Layer (90%)": {
        "Storage": "PostgreSQL",
        "Purpose": "Exact data, transactions, ACID",
        "Operations": "SQL queries, joins, constraints"
    },
    "Concept Layer (10%)": {
        "Storage": "Qdrant + SQLite + NetworkX",
        "Purpose": "Semantic understanding, relationships",
        "Operations": "Natural language queries, similarity search"
    },
    "Routing Layer": {
        "Purpose": "Intelligently route queries to appropriate layer",
        "Decision": "Based on query type and confidence"
    }
}
```

### Core Components

1. **Storage Layer** (Hybrid Infrastructure)
   - `PostgreSQL`: Precise data storage (90%)
   - `VectorStore`: Qdrant for concept vectors
   - `MetadataStore`: SQLite for concept metadata
   - `RelationStore`: NetworkX for relationships

2. **Concept Layer** (10% Enhancement)
   - `ConceptManager`: CRUD operations for concepts
   - `SemanticEngine`: Text-to-vector transformation
   - `RelationshipEngine`: Concept relationship discovery
   - `QueryProcessor`: Natural language to SQL/Vector
   - `EvolutionTracker`: Monitor conceptualization progress

3. **Interface Layer** (Multi-Form Product)
   - `CLI Tool`: npm package @conceptdb/cli
   - `REST API`: FastAPI at `/api/v1/`
   - `SDK`: JavaScript/TypeScript first
   - `Web Studio`: Visual exploration interface

## Product Strategy (產品形態)

### Phase 1 Product Forms (Current Focus)

```typescript
// 1. CLI Tool (npm package)
npm install -g @conceptdb/cli
conceptdb init my-project
conceptdb dev
conceptdb query "find similar concepts to 'user satisfaction'"

// 2. JavaScript SDK
import { ConceptDB } from '@conceptdb/sdk';
const db = new ConceptDB({ url: 'http://localhost:8000' });
const results = await db.query("users who might churn");

// 3. Web Studio (Visual Interface)
http://localhost:8000/studio
- Concept graph exploration
- Natural language queries
- Evolution timeline
- Real-time insights dashboard
```

## Development Commands

```bash
# Phase 1: Start hybrid environment
docker-compose up -d  # PostgreSQL + Qdrant + API

# Install dependencies
pip install -r requirements.txt
npm install  # For CLI tool

# Run API server
uvicorn src.api.main:app --reload --port 8000

# Run Web Studio (replacing Streamlit)
cd studio && npm run dev

# Run tests
pytest tests/ -v
npm test  # CLI tests

# Format code
black src/ tests/
prettier --write "studio/**/*.{ts,tsx}"
```

## API Endpoints (Phase 1)

### Unified Query Interface
- `POST /api/v1/query` - Intelligent routing (SQL or natural language)
- `GET /api/v1/query/explain` - Explain routing decision

### Precise Data Operations (90%)
- `POST /api/v1/data` - Traditional CRUD via PostgreSQL
- `GET /api/v1/data/{id}` - Fetch precise data
- `PUT /api/v1/data/{id}` - Update with ACID guarantees

### Concept Operations (10%)
- `POST /api/v1/concepts` - Create concepts from data
- `POST /api/v1/concepts/extract` - Auto-extract from text
- `POST /api/v1/concepts/search` - Semantic search
- `GET /api/v1/concepts/{id}/evolution` - Track concept changes
- `GET /api/v1/concepts/graph` - Relationship visualization

### Evolution Metrics
- `GET /api/v1/metrics/evolution` - Current conceptualization %
- `GET /api/v1/metrics/routing` - Query routing statistics
- `POST /api/v1/evolve` - Trigger evolution to next phase

## Technical Architecture (Phase 1)

### Dual Storage
- **PostgreSQL**: 90% of data (transactions, joins, constraints)
- **ConceptDB Layer**: 10% enhancement (vectors, relationships)
- **Query Router**: Intelligent decision based on query type

### Performance Targets
- **Hybrid queries**: P95 < 500ms
- **Concept extraction**: < 1s for 1000 words
- **Routing decision**: < 50ms
- **Memory**: < 4GB for concept layer
- **PostgreSQL**: Standard tuning applies

## Development Guidelines

### Naming Conventions & Code Style
- **Functions/Variables**: `snake_case`
- **Classes**: `PascalCase`
- **Constants**: `UPPER_SNAKE_CASE`
- **Always use type hints** for function signatures
- **Docstrings**: Google style for all public functions/classes
- **Async-first**: Use `async/await` for I/O operations

### Error Handling
- Always provide meaningful error messages
- Use structured logging with `loguru`
- Never suppress errors silently
- Include context in error responses

### Testing Requirements
- Unit tests for all core concept operations
- Integration tests for API endpoints
- Performance tests for vector operations
- Minimum 80% code coverage

## Phase 1 Implementation Priorities

### Week 1-2: Core Infrastructure
```python
priority_1 = {
    "PostgreSQL Integration": {
        "tasks": [
            "Setup PostgreSQL alongside Qdrant",
            "Create hybrid schema design",
            "Implement connection pooling"
        ],
        "files": ["src/core/pg_storage.py", "src/core/router.py"]
    },
    "Query Router": {
        "tasks": [
            "Analyze query intent (SQL vs NL)",
            "Route to appropriate storage",
            "Merge results from both layers"
        ],
        "files": ["src/core/query_router.py"]
    }
}
```

### Week 3-4: Developer Tools
```python
priority_2 = {
    "CLI Tool": {
        "path": "cli/",
        "stack": "Node.js + Commander.js",
        "package": "@conceptdb/cli",
        "features": ["init", "dev", "query", "import"]
    },
    "JavaScript SDK": {
        "path": "sdk/javascript/",
        "stack": "TypeScript",
        "package": "@conceptdb/sdk",
        "features": ["connect", "query", "concepts.create"]
    }
}
```

### Week 5-6: Web Studio (Replacing Streamlit)
```python
priority_3 = {
    "Web Studio": {
        "path": "studio/",
        "stack": "Next.js + Tailwind + D3.js",
        "features": [
            "Concept Graph Visualization",
            "Natural Language Query Builder",
            "Evolution Timeline",
            "Real-time Insights Dashboard"
        ]
    }
}
```

## Docker Setup (Phase 1 - Hybrid)

```yaml
# docker-compose.yml for Phase 1
services:
  postgres:
    image: postgres:15
    ports: ["5432:5432"]
    environment:
      POSTGRES_DB: conceptdb
      POSTGRES_USER: concept_user
      POSTGRES_PASSWORD: concept_pass
    volumes: ["./pg_data:/var/lib/postgresql/data"]
  
  qdrant:
    image: qdrant/qdrant
    ports: ["6333:6333"]
    volumes: ["./qdrant_data:/qdrant/storage"]
  
  api:
    build: .
    ports: ["8000:8000"]
    depends_on: [postgres, qdrant]
    environment:
      - POSTGRES_URL=postgresql://concept_user:concept_pass@postgres:5432/conceptdb
      - QDRANT_URL=http://qdrant:6333
      - EVOLUTION_PHASE=1
      - CONCEPT_RATIO=0.1
```

## Critical Implementation Notes

### Phase 1 Specific
- **Dual Storage**: Always maintain data consistency between PostgreSQL and ConceptDB
- **Query Routing**: Route based on confidence score (>0.8 to concepts, else PostgreSQL)
- **Evolution Tracking**: Monitor % of queries handled by each layer
- **Gradual Migration**: Start with read-only concept layer, add write in Phase 2

### Concept Extraction
- Auto-extract concepts from PostgreSQL data
- Maintain bidirectional sync between layers
- Track concept evolution over time
- Four relation types: `is_a`, `part_of`, `related_to`, `opposite_of`

### Product Differentiation
- **Natural Language First**: Every query can be natural language
- **Visual by Default**: Results include visualizations
- **Evolution Aware**: Show how data understanding improves
- **AI-Native**: Built for LangChain/LlamaIndex integration

## Project Philosophy

**Phase 1 Success Metrics**:
- 10% of queries handled by concept layer
- 50% reduction in "no results found" for semantic queries
- Developer can integrate in < 30 minutes
- Visual studio makes concepts understandable

**Remember**: 
- Start practical (PostgreSQL + 10% concepts)
- Prove value incrementally
- Make adoption risk-free
- Focus on developer experience

**Not Yet**:
- Don't optimize for scale
- Don't compete on speed
- Don't require data migration
- Don't break existing systems

Every feature should answer: "Does this make the 10% concept layer valuable enough to adopt?"