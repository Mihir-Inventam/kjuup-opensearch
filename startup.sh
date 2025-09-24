#!/bin/bash

# OpenSearch Startup Script with Custom Model Registration
# This script starts OpenSearch and automatically registers the custom model

set -e

echo "🚀 Starting OpenSearch with custom model setup..."

# Set environment variables
export PATH="/opt/venv/bin:$PATH"

# Function to log messages
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Function to check if OpenSearch is running
check_opensearch() {
    curl -k -u admin:KjuupInventam@519UTC \
         -H "Content-Type: application/json" \
         "https://localhost:9200/_cluster/health" \
         --max-time 5 --silent > /dev/null 2>&1
}

# Prepare model directory in mounted volume and download if missing
prepare_model_dir() {
    MODEL_DIR_PATH="${MODEL_DIR:-/usr/share/opensearch/ml_models}"
    MODEL_NAME_VAL="${MODEL_NAME:-paraphrase-multilingual-mpnet-base-v2}"

    log "📁 Ensuring model directory exists and is accessible: ${MODEL_DIR_PATH}"
    mkdir -p "${MODEL_DIR_PATH}"
    # We may be running as root here; set ownership so OpenSearch (opensearch user) can read
    chown -R opensearch:opensearch "${MODEL_DIR_PATH}" || true

    # If the model directory is missing or empty, download the model into the volume
    if [ ! -d "${MODEL_DIR_PATH}/${MODEL_NAME_VAL}" ] || [ -z "$(ls -A "${MODEL_DIR_PATH}/${MODEL_NAME_VAL}" 2>/dev/null)" ]; then
        log "⬇️  Model not found in volume. Downloading model: ${MODEL_NAME_VAL}"
        cd /usr/share/opensearch/scripts
        python download_model.py || {
            log "❌ Model download failed"
            return 1
        }
        chown -R opensearch:opensearch "${MODEL_DIR_PATH}/${MODEL_NAME_VAL}" || true
        log "✅ Model downloaded into volume"
    else
        log "ℹ️ Model already present in volume. Skipping download."
    fi
}

# Function to register the model in background
register_model_async() {
    log "🔄 Starting model registration process in background..."
    
    # Wait a bit for OpenSearch to fully initialize
    sleep 30
    
    # Run the model registration script
    cd /usr/share/opensearch/scripts
    python register_model.py > /tmp/model_registration.log 2>&1
    
    if [ $? -eq 0 ]; then
        log "✅ Model registration completed successfully!"
        log "📋 Check /tmp/model_registration.log for details"
    else
        log "❌ Model registration failed!"
        log "📋 Check /tmp/model_registration.log for error details"
    fi
}

# Prepare volume and model before starting registration
prepare_model_dir || true

# Start the model registration process in background
register_model_async &

log "🔧 Starting OpenSearch daemon..."

# Start OpenSearch using the original entrypoint
# If running as root, drop privileges to 'opensearch' user before starting
if [ "$(id -u)" -eq 0 ]; then
  if command -v runuser >/dev/null 2>&1; then
    exec runuser -u opensearch -- /usr/share/opensearch/opensearch-docker-entrypoint.sh
  elif command -v su >/dev/null 2>&1; then
    exec su -s /bin/bash -c "/usr/share/opensearch/opensearch-docker-entrypoint.sh" opensearch
  else
    echo "Missing 'runuser'/'su' to drop privileges; attempting direct exec (may fail)" >&2
    exec /usr/share/opensearch/opensearch-docker-entrypoint.sh
  fi
else
  exec /usr/share/opensearch/opensearch-docker-entrypoint.sh
fi

