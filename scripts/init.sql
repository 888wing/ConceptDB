-- ConceptDB PostgreSQL initialization script
-- Phase 1: 90% PostgreSQL + 10% Concept Layer

-- Create schema for ConceptDB metadata
CREATE SCHEMA IF NOT EXISTS conceptdb;

-- Table for tracking concept-data relationships
CREATE TABLE IF NOT EXISTS conceptdb.concept_mappings (
    id SERIAL PRIMARY KEY,
    table_name VARCHAR(255) NOT NULL,
    column_name VARCHAR(255) NOT NULL,
    concept_id UUID NOT NULL,
    confidence FLOAT DEFAULT 0.5,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table for query routing history
CREATE TABLE IF NOT EXISTS conceptdb.query_history (
    id SERIAL PRIMARY KEY,
    query_text TEXT NOT NULL,
    query_type VARCHAR(50) NOT NULL, -- 'sql', 'natural', 'hybrid'
    routing_decision VARCHAR(50) NOT NULL, -- 'postgres', 'concepts', 'both'
    confidence_score FLOAT NOT NULL,
    execution_time_ms INTEGER,
    result_count INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table for evolution metrics
CREATE TABLE IF NOT EXISTS conceptdb.evolution_metrics (
    id SERIAL PRIMARY KEY,
    current_phase INTEGER DEFAULT 1,
    conceptualization_ratio FLOAT DEFAULT 0.1,
    total_queries INTEGER DEFAULT 0,
    sql_queries INTEGER DEFAULT 0,
    concept_queries INTEGER DEFAULT 0,
    hybrid_queries INTEGER DEFAULT 0,
    last_evolution TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert initial evolution metrics
INSERT INTO conceptdb.evolution_metrics (
    current_phase, 
    conceptualization_ratio, 
    total_queries, 
    sql_queries, 
    concept_queries, 
    hybrid_queries
) VALUES (1, 0.1, 0, 0, 0, 0)
ON CONFLICT DO NOTHING;

-- Sample tables for demo (e-commerce scenario)
CREATE TABLE IF NOT EXISTS customers (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_purchase_at TIMESTAMP,
    total_spent DECIMAL(10, 2) DEFAULT 0,
    loyalty_tier VARCHAR(50) DEFAULT 'bronze'
);

CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    sku VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    price DECIMAL(10, 2) NOT NULL,
    category VARCHAR(100),
    stock_quantity INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(id),
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_amount DECIMAL(10, 2) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    shipping_address TEXT
);

CREATE TABLE IF NOT EXISTS order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES orders(id),
    product_id INTEGER REFERENCES products(id),
    quantity INTEGER NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL,
    subtotal DECIMAL(10, 2) NOT NULL
);

-- Indexes for performance
CREATE INDEX idx_concept_mappings_table ON conceptdb.concept_mappings(table_name, column_name);
CREATE INDEX idx_query_history_type ON conceptdb.query_history(query_type, routing_decision);
CREATE INDEX idx_query_history_created ON conceptdb.query_history(created_at DESC);
CREATE INDEX idx_customers_email ON customers(email);
CREATE INDEX idx_products_category ON products(category);
CREATE INDEX idx_orders_customer ON orders(customer_id);
CREATE INDEX idx_orders_status ON orders(status);

-- Functions for query routing
CREATE OR REPLACE FUNCTION conceptdb.should_route_to_concepts(query_text TEXT)
RETURNS BOOLEAN AS $$
DECLARE
    semantic_keywords TEXT[] := ARRAY['similar', 'like', 'related', 'might', 'could', 'probably', 'seems', 'about'];
    keyword TEXT;
BEGIN
    FOREACH keyword IN ARRAY semantic_keywords
    LOOP
        IF position(lower(keyword) in lower(query_text)) > 0 THEN
            RETURN TRUE;
        END IF;
    END LOOP;
    RETURN FALSE;
END;
$$ LANGUAGE plpgsql;

-- Function to track query routing
CREATE OR REPLACE FUNCTION conceptdb.track_query(
    p_query_text TEXT,
    p_query_type VARCHAR(50),
    p_routing_decision VARCHAR(50),
    p_confidence_score FLOAT,
    p_execution_time_ms INTEGER,
    p_result_count INTEGER
) RETURNS VOID AS $$
BEGIN
    INSERT INTO conceptdb.query_history (
        query_text,
        query_type,
        routing_decision,
        confidence_score,
        execution_time_ms,
        result_count
    ) VALUES (
        p_query_text,
        p_query_type,
        p_routing_decision,
        p_confidence_score,
        p_execution_time_ms,
        p_result_count
    );
    
    -- Update evolution metrics
    UPDATE conceptdb.evolution_metrics
    SET total_queries = total_queries + 1,
        sql_queries = sql_queries + CASE WHEN p_routing_decision = 'postgres' THEN 1 ELSE 0 END,
        concept_queries = concept_queries + CASE WHEN p_routing_decision = 'concepts' THEN 1 ELSE 0 END,
        hybrid_queries = hybrid_queries + CASE WHEN p_routing_decision = 'both' THEN 1 ELSE 0 END,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = 1;
END;
$$ LANGUAGE plpgsql;

-- Sample data for demo
INSERT INTO customers (email, name, last_purchase_at, total_spent, loyalty_tier) VALUES
('john.doe@email.com', 'John Doe', '2024-01-15', 1250.00, 'gold'),
('jane.smith@email.com', 'Jane Smith', '2024-01-20', 450.00, 'silver'),
('bob.wilson@email.com', 'Bob Wilson', '2024-01-10', 2500.00, 'platinum'),
('alice.johnson@email.com', 'Alice Johnson', '2024-01-18', 150.00, 'bronze'),
('charlie.brown@email.com', 'Charlie Brown', '2023-12-20', 800.00, 'silver')
ON CONFLICT (email) DO NOTHING;

INSERT INTO products (sku, name, description, price, category, stock_quantity) VALUES
('LAPTOP-001', 'ProBook Laptop', 'High-performance laptop for professionals', 1299.99, 'Electronics', 15),
('PHONE-001', 'SmartPhone X', 'Latest smartphone with AI features', 899.99, 'Electronics', 25),
('BOOK-001', 'Database Design', 'Complete guide to database architecture', 49.99, 'Books', 100),
('CHAIR-001', 'Ergonomic Office Chair', 'Comfortable chair for long work sessions', 399.99, 'Furniture', 10),
('COFFEE-001', 'Premium Coffee Beans', 'Arabica coffee beans from Colombia', 29.99, 'Food', 50)
ON CONFLICT (sku) DO NOTHING;

-- Grant permissions
GRANT ALL ON SCHEMA conceptdb TO concept_user;
GRANT ALL ON ALL TABLES IN SCHEMA conceptdb TO concept_user;
GRANT ALL ON ALL SEQUENCES IN SCHEMA conceptdb TO concept_user;
GRANT ALL ON ALL FUNCTIONS IN SCHEMA conceptdb TO concept_user;