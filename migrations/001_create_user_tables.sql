-- Migration: 001_create_user_tables.sql
-- Purpose: Create user authentication and organization tables for ConceptDB
-- Date: 2024

-- Create organizations table
CREATE TABLE IF NOT EXISTS organizations (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) UNIQUE NOT NULL,
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
);

-- Create index on slug for fast lookups
CREATE INDEX idx_organizations_slug ON organizations(slug);

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

-- Create indexes for user lookups
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_organization ON users(organization_id);

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

-- Create indexes for API key lookups
CREATE UNIQUE INDEX idx_api_keys_hash ON api_keys(key_hash) WHERE is_active = TRUE;
CREATE INDEX idx_api_keys_organization ON api_keys(organization_id);

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

-- Create index for subscription lookups
CREATE INDEX idx_subscriptions_stripe ON subscriptions(stripe_customer_id);

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

-- Create usage_metrics table for tracking usage
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

-- Create indexes for usage metrics
CREATE INDEX idx_usage_metrics_org_time ON usage_metrics(organization_id, timestamp DESC);
CREATE INDEX idx_usage_metrics_org_type ON usage_metrics(organization_id, metric_type);

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

-- Create index for alert lookups
CREATE INDEX idx_usage_alerts_org_unresolved ON usage_alerts(organization_id, is_resolved);

-- Create refresh tokens table for JWT refresh
CREATE TABLE IF NOT EXISTS refresh_tokens (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    token_hash VARCHAR(64) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    revoked_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Create index for refresh token lookups
CREATE INDEX idx_refresh_tokens_user ON refresh_tokens(user_id);
CREATE INDEX idx_refresh_tokens_hash ON refresh_tokens(token_hash) WHERE revoked_at IS NULL;

-- Create audit_logs table (for enterprise)
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

-- Create indexes for audit log queries
CREATE INDEX idx_audit_logs_org_time ON audit_logs(organization_id, created_at DESC);
CREATE INDEX idx_audit_logs_user ON audit_logs(user_id, created_at DESC);
CREATE INDEX idx_audit_logs_action ON audit_logs(organization_id, action);