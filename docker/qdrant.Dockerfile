FROM qdrant/qdrant:latest

# Create entrypoint script for initialization
COPY <<EOF /entrypoint.sh
#!/bin/sh
set -e

# Start Qdrant in background
./qdrant &

# Wait for Qdrant to be ready
echo "Waiting for Qdrant to start..."
sleep 5

# Check if service is running
until curl -f http://localhost:6333/health; do
    echo "Waiting for Qdrant..."
    sleep 2
done

echo "Qdrant is ready!"

# Keep the container running
wait
EOF

RUN chmod +x /entrypoint.sh

# Expose port
EXPOSE 6333

# Use custom entrypoint
ENTRYPOINT ["/entrypoint.sh"]