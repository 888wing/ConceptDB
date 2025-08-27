-- ConceptDB Production Database Setup
-- Run this script using: psql "postgresql://root:wmdV5zofRX2b01MAuqr74LK83NyWB96h@8.222.255.146:30451/zeabur" -f setup_production_db.sql

-- ==================== Phase 1: Core Tables ====================

-- Create products table (for demo data)
CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    price DECIMAL(10, 2),
    category VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
);

-- Create concepts table
CREATE TABLE IF NOT EXISTS concepts (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    vector FLOAT[] NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
);

-- Create concept relationships
CREATE TABLE IF NOT EXISTS concept_relationships (
    id SERIAL PRIMARY KEY,
    source_concept_id VARCHAR(36) NOT NULL,
    target_concept_id VARCHAR(36) NOT NULL,
    relation_type VARCHAR(50) NOT NULL,
    confidence FLOAT DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (source_concept_id) REFERENCES concepts(id) ON DELETE CASCADE,
    FOREIGN KEY (target_concept_id) REFERENCES concepts(id) ON DELETE CASCADE
);

-- Create query logs for analytics
CREATE TABLE IF NOT EXISTS query_logs (
    id SERIAL PRIMARY KEY,
    organization_id VARCHAR(36),
    query_text TEXT NOT NULL,
    query_type VARCHAR(50),
    routed_to VARCHAR(20),
    result_count INTEGER DEFAULT 0,
    execution_time_ms FLOAT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create evolution tracker
CREATE TABLE IF NOT EXISTS evolution_tracker (
    id SERIAL PRIMARY KEY,
    phase INTEGER DEFAULT 1,
    concept_percentage FLOAT DEFAULT 10.0,
    total_concepts INTEGER DEFAULT 0,
    total_queries INTEGER DEFAULT 0,
    queries_to_concepts INTEGER DEFAULT 0,
    queries_to_postgres INTEGER DEFAULT 0,
    last_evolution_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==================== User Authentication Tables ====================

-- Create organizations table
CREATE TABLE IF NOT EXISTS organizations (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) UNIQUE NOT NULL,
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
);

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(36) PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    password_hash VARCHAR(255),
    organization_id VARCHAR(36),
    role VARCHAR(20) DEFAULT 'member' CHECK (role IN ('owner', 'admin', 'member', 'viewer')),
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    last_login_at TIMESTAMP,
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE SET NULL
);

-- Create api_keys table
CREATE TABLE IF NOT EXISTS api_keys (
    id VARCHAR(36) PRIMARY KEY,
    organization_id VARCHAR(36) NOT NULL,
    key_hash VARCHAR(64) NOT NULL,
    name VARCHAR(255),
    description TEXT,
    scopes TEXT[] DEFAULT '{}',
    last_used_at TIMESTAMP,
    usage_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE
);

-- Create subscriptions table
CREATE TABLE IF NOT EXISTS subscriptions (
    id VARCHAR(36) PRIMARY KEY,
    organization_id VARCHAR(36) NOT NULL UNIQUE,
    plan_type VARCHAR(20) DEFAULT 'free' CHECK (plan_type IN ('free', 'professional', 'enterprise')),
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'cancelled', 'past_due', 'trialing')),
    stripe_subscription_id VARCHAR(255),
    stripe_customer_id VARCHAR(255),
    current_period_start TIMESTAMP,
    current_period_end TIMESTAMP,
    trial_end TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    cancelled_at TIMESTAMP,
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE
);

-- Create quotas table
CREATE TABLE IF NOT EXISTS quotas (
    organization_id VARCHAR(36) PRIMARY KEY,
    max_concepts INTEGER DEFAULT 100000,
    max_queries_per_month INTEGER DEFAULT 100000,
    max_api_calls_per_month INTEGER DEFAULT 100000,
    max_storage_gb FLOAT DEFAULT 1.0,
    max_concurrent_connections INTEGER DEFAULT 10,
    max_evolution_phase INTEGER DEFAULT 1,
    max_queries_per_minute INTEGER DEFAULT 100,
    max_api_calls_per_second INTEGER DEFAULT 10,
    custom_models_enabled BOOLEAN DEFAULT FALSE,
    sso_enabled BOOLEAN DEFAULT FALSE,
    audit_logs_enabled BOOLEAN DEFAULT FALSE,
    white_labeling_enabled BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE
);

-- Create usage_metrics table
CREATE TABLE IF NOT EXISTS usage_metrics (
    id VARCHAR(36) PRIMARY KEY,
    organization_id VARCHAR(36) NOT NULL,
    metric_type VARCHAR(50) NOT NULL CHECK (metric_type IN ('concepts', 'queries', 'api_calls', 'storage_gb', 'vector_operations')),
    value FLOAT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    period_start TIMESTAMP,
    period_end TIMESTAMP,
    metadata JSONB DEFAULT '{}',
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE
);

-- Create usage_alerts table
CREATE TABLE IF NOT EXISTS usage_alerts (
    id VARCHAR(36) PRIMARY KEY,
    organization_id VARCHAR(36) NOT NULL,
    metric_type VARCHAR(50) NOT NULL,
    threshold_percentage FLOAT NOT NULL,
    current_usage FLOAT NOT NULL,
    limit_value FLOAT NOT NULL,
    is_resolved BOOLEAN DEFAULT FALSE,
    notified_at TIMESTAMP,
    resolved_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE
);

-- Create refresh_tokens table
CREATE TABLE IF NOT EXISTS refresh_tokens (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    token_hash VARCHAR(64) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    revoked_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Create audit_logs table
CREATE TABLE IF NOT EXISTS audit_logs (
    id VARCHAR(36) PRIMARY KEY,
    organization_id VARCHAR(36) NOT NULL,
    user_id VARCHAR(36),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id VARCHAR(255),
    ip_address VARCHAR(45),
    user_agent TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- Create api_usage_logs table
CREATE TABLE IF NOT EXISTS api_usage_logs (
    id SERIAL PRIMARY KEY,
    organization_id VARCHAR(36),
    endpoint VARCHAR(255),
    method VARCHAR(10),
    response_time_ms FLOAT,
    status_code INTEGER,
    metadata JSONB DEFAULT '{}',
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create schema_migrations table
CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(255) PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    checksum VARCHAR(64)
);

-- ==================== Indexes for Performance ====================

-- Core indexes
CREATE INDEX IF NOT EXISTS idx_concepts_name ON concepts(name);
CREATE INDEX IF NOT EXISTS idx_concept_relationships_source ON concept_relationships(source_concept_id);
CREATE INDEX IF NOT EXISTS idx_concept_relationships_target ON concept_relationships(target_concept_id);
CREATE INDEX IF NOT EXISTS idx_query_logs_timestamp ON query_logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_query_logs_org ON query_logs(organization_id, timestamp DESC);

-- User/Auth indexes
CREATE INDEX IF NOT EXISTS idx_organizations_slug ON organizations(slug);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_organization ON users(organization_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys(key_hash) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_api_keys_organization ON api_keys(organization_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_stripe ON subscriptions(stripe_customer_id);

-- Usage tracking indexes
CREATE INDEX IF NOT EXISTS idx_usage_metrics_org_time ON usage_metrics(organization_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_usage_metrics_org_type ON usage_metrics(organization_id, metric_type);
CREATE INDEX IF NOT EXISTS idx_usage_alerts_org_unresolved ON usage_alerts(organization_id, is_resolved);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user ON refresh_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_hash ON refresh_tokens(token_hash) WHERE revoked_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_audit_logs_org_time ON audit_logs(organization_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user ON audit_logs(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_api_usage_logs_org ON api_usage_logs(organization_id, timestamp DESC);

-- ==================== Initial Data ====================

-- Insert initial evolution tracker
INSERT INTO evolution_tracker (phase, concept_percentage, total_concepts, total_queries)
VALUES (1, 10.0, 0, 0)
ON CONFLICT DO NOTHING;

-- Insert demo products
INSERT INTO products (name, description, price, category) VALUES
    ('MacBook Pro M3', 'Powerful laptop for developers', 2499.99, 'Electronics'),
    ('iPhone 15 Pro', 'Latest flagship smartphone', 1199.99, 'Electronics'),
    ('AirPods Pro', 'Noise-cancelling earbuds', 249.99, 'Electronics'),
    ('Smart Home Hub', 'Central control for IoT devices', 149.99, 'Smart Home'),
    ('Wireless Charger', 'Fast charging pad', 39.99, 'Accessories')
ON CONFLICT DO NOTHING;

-- Record migration
INSERT INTO schema_migrations (version, checksum) 
VALUES ('001_initial_setup', 'production_setup_v1')
ON CONFLICT DO NOTHING;

-- ==================== Verification ====================

-- Show created tables
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
ORDER BY table_name;

-- Show row counts
SELECT 
    'products' as table_name, COUNT(*) as row_count FROM products
UNION ALL
SELECT 
    'organizations', COUNT(*) FROM organizations
UNION ALL
SELECT 
    'users', COUNT(*) FROM users
UNION ALL
SELECT 
    'evolution_tracker', COUNT(*) FROM evolution_tracker;

\echo 'Database setup completed successfully!'