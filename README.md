# ConceptDB - Evolutionary Concept-Type Database

[![npm version](https://img.shields.io/npm/v/@conceptdb/cli.svg)](https://www.npmjs.com/package/@conceptdb/cli)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

ConceptDB is an **Evolutionary Concept-Type Database** that starts as a 10% semantic enhancement layer on top of PostgreSQL and gradually evolves to 100% concept-based operations. Built for the AI era, it bridges the gap between traditional precise data storage and AI-native semantic understanding.

## 🚀 Quick Deploy

### One-Click Deployment

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new/template/github?repo=https://github.com/888wing/ConceptDB)
[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/888wing/ConceptDB)

## 🌟 Key Features

- **Hybrid Storage**: 90% PostgreSQL (precise data) + 10% ConceptDB (semantic understanding)
- **Natural Language Queries**: Query your data using plain English
- **Gradual Evolution**: Start safe with PostgreSQL, evolve to full conceptual database
- **Visual Studio**: Web-based interface for exploring concepts and relationships
- **Developer Friendly**: CLI tool, JavaScript SDK, and REST API

## 🚀 Quick Start

### Install CLI Tool

```bash
npm install -g @conceptdb/cli
```

### Initialize Project

```bash
conceptdb init my-project
cd my-project
```

### Start Development Environment

```bash
conceptdb dev
```

This starts:
- PostgreSQL database (port 5432)
- Qdrant vector database (port 6333)
- ConceptDB API server (port 8000)
- Web Studio (port 3000)

### Your First Query

Using the CLI:
```bash
conceptdb query "find users who might churn"
```

Using JavaScript SDK:
```javascript
import { ConceptDB } from '@conceptdb/sdk';

const db = new ConceptDB({ url: 'http://localhost:8000' });
const results = await db.query("customers similar to those who bought premium");
```

Using Web Studio:
Open http://localhost:3000 in your browser

## 📦 Installation Options

### Option 1: NPM Package (Recommended)

```bash
npm install -g @conceptdb/cli
npm install @conceptdb/sdk  # For JavaScript projects
```

### Option 2: Docker Compose

```bash
git clone https://github.com/yourusername/conceptdb.git
cd conceptdb
docker-compose up -d
```

### Option 3: From Source

```bash
git clone https://github.com/yourusername/conceptdb.git
cd conceptdb

# Install dependencies
pip install -r requirements.txt
cd cli && npm install && npm run build
cd ../sdk/javascript && npm install && npm run build
cd ../studio && npm install

# Start services
docker-compose up -d postgres qdrant
uvicorn src.api.main:app --reload --port 8000
cd studio && npm run dev
```

## 🏗️ Architecture

### Phase 1: Enhancement Layer (Current)
```
┌─────────────────────────────────────┐
│          Your Application           │
└─────────────────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────┐
│        ConceptDB Query Router       │
│     (Intelligent Query Routing)     │
└─────────────────────────────────────┘
        │                    │
        ↓                    ↓
┌────────────────┐  ┌─────────────────┐
│   PostgreSQL   │  │  Concept Layer  │
│   (90% Data)   │  │  (10% Semantic) │
└────────────────┘  └─────────────────┘
```

### Components

- **PostgreSQL**: Traditional relational data, transactions, ACID compliance
- **Qdrant**: Vector storage for concept embeddings
- **SQLite**: Metadata storage for concept properties
- **NetworkX**: Relationship graph between concepts
- **FastAPI**: REST API server
- **Next.js Studio**: Visual exploration interface

## 📖 API Reference

### REST API

Base URL: `http://localhost:8000/api/v1`

#### Query Endpoints
- `POST /query` - Execute natural language or SQL query
- `GET /query/explain` - Explain query routing decision

#### Concept Management
- `POST /concepts` - Create new concept
- `GET /concepts/{id}` - Get concept details
- `POST /concepts/extract` - Extract concepts from text
- `POST /concepts/search` - Semantic search

#### Evolution Tracking
- `GET /metrics/evolution` - Current evolution metrics
- `POST /evolve` - Trigger evolution to next phase
- `GET /evolution/timeline` - Historical evolution data

### JavaScript SDK

```javascript
import { ConceptDB } from '@conceptdb/sdk';

const db = new ConceptDB({
  url: 'http://localhost:8000',
  apiKey: 'your-api-key' // Optional
});

// Natural language query
const results = await db.query("products similar to bestsellers");

// SQL query (routed to PostgreSQL)
const sqlResults = await db.query("SELECT * FROM users WHERE age > 25");

// Concept operations
const concept = await db.concepts.create({
  name: "Premium Customer",
  description: "Customers with high lifetime value"
});

// Search similar concepts
const similar = await db.concepts.search("high-value users", 0.8);

// Evolution metrics
const metrics = await db.evolution.getMetrics();
console.log(`Current phase: ${metrics.current_phase}`);
console.log(`Conceptualization: ${metrics.conceptualization_ratio}%`);
```

### CLI Commands

```bash
# Project Management
conceptdb init <project-name>    # Initialize new project
conceptdb dev                     # Start development environment
conceptdb status                  # Check system status

# Querying
conceptdb query <query>          # Execute query
conceptdb query --sql <query>    # Force SQL routing
conceptdb query --explain <query> # Explain routing decision

# Data Import
conceptdb import data.csv        # Import CSV data
conceptdb import data.json       # Import JSON data

# Evolution
conceptdb evolve                 # Check evolution readiness
conceptdb evolve --target 2      # Evolve to phase 2
conceptdb evolve --dry-run       # Simulate evolution
```

## 🎯 Use Cases

### 1. Semantic Search on Existing Database
Add ConceptDB as a layer on top of your PostgreSQL database to enable:
- Natural language queries without changing schema
- Find similar records based on meaning, not just values
- Discover hidden relationships in your data

### 2. AI-Powered Analytics
- Query data using business terms instead of SQL
- Get insights from unstructured data
- Automatic pattern recognition

### 3. Gradual Migration to AI-Native
- Start with 10% concepts, keep 90% in PostgreSQL
- Gradually increase conceptualization as confidence grows
- Never lose the safety of traditional databases

## 🔄 Evolution Phases

### Phase 1: Enhancement (10% Concepts) - **Current**
- Add semantic search to existing PostgreSQL
- No migration required
- Zero risk to existing operations

### Phase 2: Hybrid (30% Concepts)
- Intelligent routing between storage layers
- Best of both worlds
- Automatic optimization

### Phase 3: Concept-First (70% Concepts)
- Concepts become primary storage
- PostgreSQL for critical data only
- AI-native operations

### Phase 4: Pure Concept (100%)
- Full conceptual database
- Revolutionary data understanding
- Future of databases

## 🛠️ Development

### Prerequisites
- Python 3.9+
- Node.js 16+
- Docker & Docker Compose
- PostgreSQL 15+

### Project Structure
```
conceptdb/
├── src/                    # Python API server
│   ├── api/               # FastAPI endpoints
│   ├── core/              # Core database logic
│   └── services/          # Business logic
├── cli/                   # Node.js CLI tool
│   ├── src/              # TypeScript source
│   └── dist/             # Compiled JavaScript
├── sdk/
│   └── javascript/       # JavaScript/TypeScript SDK
│       ├── src/         # TypeScript source
│       └── dist/        # Compiled output
├── studio/               # Next.js web interface
│   ├── src/             # React components
│   └── public/          # Static assets
├── tests/               # Test suites
└── docker-compose.yml   # Development environment
```

### Running Tests

```bash
# Python tests
pytest tests/ -v

# CLI tests
cd cli && npm test

# SDK tests
cd sdk/javascript && npm test

# Studio tests
cd studio && npm test

# Integration tests
docker-compose up -d
pytest tests/integration/ -v
```

## 📊 Performance

### Benchmarks (Phase 1)
- **Hybrid queries**: P95 < 500ms
- **Concept extraction**: < 1s for 1000 words
- **Routing decision**: < 50ms
- **PostgreSQL queries**: Native speed
- **Vector search**: < 100ms for 1M vectors

### Resource Requirements
- **Memory**: 4GB minimum, 8GB recommended
- **Storage**: 10GB + your data size
- **CPU**: 2 cores minimum, 4 cores recommended

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details.

### Development Setup

1. Fork the repository
2. Clone your fork
3. Install dependencies
4. Create a feature branch
5. Make your changes
6. Run tests
7. Submit a pull request

## 📝 License

MIT License - see [LICENSE](LICENSE) file for details

## 🙏 Acknowledgments

- Built on top of PostgreSQL, Qdrant, and SQLite
- Inspired by the need for AI-native databases
- Thanks to all contributors

## 📚 Resources

- [Documentation](https://conceptdb.dev/docs)
- [API Reference](https://conceptdb.dev/api)
- [Examples](https://github.com/conceptdb/examples)
- [Discord Community](https://discord.gg/conceptdb)
- [Blog](https://conceptdb.dev/blog)

## 🚧 Roadmap

### Q1 2024
- ✅ Phase 1 implementation (10% concepts)
- ✅ CLI tool
- ✅ JavaScript SDK
- ✅ Web Studio
- ⬜ Python SDK
- ⬜ Production deployment guide

### Q2 2024
- ⬜ Phase 2 implementation (30% concepts)
- ⬜ Advanced routing algorithms
- ⬜ Performance optimizations
- ⬜ Enterprise features

### Q3 2024
- ⬜ Phase 3 implementation (70% concepts)
- ⬜ Multi-language SDKs
- ⬜ Cloud hosting service
- ⬜ Advanced visualization

### Q4 2024
- ⬜ Phase 4 implementation (100% concepts)
- ⬜ Revolutionary features
- ⬜ Industry partnerships

---

**ConceptDB** - The future of databases is conceptual 🚀