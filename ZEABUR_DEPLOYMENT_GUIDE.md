# Zeabur Deployment Guide for ConceptDB

## 🚀 Quick Setup

### 1. Database Setup
```bash
# Run the setup script
psql "postgresql://root:wmdV5zofRX2b01MAuqr74LK83NyWB96h@8.222.255.146:30451/zeabur" -f setup_production_db.sql
```

### 2. Environment Variables (Add to Zeabur)

```env
# Required Environment Variables
DATABASE_URL=postgresql://root:wmdV5zofRX2b01MAuqr74LK83NyWB96h@8.222.255.146:30451/zeabur
POSTGRES_URL=postgresql://root:wmdV5zofRX2b01MAuqr74LK83NyWB96h@8.222.255.146:30451/zeabur
JWT_SECRET_KEY=<generate-random-32-char-string>
USE_SIMPLE_VECTOR=true
EVOLUTION_PHASE=1
CONCEPT_RATIO=0.1
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO
ENVIRONMENT=production
```

### 3. Generate JWT Secret Key
```python
# Run this Python code to generate a secure key
import secrets
print(secrets.token_urlsafe(32))
```

## 📊 Database Tables Created

### Core Tables (Phase 1)
- `products` - Demo product data
- `concepts` - Concept storage with vectors
- `concept_relationships` - Concept connections
- `query_logs` - Query analytics
- `evolution_tracker` - Evolution metrics

### Authentication Tables
- `organizations` - Multi-tenant support
- `users` - User accounts
- `api_keys` - API authentication
- `subscriptions` - Payment plans
- `quotas` - Usage limits
- `usage_metrics` - Usage tracking
- `usage_alerts` - Quota warnings
- `refresh_tokens` - JWT refresh
- `audit_logs` - Enterprise audit trail
- `api_usage_logs` - API analytics

## 🔧 Database Management Commands

### Connect to Database
```bash
psql "postgresql://root:wmdV5zofRX2b01MAuqr74LK83NyWB96h@8.222.255.146:30451/zeabur"
```

### Useful SQL Commands
```sql
-- Check all tables
\dt

-- View table structure
\d users

-- Check row counts
SELECT table_name, 
       (xpath('/row/cnt/text()', xml_count))[1]::text::int as row_count
FROM (
  SELECT table_name, 
         query_to_xml(format('select count(*) as cnt from %I', table_name), 
         false, true, '') as xml_count
  FROM information_schema.tables
  WHERE table_schema = 'public'
) t;

-- View recent queries
SELECT query_text, execution_time_ms, timestamp 
FROM query_logs 
ORDER BY timestamp DESC 
LIMIT 10;

-- Check usage metrics
SELECT organization_id, metric_type, SUM(value) as total 
FROM usage_metrics 
WHERE timestamp > NOW() - INTERVAL '30 days'
GROUP BY organization_id, metric_type;

-- View active users
SELECT email, role, last_login_at 
FROM users 
WHERE is_active = TRUE 
ORDER BY created_at DESC;
```

## 🔐 Security Configuration

### JWT Configuration
- Access token expires in 24 hours
- Refresh token expires in 30 days
- Use strong secret key (32+ characters)

### API Key Format
- Format: `ck_live_<random_string>`
- Store only hash in database
- Support scopes for permissions

## 📈 Monitoring

### Health Check Endpoint
```bash
curl https://your-app.zeabur.app/health
```

### API Documentation
```
https://your-app.zeabur.app/docs
```

### Key Metrics to Monitor
- Query routing (concepts vs PostgreSQL)
- API response times
- Usage against quotas
- Error rates

## 🎯 Free Tier Limits

```python
{
    "max_concepts": 100000,
    "max_queries_per_month": 100000,
    "max_api_calls_per_month": 100000,
    "max_storage_gb": 1.0,
    "max_evolution_phase": 1
}
```

## 🚨 Troubleshooting

### Database Connection Issues
1. Check DATABASE_URL is correct
2. Verify PostgreSQL is accessible from Zeabur
3. Check firewall rules allow connection

### Authentication Issues
1. Verify JWT_SECRET_KEY is set
2. Check token expiration
3. Verify user exists in database

### Performance Issues
1. Check database indexes are created
2. Monitor query_logs table
3. Use `EXPLAIN ANALYZE` for slow queries

## 📝 First User Setup

```python
# Create first admin user via API
import requests

# Register
response = requests.post(
    "https://your-app.zeabur.app/api/v1/auth/register",
    json={
        "email": "admin@conceptdb.com",
        "password": "YourSecurePassword123!",
        "name": "Admin User",
        "organization_name": "ConceptDB"
    }
)

# Get access token
token = response.json()["data"]["access_token"]
print(f"Admin token: {token}")
```

## 🔄 Update Deployment

```bash
# Push to GitHub
git add .
git commit -m "Update ConceptDB"
git push origin main

# Zeabur will auto-deploy from GitHub
```

## 📊 Cost Estimation

With PostgreSQL on Zeabur:
- **Database**: ~$5-20/month (depends on usage)
- **Compute**: ~$5-10/month 
- **Total**: ~$10-30/month for starter

Break-even: 1 paying customer at $49/month

## ✅ Deployment Checklist

- [ ] Run database setup script
- [ ] Add all environment variables to Zeabur
- [ ] Generate and set JWT_SECRET_KEY
- [ ] Deploy from GitHub
- [ ] Test health endpoint
- [ ] Create first admin user
- [ ] Test authentication flow
- [ ] Monitor initial usage