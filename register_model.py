#!/usr/bin/env python

import requests
import json
import time
import os
from requests.auth import HTTPBasicAuth
from urllib3.exceptions import InsecureRequestWarning

# Disable SSL warnings for self-signed certificates
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

class OpenSearchModelRegistrar:
    def __init__(self,
                 host: str | None = None,
                 username: str | None = None,
                 password: str | None = None,
                 model_name: str | None = None,
                 model_hf_id: str | None = None,
                 embed_dim: int | None = None,
                 max_seq_len: int | None = None,
                 model_dir: str | None = None):
        # Read connection config
        self.host = host or os.getenv("OPENSEARCH_HOST", "https://localhost:9200")
        self.auth = HTTPBasicAuth(
            username or os.getenv("OPENSEARCH_USERNAME", "admin"),
            password or os.getenv("OPENSEARCH_PASSWORD", "KjuupInventam@519UTC")
        )
        self.headers = {"Content-Type": "application/json"}
        
        # Read model config
        self.model_name = model_name or os.getenv("MODEL_NAME", "paraphrase-multilingual-mpnet-base-v2")
        self.model_hf_id = model_hf_id or os.getenv("MODEL_HF_ID", "sentence-transformers/paraphrase-multilingual-mpnet-base-v2")
        self.embed_dim = int(embed_dim or os.getenv("MODEL_EMBED_DIM", "768"))
        self.max_seq_len = int(max_seq_len or os.getenv("MODEL_MAX_SEQ_LEN", "384"))
        self.model_dir = model_dir or os.getenv("MODEL_DIR", "/usr/share/opensearch/ml_models")
        self.model_url = f"file://{self.model_dir.rstrip('/')}/{self.model_name}/"
        
    def wait_for_opensearch(self, max_attempts=30, delay=10):
        """Wait for OpenSearch to be ready"""
        print("🔄 Waiting for OpenSearch to be ready...")
        
        for attempt in range(max_attempts):
            try:
                response = requests.get(
                    f"{self.host}/_cluster/health",
                    auth=self.auth,
                    headers=self.headers,
                    verify=False,
                    timeout=5
                )
                if response.status_code == 200:
                    health = response.json()
                    if health.get("status") in ["green", "yellow"]:
                        print("✅ OpenSearch is ready!")
                        return True
            except Exception as e:
                print(f"⏳ Attempt {attempt + 1}/{max_attempts}: OpenSearch not ready yet ({str(e)})")
                
            time.sleep(delay)
        
        print("❌ OpenSearch failed to become ready")
        return False
    
    def find_model_by_name(self, name: str):
        """Return (model_id, state) if a model with the given name exists, else (None, None)"""
        try:
            payload = {
                "size": 1,
                "query": {
                    "term": {"name.keyword": name}
                }
            }
            response = requests.post(
                f"{self.host}/_plugins/_ml/models/_search",
                auth=self.auth,
                headers=self.headers,
                json=payload,
                verify=False,
                timeout=15
            )
            if response.status_code == 200:
                models = response.json().get('hits', {}).get('hits', [])
                if models:
                    hit = models[0]
                    source = hit.get('_source', {})
                    return hit.get('_id'), source.get('model_state')
            else:
                print(f"⚠️ Failed to list models: {response.status_code} {response.text}")
        except Exception as e:
            print(f"⚠️ Error listing models: {str(e)}")
        return None, None
    
    def register_model(self):
        """Register the model if not already registered; returns model_id."""
        
        # Idempotent: reuse if already registered
        existing_id, existing_state = self.find_model_by_name(self.model_name)
        if existing_id:
            print(f"ℹ️ Model already registered: {self.model_name} (ID: {existing_id}, State: {existing_state})")
            return existing_id
        
        model_config = {
            "name": self.model_name,
            "version": "1.0.0",
            "description": "Sentence-Transformers model for semantic search and text similarity",
            "model_format": "TORCH_SCRIPT",
            "model_config": {
                "model_type": "sentence_transformers",
                "embedding_dimension": self.embed_dim,
                "framework_type": "sentence_transformers",
                "all_config": json.dumps({
                    "model_name": self.model_hf_id,
                    "normalize_embeddings": True,
                    "pooling_mode": "mean",
                    "max_seq_length": self.max_seq_len
                })
            },
            "url": self.model_url
        }
        
        print("📝 Registering model with OpenSearch ML Commons...")
        
        try:
            response = requests.post(
                f"{self.host}/_plugins/_ml/models/_register",
                auth=self.auth,
                headers=self.headers,
                json=model_config,
                verify=False,
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                result = response.json()
                model_id = result.get("model_id")
                task_id = result.get("task_id")
                
                print(f"✅ Model registration initiated!")
                print(f"   Model ID: {model_id}")
                print(f"   Task ID: {task_id}")
                
                if task_id:
                    return self.wait_for_model_registration(task_id)
                else:
                    return model_id
                    
            else:
                print(f"❌ Model registration failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Error registering model: {str(e)}")
            return None
    
    def wait_for_model_registration(self, task_id, max_attempts=30, delay=10):
        """Wait for model registration to complete"""
        print(f"⏳ Waiting for model registration to complete (Task ID: {task_id})...")
        
        for attempt in range(max_attempts):
            try:
                response = requests.get(
                    f"{self.host}/_plugins/_ml/tasks/{task_id}",
                    auth=self.auth,
                    headers=self.headers,
                    verify=False,
                    timeout=10
                )
                
                if response.status_code == 200:
                    task_info = response.json()
                    state = task_info.get("state", "").upper()
                    
                    if state == "COMPLETED":
                        model_id = task_info.get("model_id")
                        print(f"✅ Model registration completed! Model ID: {model_id}")
                        return model_id
                    elif state == "FAILED":
                        error = task_info.get("error", "Unknown error")
                        print(f"❌ Model registration failed: {error}")
                        return None
                    else:
                        print(f"⏳ Registration in progress... State: {state}")
                        
            except Exception as e:
                print(f"⚠️  Error checking task status: {str(e)}")
                
            time.sleep(delay)
        
        print("❌ Model registration timed out")
        return None
    
    def deploy_model(self, model_id):
        """Deploy the registered model"""
        print(f"🚀 Deploying model {model_id}...")
        
        # If already deployed, return early
        existing_id, existing_state = self.find_model_by_name(self.model_name)
        if existing_id == model_id and str(existing_state).upper() == "DEPLOYED":
            print("ℹ️ Model is already deployed. Skipping deployment.")
            return True

        try:
            response = requests.post(
                f"{self.host}/_plugins/_ml/models/{model_id}/_deploy",
                auth=self.auth,
                headers=self.headers,
                verify=False,
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                result = response.json()
                task_id = result.get("task_id")
                print(f"✅ Model deployment initiated! Task ID: {task_id}")
                
                if task_id:
                    return self.wait_for_model_deployment(task_id)
                else:
                    return True
                    
            else:
                print(f"❌ Model deployment failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error deploying model: {str(e)}")
            return False
    
    def wait_for_model_deployment(self, task_id, max_attempts=20, delay=10):
        """Wait for model deployment to complete"""
        print(f"⏳ Waiting for model deployment to complete (Task ID: {task_id})...")
        
        for attempt in range(max_attempts):
            try:
                response = requests.get(
                    f"{self.host}/_plugins/_ml/tasks/{task_id}",
                    auth=self.auth,
                    headers=self.headers,
                    verify=False,
                    timeout=10
                )
                
                if response.status_code == 200:
                    task_info = response.json()
                    state = task_info.get("state", "").upper()
                    
                    if state == "COMPLETED":
                        print("✅ Model deployment completed!")
                        return True
                    elif state == "FAILED":
                        error = task_info.get("error", "Unknown error")
                        print(f"❌ Model deployment failed: {error}")
                        return False
                    else:
                        print(f"⏳ Deployment in progress... State: {state}")
                        
            except Exception as e:
                print(f"⚠️  Error checking deployment status: {str(e)}")
                
            time.sleep(delay)
        
        print("❌ Model deployment timed out")
        return False
    
    def test_model(self, model_id):
        """Test the deployed model"""
        print(f"🧪 Testing model {model_id}...")
        
        test_data = {
            "text_docs": [
                "This is a test sentence for semantic search",
                "OpenSearch is a powerful search engine"
            ]
        }
        
        try:
            response = requests.post(
                f"{self.host}/_plugins/_ml/models/{model_id}/_predict",
                auth=self.auth,
                headers=self.headers,
                json=test_data,
                verify=False,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                print("✅ Model test successful!")
                print(f"   Generated embeddings for {len(test_data['text_docs'])} documents")
                return True
            else:
                print(f"❌ Model test failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error testing model: {str(e)}")
            return False

def main():
    """Main function to register and deploy the model"""
    print("🚀 Starting OpenSearch ML model registration process...")
    
    registrar = OpenSearchModelRegistrar()
    
    # Wait for OpenSearch to be ready
    if not registrar.wait_for_opensearch():
        print("💥 Failed to connect to OpenSearch")
        return False
    
    # Register the model
    model_id = registrar.register_model()
    if not model_id:
        print("💥 Model registration failed")
        return False
    
    # Deploy the model
    if not registrar.deploy_model(model_id):
        print("💥 Model deployment failed")
        return False
    
    # Test the model
    if not registrar.test_model(model_id):
        print("💥 Model test failed")
        return False
    
    print("🎉 Model registration, deployment, and testing completed successfully!")
    print(f"   Model ID: {model_id}")
    print(f"   Model Name: {registrar.model_name}")
    print("   You can now use this model for semantic search and text similarity tasks!")
    
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        exit(1)

