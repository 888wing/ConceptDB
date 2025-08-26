# ConceptDB JavaScript SDK

JavaScript/TypeScript SDK for ConceptDB - An Evolutionary Concept-Type Database that evolves from 10% to 100% conceptualization.

## Installation

```bash
npm install @conceptdb/sdk
# or
yarn add @conceptdb/sdk
```

## Quick Start

```javascript
import { ConceptDB } from '@conceptdb/sdk';

// Initialize the client
const db = new ConceptDB({
  url: 'http://localhost:8000',
  phase: 1  // Current evolution phase (1-4)
});

// Execute queries (natural language or SQL)
const result = await db.execute("find users who might churn");
console.log(result.routing.type);  // 'concept', 'sql', or 'hybrid'
console.log(result.data);
```

## Features

- **Hybrid Queries**: Execute both SQL and natural language queries
- **Query Builder**: Fluent API for building complex queries
- **Concept Management**: Create, search, and relate concepts
- **Evolution Tracking**: Monitor and control database evolution
- **TypeScript Support**: Full type definitions included

## License

MIT