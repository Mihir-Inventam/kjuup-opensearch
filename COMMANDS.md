# Reproducible Commands Log

This file summarizes the key commands used to build, run, register, and deploy the custom ML model in OpenSearch, and finally commit the project to GitHub.

Replace placeholders like <TASK_ID>, <DEPLOY_TASK_ID>, <MODEL_ID>, and <GITHUB_REPO_URL> as instructed.

---

## 1) Docker Compose: Build/Run

```bash
# From project root: /home/its-lp-m-24/kjuup-opensearch

docker-compose down

docker-compose up -d

# Check containers
 docker ps

# Check OpenSearch cluster health
 curl -k -u admin:'KjuupInventam@519UTC' \
  "https://localhost:9200/_cluster/health?pretty"
```

---

## 2) Ensure in-container HTTP server is running (serves the model ZIP)

```bash
# Start HTTP server inside the OpenSearch container
 docker exec -d opensearch-secure bash -lc '
   cd /usr/share/opensearch/ml_models &&
   nohup python3 -m http.server 8000 > /tmp/ml_http.log 2>&1 || true
 '

# Verify the ZIP is reachable (expect HTTP/1.0 200 OK)
 docker exec opensearch-secure bash -lc \
  'curl -sI http://127.0.0.1:8000/paraphrase-multilingual-mpnet-base-v2.flat.zip | head -n 1'
```

---

## 3) Compute ZIP hash and size (if needed)

```bash
# SHA-256 hash of the flat ZIP
 docker exec opensearch-secure bash -lc \
  'sha256sum /usr/share/opensearch/ml_models/paraphrase-multilingual-mpnet-base-v2.flat.zip | awk "{print $1}"'

# Size in bytes
 docker exec opensearch-secure bash -lc \
  'stat -c %s /usr/share/opensearch/ml_models/paraphrase-multilingual-mpnet-base-v2.flat.zip'
```

Known values used in this setup:
- model_content_hash_value: `0e6b0c04b1571504807406c839d537d2282d03f2121f6c2b40849269eef2d7b0`
- model_content_size_in_bytes: `3032556292`

---

## 4) Register the model via URL (with hash + size)

```bash
# Create payload file (adjust name if you register anew)
cat > /tmp/register_payload.json <<'JSON'
{
  "name": "paraphrase-multilingual-mpnet-base-v2-v3",
  "model_format": "TORCH_SCRIPT",
  "function_name": "TEXT_EMBEDDING",
  "version": "1.0.0",
  "model_config": {
    "model_type": "sentence_transformers",
    "embedding_dimension": 768,
    "framework_type": "sentence_transformers",
    "all_config": "{\"model_name\":\"sentence-transformers/paraphrase-multilingual-mpnet-base-v2\",\"normalize_embeddings\":true,\"pooling_mode\":\"mean\",\"max_seq_length\":384}"
  },
  "url": "http://127.0.0.1:8000/paraphrase-multilingual-mpnet-base-v2.flat.zip",
  "model_content_hash_value": "0e6b0c04b1571504807406c839d537d2282d03f2121f6c2b40849269eef2d7b0",
  "model_content_size_in_bytes": 3032556292
}
JSON

# Submit registration
curl -k -u admin:'KjuupInventam@519UTC' \
  -H 'Content-Type: application/json' \
  -X POST 'https://localhost:9200/_plugins/_ml/models/_register' \
  -d @/tmp/register_payload.json
# → Capture the task_id from the response
```

---

## 5) Track registration task until COMPLETED

```bash
# Replace <TASK_ID> with the ID returned from the register call
curl -k -u admin:'KjuupInventam@519UTC' \
  "https://localhost:9200/_plugins/_ml/tasks/<TASK_ID>?pretty"

# Optional: list active tasks
curl -k -u admin:'KjuupInventam@519UTC' \
  "https://localhost:9200/_plugins/_ml/tasks?pretty"
```

Only proceed after the registration task reaches `COMPLETED`.

---

## 6) Find the model document and get model_id

```bash
curl -k -u admin:'KjuupInventam@519UTC' \
  -H "Content-Type: application/json" \
  -X POST "https://localhost:9200/_plugins/_ml/models/_search" \
  -d '{ "size": 1, "query": { "term": { "name.keyword": "paraphrase-multilingual-mpnet-base-v2-v3" } } }'
# → Copy the _id from the first hit as MODEL_ID
```

---

## 7) Deploy the model (only after model_state is REGISTERED)

```bash
# Deploy
MODEL_ID=<paste__id_from_search>
curl -k -u admin:'KjuupInventam@519UTC' -X POST \
  "https://localhost:9200/_plugins/_ml/models/$MODEL_ID/_deploy"
# → Capture DEPLOY_TASK_ID from response

# Poll deploy task
DEPLOY_TASK_ID=<paste_task_id>
curl -k -u admin:'KjuupInventam@519UTC' \
  "https://localhost:9200/_plugins/_ml/tasks/$DEPLOY_TASK_ID?pretty"
```

---

## 8) Verify DEPLOYED and run a quick prediction

```bash
# Confirm model state is DEPLOYED
curl -k -u admin:'KjuupInventam@519UTC' \
  -H "Content-Type: application/json" \
  -X POST "https://localhost:9200/_plugins/_ml/models/_search" \
  -d '{ "size": 1, "query": { "term": { "name.keyword": "paraphrase-multilingual-mpnet-base-v2-v3" } } }'

# Quick prediction (replace with your MODEL_ID)
MODEL_ID=<paste__id_from_search>
curl -k -u admin:'KjuupInventam@519UTC' \
  -H "Content-Type: application/json" \
  -X POST "https://localhost:9200/_plugins/_ml/models/$MODEL_ID/_predict" \
  -d '{
    "text_docs": [
      "OpenSearch is a powerful search and analytics engine",
      "This is a test sentence for semantic similarity"
    ]
  }'
```

---

## 9) Useful diagnostics

```bash
# Check JVM flags (verify -Xms4g -Xmx4g under the OpenSearch node)
curl -k -u admin:'KjuupInventam@519UTC' \
  "https://localhost:9200/_nodes/jvm?pretty" | grep -E -- "-Xms|-Xmx"

# Tail ML-related logs for errors/exceptions
docker logs opensearch-secure | grep -i -E "ml|model|chunk|error|exception" | tail -n 200
```

---

## 10) GitHub: initialize repo and push

```bash
# Initialize repository
git init

# Optionally set your identity
git config user.name "Your Name"
git config user.email "you@example.com"

# Create a .gitignore (optional)
cat > .gitignore <<'EOF'
# Python
__pycache__/
*.pyc

# Env
.env
venv/

# OS
.DS_Store

# Docker and volumes (keep these ignored if you do not want to commit data)
.opensearch-data/
.opensearch-models/
EOF

# Stage and commit
git add .
git commit -m "OpenSearch + ML Commons: custom model setup, registration & deployment scripts"

# Create main branch and add remote
git branch -M main
git remote add origin <GITHUB_REPO_URL>

# Push
git push -u origin main
```

Notes:
- Replace `<GITHUB_REPO_URL>` with your repository (e.g., `git@github.com:yourname/yourrepo.git` or `https://github.com/yourname/yourrepo.git`).
- If you want to include or exclude specific files (e.g., large zips), adjust `.gitignore` accordingly.
