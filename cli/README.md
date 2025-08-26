# ConceptDB CLI

Command-line interface for ConceptDB - Evolutionary Concept-Type Database.

## Installation

```bash
npm install -g @conceptdb/cli
```

## Quick Start

```bash
# Initialize a new project
conceptdb init my-app

# Start development environment
cd my-app
conceptdb dev

# Run queries
conceptdb query "find all customer feedback"
conceptdb query "SELECT * FROM data_records"

# Import data
conceptdb import data.csv --extract-concepts

# Check evolution progress
conceptdb evolve --metrics
```

## Commands

### `conceptdb init [project-name]`
Initialize a new ConceptDB project with Docker setup and configuration.

Options:
- `-t, --template <template>` - Project template (basic, langchain, fullstack)
- `-p, --phase <phase>` - Evolution phase (1-4)

### `conceptdb dev`
Start the development environment with Docker Compose.

Options:
- `-p, --port <port>` - API port (default: 8000)
- `--postgres` - Start with PostgreSQL (default: true)
- `--no-studio` - Don't open Web Studio

### `conceptdb query <query>`
Execute SQL or natural language queries.

Options:
- `-t, --type <type>` - Query type (auto, sql, natural)
- `-l, --layer <layer>` - Target layer (auto, postgres, concepts)
- `-f, --format <format>` - Output format (json, table, pretty)

Examples:
```bash
# Natural language query
conceptdb query "find products with high ratings"

# SQL query
conceptdb query "SELECT * FROM data_records WHERE type = 'product'"

# Query specific layer
conceptdb query "similar concepts to satisfaction" --layer concepts
```

### `conceptdb import <file>`
Import data from CSV, JSON, or SQL files.

Options:
- `-t, --type <type>` - Data type for records
- `--extract-concepts` - Extract concepts immediately (default: true)
- `--batch-size <size>` - Batch size for import (default: 100)

Examples:
```bash
# Import CSV with concept extraction
conceptdb import customers.csv --type customer_data

# Import JSON without concept extraction
conceptdb import products.json --no-extract-concepts
```

### `conceptdb evolve [phase]`
Check evolution status or evolve to next phase.

Options:
- `--metrics` - Show detailed evolution metrics
- `--simulate` - Simulate evolution without applying changes

Examples:
```bash
# Check current evolution metrics
conceptdb evolve --metrics

# Evolve to Phase 2 (30% conceptualization)
conceptdb evolve 2

# Simulate evolution to Phase 3
conceptdb evolve 3 --simulate
```

### `conceptdb config [key] [value]`
Get or set configuration values.

Options:
- `-l, --list` - List all configuration
- `-g, --global` - Use global configuration

Examples:
```bash
# List all configuration
conceptdb config --list

# Get specific value
conceptdb config api.url

# Set value
conceptdb config api.port 8080
```

## Configuration

ConceptDB CLI uses a `.conceptdb` file in your project directory:

```json
{
  "name": "my-app",
  "version": "0.1.0",
  "phase": 1,
  "api": {
    "url": "http://localhost:8000",
    "version": "v1"
  },
  "postgres": {
    "host": "localhost",
    "port": 5432,
    "database": "conceptdb",
    "user": "concept_user"
  },
  "evolution": {
    "currentPhase": 1,
    "conceptualizationRatio": 0.1,
    "autoEvolve": false
  }
}
```

## Evolution Phases

ConceptDB follows an evolutionary architecture:

1. **Phase 1** (10%): PostgreSQL with concept enhancement layer
2. **Phase 2** (30%): Hybrid storage with intelligent routing
3. **Phase 3** (70%): Concept-first with PostgreSQL backup
4. **Phase 4** (100%): Pure concept database

## Environment Variables

```bash
CONCEPTDB_API_URL=http://localhost:8000
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=conceptdb
POSTGRES_USER=concept_user
POSTGRES_PASSWORD=concept_pass
QDRANT_HOST=localhost
QDRANT_PORT=6333
EVOLUTION_PHASE=1
CONCEPT_RATIO=0.1
```

## Development

```bash
# Clone the repository
git clone https://github.com/conceptdb/cli
cd cli

# Install dependencies
npm install

# Build
npm run build

# Run in development
npm run dev

# Run tests
npm test
```

## License

MIT