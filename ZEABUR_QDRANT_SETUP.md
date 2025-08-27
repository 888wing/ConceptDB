# Zeabur Deployment with Qdrant Vector Database

## 🚀 Complete Setup Guide

### 1. Deploy Services on Zeabur

#### A. Deploy PostgreSQL
- Already deployed at: `8.222.255.146:30451`
- Database name: `zeabur`
- User: `root`

#### B. Deploy Qdrant
1. In Zeabur dashboard, add new service
2. Select "Qdrant" from marketplace or use Docker image
3. Configure:
   ```yaml
   Image: qdrant/qdrant:latest
   Port: 6333
   Environment Variables:
     QDRANT__SERVICE__HTTP_PORT: 6333
     QDRANT__SERVICE__GRPC_PORT: 6334
     QDRANT__LOG_LEVEL: INFO
   ```

#### C. Deploy ConceptDB API
1. Connect GitHub repository
2. Set build command: `pip install -r requirements.txt`
3. Set start command: `uvicorn src.api.main:app --host 0.0.0.0 --port 8000`

### 2. Environment Variables Configuration

Add these to your Zeabur ConceptDB service:

```env
# Database
DATABASE_URL=postgresql://root:wmdV5zofRX2b01MAuqr74LK83NyWB96h@8.222.255.146:30451/zeabur
POSTGRES_URL=postgresql://root:wmdV5zofRX2b01MAuqr74LK83NyWB96h@8.222.255.146:30451/zeabur

# Qdrant Vector Database
USE_SIMPLE_VECTOR=false
QDRANT_URL=http://qdrant:6333  # Internal service name
# Or use external URL if Qdrant is exposed:
# QDRANT_URL=https://qdrant-xxx.zeabur.app

# Authentication
JWT_SECRET_KEY=<generate-with-secrets.token_urlsafe(32)>

# ConceptDB Settings
EVOLUTION_PHASE=1
CONCEPT_RATIO=0.1
ENVIRONMENT=zeabur

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO
```

### 3. Service Communication

#### Internal Communication (Recommended)
Services in same Zeabur project can communicate using service names:
- PostgreSQL: Use provided connection string
- Qdrant: `http://qdrant:6333`
- API: `http://conceptdb:8000`

#### External Access
If you need external access to Qdrant:
1. Enable external access in Zeabur
2. Use the provided URL: `https://qdrant-xxx.zeabur.app`
3. Update `QDRANT_URL` environment variable

### 4. Initialize Database

```bash
# Run database setup
psql "postgresql://root:wmdV5zofRX2b01MAuqr74LK83NyWB96h@8.222.255.146:30451/zeabur" -f setup_production_db.sql
```

### 5. Verify Deployment

#### Check Health
```bash
curl https://your-conceptdb.zeabur.app/health
```

Expected response:
```json
{
  "status": "healthy",
  "services": {
    "postgresql": true,
    "qdrant": true,
    "api": true
  },
  "phase": 1,
  "conceptualization_ratio": 0.1
}
```

#### Test Qdrant Connection
```bash
# Direct Qdrant health check (if exposed)
curl https://your-qdrant.zeabur.app/health

# Or via ConceptDB API
curl -X POST https://your-conceptdb.zeabur.app/api/v1/concepts \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Concept", "description": "Testing Qdrant"}'
```

### 6. Architecture on Zeabur

```
┌─────────────────────────────────────┐
│          Zeabur Platform            │
├─────────────────────────────────────┤
│                                     │
│  ┌──────────────┐  ┌─────────────┐│
│  │  PostgreSQL  │  │   Qdrant    ││
│  │   (Remote)   │  │  (Docker)   ││
│  │ 8.222.255... │  │ Port: 6333  ││
│  └──────┬───────┘  └──────┬──────┘│
│         │                  │       │
│         └────────┬─────────┘       │
│                  │                 │
│         ┌────────▼────────┐        │
│         │   ConceptDB     │        │
│         │   API Server    │        │
│         │  Port: 8000     │        │
│         └─────────────────┘        │
│                                     │
└─────────────────────────────────────┘
```

### 7. Performance Configuration

#### Qdrant Optimization
```env
# Add to Qdrant environment variables
QDRANT__SERVICE__MAX_REQUEST_SIZE_MB=50
QDRANT__SERVICE__MAX_WORKERS=4
QDRANT__STORAGE__STORAGE_PATH=/qdrant/storage
QDRANT__STORAGE__OPTIMIZERS_CONFIG__MEMMAP_THRESHOLD=50000
```

#### ConceptDB Optimization
```env
# Connection pooling
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20

# Vector operations
VECTOR_BATCH_SIZE=100
SEMANTIC_MODEL_CACHE=true
```

### 8. Monitoring & Logging

#### View Logs in Zeabur
1. Go to your service in Zeabur dashboard
2. Click on "Logs" tab
3. Filter by service: ConceptDB, Qdrant

#### Key Metrics to Monitor
- Qdrant collection size
- Vector search latency
- PostgreSQL query performance
- API response times

### 9. Troubleshooting

#### Qdrant Connection Issues
```python
# Debug script
import qdrant_client
from qdrant_client import QdrantClient

# Test connection
client = QdrantClient(
    url="http://qdrant:6333",  # or your external URL
    timeout=10
)

try:
    info = client.get_collections()
    print("✅ Qdrant connected:", info)
except Exception as e:
    print("❌ Qdrant connection failed:", e)
```

#### Fallback to Simple Vector Store
The system automatically falls back to simple vector store if Qdrant is unavailable:
```python
# In main.py
try:
    vector_store = VectorStore(qdrant_url)
    await vector_store.initialize()
except Exception:
    # Automatic fallback
    vector_store = VectorStore()  # Simple in-memory store
```

### 10. Cost Optimization

#### Zeabur Pricing (Approximate)
- **PostgreSQL**: $5-20/month (external)
- **Qdrant**: $10-30/month (depends on storage/compute)
- **ConceptDB API**: $5-15/month
- **Total**: $20-65/month

#### Optimization Tips
1. Use Qdrant's built-in compression
2. Implement vector quantization for large datasets
3. Cache frequently accessed vectors
4. Use batch operations for bulk imports

### 11. Scaling Strategy

#### Phase 1 (Current)
- Single Qdrant instance
- 10% concept layer
- Suitable for < 1M vectors

#### Phase 2 (Growth)
- Qdrant clustering
- 30% concept layer
- PostgreSQL read replicas

#### Phase 3 (Scale)
- Distributed Qdrant
- 70% concept layer
- Sharded PostgreSQL

### 12. Security Considerations

#### Qdrant API Key (Optional)
```env
# If Qdrant requires authentication
QDRANT_API_KEY=your-qdrant-api-key
```

#### Network Security
- Keep Qdrant internal (not exposed) if possible
- Use Zeabur's internal networking
- Enable SSL/TLS for external connections

### 13. Quick Test Script

```python
#!/usr/bin/env python3
import asyncio
import aiohttp

async def test_zeabur_deployment():
    base_url = "https://your-conceptdb.zeabur.app"
    
    async with aiohttp.ClientSession() as session:
        # Health check
        async with session.get(f"{base_url}/health") as resp:
            health = await resp.json()
            print(f"Health: {health}")
        
        # Create concept (tests Qdrant)
        concept = {
            "name": "Zeabur Test",
            "description": "Testing Qdrant on Zeabur"
        }
        async with session.post(
            f"{base_url}/api/v1/concepts",
            json=concept
        ) as resp:
            result = await resp.json()
            print(f"Concept created: {result}")
        
        # Search concepts
        async with session.post(
            f"{base_url}/api/v1/concepts/search",
            json={"query": "test", "limit": 5}
        ) as resp:
            results = await resp.json()
            print(f"Search results: {results}")

asyncio.run(test_zeabur_deployment())
```

## ✅ Deployment Checklist

- [ ] PostgreSQL deployed and accessible
- [ ] Qdrant service deployed on Zeabur
- [ ] ConceptDB connected to GitHub
- [ ] All environment variables set
- [ ] Database initialized with setup script
- [ ] Health endpoint returns healthy
- [ ] Qdrant connection verified
- [ ] Test concept creation works
- [ ] Authentication system tested
- [ ] Monitoring enabled