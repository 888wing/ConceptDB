FROM postgres:15-alpine

# Create initialization script
COPY <<EOF /docker-entrypoint-initdb.d/init.sql
-- Create database if not exists
SELECT 'CREATE DATABASE conceptdb'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'conceptdb');

-- Create user if not exists
DO
\$do\$
BEGIN
   IF NOT EXISTS (
      SELECT FROM pg_catalog.pg_user
      WHERE usename = 'concept_user') THEN
      CREATE USER concept_user WITH PASSWORD 'concept_pass';
   END IF;
END
\$do\$;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE conceptdb TO concept_user;
EOF

# Set default environment variables
ENV POSTGRES_DB=conceptdb
ENV POSTGRES_USER=concept_user
ENV POSTGRES_PASSWORD=concept_pass