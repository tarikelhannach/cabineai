#!/bin/bash

# Start Redis and Elasticsearch in the background
echo "🚀 Starting infrastructure services..."
docker-compose up -d redis elasticsearch

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 5

# Check Redis
if docker-compose exec -T redis redis-cli ping | grep -q "PONG"; then
    echo "✅ Redis is ready"
else
    echo "❌ Redis failed to start"
fi

# Check Elasticsearch
if curl -s http://localhost:9200/_cluster/health | grep -q "status"; then
    echo "✅ Elasticsearch is ready"
else
    echo "❌ Elasticsearch failed to start (might need more time)"
fi

echo "
🎉 Services started!
- Redis: localhost:6379
- Elasticsearch: localhost:9200
"
