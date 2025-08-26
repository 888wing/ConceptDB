# Deployment Guide

ConceptDB can be deployed to various cloud platforms. Choose the one that best fits your needs.

## Quick Deploy Options

### Deploy to Railway
[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new/template/github?repo=https://github.com/888wing/ConceptDB)

Railway provides a simple one-click deployment with automatic SSL and scaling.

### Deploy to Render
[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/888wing/ConceptDB)

Render offers free tier options and automatic deployments from GitHub.

### Deploy to Heroku
[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy?template=https://github.com/888wing/ConceptDB)

Heroku provides easy deployment with add-ons for PostgreSQL and monitoring.

## Manual Deployment

### Prerequisites
- Docker and Docker Compose installed
- PostgreSQL 15+ (or use managed service)
- Python 3.9+ runtime
- 4GB RAM minimum

### Environment Variables

```env
# Database Configuration
POSTGRES_URL=postgresql://user:pass@host:5432/conceptdb
QDRANT_URL=http://qdrant-host:6333

# Evolution Settings
EVOLUTION_PHASE=1
CONCEPT_RATIO=0.1

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false

# Optional: AI Features
OPENAI_API_KEY=your-key-here
```

### Docker Deployment

1. Clone the repository:
```bash
git clone https://github.com/888wing/ConceptDB.git
cd ConceptDB
```

2. Create `.env` file with your configuration

3. Build and run:
```bash
docker-compose up -d
```

### Kubernetes Deployment

```bash
# Apply configurations
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/postgres.yaml
kubectl apply -f k8s/qdrant.yaml
kubectl apply -f k8s/api.yaml
kubectl apply -f k8s/ingress.yaml
```

### Cloud-Specific Guides

#### AWS ECS
1. Build and push Docker image to ECR
2. Create ECS task definition
3. Configure RDS PostgreSQL
4. Deploy service with auto-scaling

#### Google Cloud Run
1. Build container image
2. Push to Container Registry
3. Deploy to Cloud Run
4. Configure Cloud SQL for PostgreSQL

#### Azure Container Instances
1. Create container registry
2. Push Docker images
3. Deploy container group
4. Configure Azure Database for PostgreSQL

## Production Considerations

### Database
- Use managed PostgreSQL service (RDS, Cloud SQL, etc.)
- Enable connection pooling
- Configure backups and replication
- Set up monitoring

### Vector Store
- Deploy Qdrant in cluster mode for HA
- Use persistent volumes for data
- Configure appropriate memory limits
- Enable authentication

### API Server
- Use multiple replicas for high availability
- Configure health checks
- Set up rate limiting
- Enable CORS for your domains
- Use environment-specific configurations

### Monitoring
- Application metrics (Prometheus/Grafana)
- Error tracking (Sentry)
- Log aggregation (ELK stack)
- Uptime monitoring

### Security
- Enable SSL/TLS everywhere
- Use secrets management
- Configure firewall rules
- Regular security updates
- API key authentication

## Scaling

### Horizontal Scaling
- API servers: Add more replicas
- PostgreSQL: Read replicas
- Qdrant: Cluster mode
- Use load balancer

### Vertical Scaling
- Increase memory for vector operations
- More CPU cores for parallel processing
- SSD storage for better I/O

## Support

For deployment help:
- [GitHub Issues](https://github.com/888wing/ConceptDB/issues)
- [Discord Community](https://discord.gg/conceptdb)
- [Documentation](https://conceptdb.dev/docs/deployment)