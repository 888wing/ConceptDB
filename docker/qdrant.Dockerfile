FROM qdrant/qdrant:latest

# Expose port
EXPOSE 6333

# Use default Qdrant entrypoint
CMD ["./qdrant"]