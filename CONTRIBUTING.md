# Contributing to ConceptDB

Thank you for your interest in contributing to ConceptDB! We're building a new database category together, and we need your help.

## 🎯 Our Mission

ConceptDB is creating an evolutionary database that bridges the gap between traditional SQL and future AI-native data operations. We believe in:

- **Gradual Evolution**: Start practical, evolve systematically
- **Developer First**: Amazing developer experience is non-negotiable
- **Open Innovation**: The best ideas come from the community

## 🚀 Getting Started

### Prerequisites

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/your-username/conceptdb.git
   cd conceptdb
   ```
3. Set up development environment:
   ```bash
   # Install Python dependencies
   pip install -r requirements.txt -r requirements-dev.txt
   
   # Install Node.js dependencies
   npm install
   cd cli && npm install && cd ..
   cd sdk/javascript && npm install && cd ../..
   cd studio && npm install && cd ..
   ```

### Development Setup

1. Start Docker services:
   ```bash
   docker-compose up -d
   ```

2. Run tests to verify setup:
   ```bash
   # Python tests
   pytest tests/ -v
   
   # JavaScript tests
   npm test
   ```

## 📝 How to Contribute

### Types of Contributions

#### 🐛 Bug Reports
- Use the GitHub Issues template
- Include reproduction steps
- Provide system information
- Share relevant logs

#### 💡 Feature Requests
- Explain the use case
- Describe expected behavior
- Consider the evolution strategy (Phase 1-4)
- Discuss in issues before implementing

#### 📖 Documentation
- Fix typos and clarify concepts
- Add examples and tutorials
- Translate documentation
- Improve API documentation

#### 💻 Code Contributions
- Fix bugs
- Implement features
- Improve performance
- Add tests

### Code Style

#### Python
```python
# Use type hints
def process_query(query: str, options: QueryOptions) -> QueryResult:
    """Process a query with the given options.
    
    Args:
        query: The query string (SQL or natural language)
        options: Query processing options
        
    Returns:
        QueryResult with data and metadata
    """
    pass

# Follow PEP 8
# Use black for formatting
# Use ruff for linting
```

#### TypeScript/JavaScript
```typescript
// Use TypeScript for new code
interface QueryOptions {
  preferLayer?: 'postgres' | 'concepts' | 'auto';
  timeout?: number;
}

// Use async/await
async function executeQuery(
  query: string, 
  options: QueryOptions = {}
): Promise<QueryResult> {
  // Implementation
}

// Follow ESLint rules
// Use Prettier for formatting
```

### Testing Requirements

- Write tests for all new features
- Maintain >80% code coverage
- Include unit and integration tests
- Test both success and error cases

Example test:
```python
@pytest.mark.asyncio
async def test_query_router_natural_language():
    """Test that natural language queries route to concepts."""
    router = QueryRouter()
    result = await router.route_query("find similar users")
    assert result.layer == "concepts"
    assert result.confidence > 0.8
```

### Commit Guidelines

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add natural language query support
fix: correct PostgreSQL connection pooling
docs: update evolution strategy documentation
test: add query router integration tests
perf: optimize concept extraction speed
refactor: simplify routing logic
```

### Pull Request Process

1. **Create a branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**:
   - Write code
   - Add tests
   - Update documentation

3. **Verify quality**:
   ```bash
   # Format code
   black src/ tests/
   prettier --write "**/*.{ts,tsx,js,jsx}"
   
   # Run linters
   ruff check src/ tests/
   npm run lint
   
   # Run tests
   pytest tests/
   npm test
   ```

4. **Submit PR**:
   - Use a descriptive title
   - Reference related issues
   - Describe what changed and why
   - Include screenshots for UI changes

5. **Review process**:
   - CI must pass
   - Code review required
   - Documentation updated
   - Tests included

## 🏗️ Architecture Guidelines

### Phase-Aware Development

Remember our evolution strategy:
- **Phase 1** (Current): 10% concepts, 90% PostgreSQL
- **Phase 2**: 30% concepts, 70% PostgreSQL
- **Phase 3**: 70% concepts, 30% PostgreSQL
- **Phase 4**: 100% concepts

When contributing, consider:
- Which phase does this feature target?
- Does it help the evolution path?
- Is it backward compatible?

### Core Principles

1. **Start Practical**: Features should provide immediate value
2. **Enable Evolution**: Don't lock us into Phase 1
3. **Developer Experience**: APIs should be intuitive
4. **Performance Matters**: Monitor query latency
5. **Test Everything**: Especially the routing logic

## 🎯 Current Focus Areas

### High Priority (Phase 1)
- PostgreSQL integration improvements
- Query router optimization
- CLI tool enhancements
- SDK documentation
- Docker setup simplification

### Medium Priority
- LangChain integration
- Performance benchmarks
- Additional language SDKs
- Web Studio features

### Future (Phase 2+)
- Advanced routing algorithms
- Concept evolution tracking
- Distributed architecture
- Enterprise features

## 📚 Resources

- [Architecture Overview](./docs/architecture.md)
- [API Documentation](./docs/api.md)
- [Evolution Strategy](./docs/evolution.md)
- [Development Guide](./docs/development.md)

## 🤝 Community

- **Discord**: [Join our community](https://discord.gg/conceptdb) (coming soon)
- **Discussions**: Use GitHub Discussions for questions
- **Issues**: Report bugs and request features
- **Twitter**: Follow [@conceptdb](https://twitter.com/conceptdb) for updates

## 📜 Code of Conduct

We are committed to providing a welcoming and inclusive environment. Please read our [Code of Conduct](CODE_OF_CONDUCT.md) before contributing.

## 🙏 Recognition

Contributors will be recognized in:
- The README.md contributors section
- Release notes
- Our website (coming soon)

## ❓ Questions?

- Check existing issues and discussions
- Ask in Discord
- Email: contribute@conceptdb.com

---

**Thank you for helping us build the future of databases!** 🚀

Every contribution, no matter how small, helps ConceptDB evolve from SQL to concepts.