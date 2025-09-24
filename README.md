# OpenSearch with Custom ML Model Setup

This repository contains a Docker-based setup for OpenSearch with a pre-configured custom machine learning model: `paraphrase-multilingual-mpnet-base-v2`.

## 🎯 Overview

This setup provides:
- **OpenSearch 2.15.0** with ML Commons plugin enabled
- **Custom ML Model**: `paraphrase-multilingual-mpnet-base-v2` for multilingual semantic search
- **Python 3.12** environment with sentence-transformers
- **Automated model registration** and deployment
- **OpenSearch Dashboards** for visualization and management

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────┐
│                Docker Compose                   │
├─────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────────┐   │
│  │   OpenSearch    │  │ OpenSearch Dashboards│   │
│  │                 │  │                     │   │
│  │ Custom Model:   │  │ Port: 5601          │   │
│  │ paraphrase-     │  │                     │   │
│  │ multilingual-   │  │                     │   │
│  │ mpnet-base-v2   │  │                     │   │
│  │                 │  │                     │   │
│  │ Port: 9200      │  │                     │   │
│  └─────────────────┘  └─────────────────────┘   │
└─────────────────────────────────────────────────┘
```

## 📋 Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- At least 4GB RAM available for the container
- Internet connection for downloading the model

## 🚀 Quick Start

1. **Clone and navigate to the directory:**
   ```bash
   cd /path/to/kjuup-opensearch
   ```

2. **Build and start the services:**
   ```bash
   docker-compose up --build
   ```

3. **Wait for initialization:**
   - OpenSearch will start first
   - The custom model will be downloaded and registered automatically
   - This process may take 5-10 minutes on first run

4. **Access the services:**
   - **OpenSearch API**: https://localhost:9200
   - **OpenSearch Dashboards**: http://localhost:5601
   - **Credentials**: admin / KjuupInventam@519UTC

## 🔧 Configuration

### Model Configuration

### Environment Variables

Key environment variables in `docker-compose.yml`:

```yaml
environment:
  - discovery.type=single-node
  - OPENSEARCH_INITIAL_ADMIN_PASSWORD=KjuupInventam@519UTC
  - OPENSEARCH_JAVA_OPTS=-Xms2g -Xmx2g
  - plugins.ml_commons.only_run_on_ml_node=false
  - plugins.ml_commons.allow_registering_model_via_local_file=true
  - plugins.ml_commons.native_memory_threshold=99
  - plugins.ml_commons.max_model_on_node=10
```

### Parameterizable Model and Connection Variables

The setup supports switching models without code changes. These env vars are read by `download_model.py`, `register_model.py`, and `test_model.py`:
├── docker-compose.yml          # Docker Compose configuration
├── Dockerfile                  # Custom OpenSearch image with Python 3.12
├── requirements.txt            # Python dependencies
├── download_model.py           # Model download and preparation script
├── register_model.py           # Model registration with OpenSearch
├── startup.sh                  # Custom startup script
└── README.md                   # This documentation
```

## 🔍 Using the Custom Model

### 1. Check Model Status

```bash
curl -k -u admin:KjuupInventam@519UTC \
  "https://localhost:9200/_plugins/_ml/models"
```

### 2. Generate Embeddings

```bash
curl -k -u admin:KjuupInventam@519UTC \
  -H "Content-Type: application/json" \
  -X POST "https://localhost:9200/_plugins/_ml/models/{MODEL_ID}/_predict" \
  -d '{
    "text_docs": [
      "This is a sample text for embedding generation",
      "Another text for semantic similarity"
    ]
  }'
```

### 3. Create a Search Index with Vector Field

```bash
curl -k -u admin:KjuupInventam@519UTC \
  -H "Content-Type: application/json" \
  -X PUT "https://localhost:9200/semantic-search" \
  -d '{
    "mappings": {
      "properties": {
        "content": {"type": "text"},
        "content_vector": {
          "type": "knn_vector",
          "dimension": 768,
          "method": {
            "name": "hnsw",
            "space_type": "cosinesimil"
          }
        }
      }
    }
  }'
```

## 🛠️ Troubleshooting

### Common Issues

1. **Model Registration Failed**
   ```bash
   # Check registration logs
   docker exec opensearch-secure cat /tmp/model_registration.log
   ```

2. **Memory Issues**
   ```bash
   # Increase Docker memory limit to at least 4GB
   # Check current memory usage
   docker stats opensearch-secure
   ```

3. **Connection Issues**
   ```bash
   # Check if OpenSearch is running
   curl -k -u admin:KjuupInventam@519UTC https://localhost:9200/_cluster/health
   ```

### Logs

- **OpenSearch logs**: `docker logs opensearch-secure`
- **Model registration logs**: `docker exec opensearch-secure cat /tmp/model_registration.log`
- **Dashboards logs**: `docker logs opensearch-dashboards`

## 🔄 Manual Model Registration

If automatic registration fails, you can manually register the model:

```bash
# Enter the container
docker exec -it opensearch-secure bash

# Run the registration script
cd /usr/share/opensearch/scripts
python3.12 register_model.py
```

## 📊 Performance Tuning

### Memory Settings

Adjust memory settings in `docker-compose.yml`:

```yaml
environment:
  - OPENSEARCH_JAVA_OPTS=-Xms4g -Xmx4g  # Increase heap size
deploy:
  resources:
    limits:
      memory: 8g  # Increase container memory
```

### Model Settings

Tune ML Commons settings:

```yaml
environment:
  - plugins.ml_commons.native_memory_threshold=80  # Adjust threshold
  - plugins.ml_commons.max_model_on_node=5         # Limit concurrent models
```

## 🧪 Testing the Setup

Run the test script to verify everything is working:

```bash
# Test model functionality
docker exec opensearch-secure python3.12 /usr/share/opensearch/scripts/register_model.py
```

## 📚 Additional Resources

- [OpenSearch ML Commons Documentation](https://opensearch.org/docs/latest/ml-commons-plugin/)
- [Sentence Transformers Documentation](https://www.sbert.net/)
- [Docker Compose Reference](https://docs.docker.com/compose/)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**Note**: This setup is optimized for development and testing. For production use, consider additional security measures, monitoring, and backup strategies.
