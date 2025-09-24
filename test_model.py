#!/usr/bin/env python3.12

import requests
import json
import time
from requests.auth import HTTPBasicAuth
from urllib3.exceptions import InsecureRequestWarning
import os

# Disable SSL warnings
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

def test_opensearch_model():
    """Test the deployed OpenSearch ML model"""
    
    host = os.getenv("OPENSEARCH_HOST", "https://localhost:9200")
    username = os.getenv("OPENSEARCH_USERNAME", "admin")
    password = os.getenv("OPENSEARCH_PASSWORD", "KjuupInventam@519UTC")
    model_name = os.getenv("MODEL_NAME", "paraphrase-multilingual-mpnet-base-v2")
    auth = HTTPBasicAuth(username, password)
    headers = {"Content-Type": "application/json"}
    
    print("🧪 Testing OpenSearch ML Model Setup")
    print("=" * 50)
    
    # Test 1: Check cluster health
    print("\n1️⃣ Testing cluster health...")
    try:
        response = requests.get(f"{host}/_cluster/health", auth=auth, headers=headers, verify=False)
        if response.status_code == 200:
            health = response.json()
            print(f"✅ Cluster Status: {health.get('status', 'unknown')}")
            print(f"   Nodes: {health.get('number_of_nodes', 0)}")
        else:
            print(f"❌ Cluster health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error checking cluster health: {str(e)}")
        return False
    
    # Test 2: List available models
    print("\n2️⃣ Checking available ML models...")
    try:
        response = requests.get(f"{host}/_plugins/_ml/models", auth=auth, headers=headers, verify=False)
        if response.status_code == 200:
            models = response.json()
            print(f"✅ Found {len(models.get('hits', {}).get('hits', []))} models")
            
            # Find our custom model
            custom_model = None
            for hit in models.get('hits', {}).get('hits', []):
                source = hit.get('_source', {})
                if model_name == source.get('name', ''):
                    custom_model = hit
                    break
            
            if custom_model:
                model_id = custom_model['_id']
                model_name = custom_model['_source']['name']
                model_state = custom_model['_source'].get('model_state', 'unknown')
                print(f"✅ Found custom model: {model_name}")
                print(f"   Model ID: {model_id}")
                print(f"   State: {model_state}")
                
                if model_state == 'DEPLOYED':
                    return test_model_prediction(host, auth, headers, model_id)
                else:
                    print(f"⚠️  Model is not deployed (State: {model_state})")
                    return False
            else:
                print("❌ Custom model not found")
                return False
        else:
            print(f"❌ Failed to list models: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error listing models: {str(e)}")
        return False

def test_model_prediction(host, auth, headers, model_id):
    """Test model prediction functionality"""
    
    print("\n3️⃣ Testing model prediction...")
    
    test_texts = [
        "OpenSearch is a powerful search and analytics engine",
        "This is a test sentence for semantic similarity",
        "Machine learning models can understand text meaning",
        "Vector search enables semantic document retrieval"
    ]
    
    prediction_data = {
        "text_docs": test_texts
    }
    
    try:
        response = requests.post(
            f"{host}/_plugins/_ml/models/{model_id}/_predict",
            auth=auth,
            headers=headers,
            json=prediction_data,
            verify=False,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            inference_results = result.get('inference_results', [])
            
            print(f"✅ Model prediction successful!")
            print(f"   Processed {len(test_texts)} text documents")
            
            for i, (text, inference) in enumerate(zip(test_texts, inference_results)):
                output = inference.get('output', [])
                if output and len(output[0].get('data', [])) > 0:
                    embedding_dim = len(output[0]['data'])
                    print(f"   Text {i+1}: Generated {embedding_dim}-dimensional embedding")
                    print(f"      \"{text[:50]}{'...' if len(text) > 50 else ''}\"")
            
            # Test semantic similarity
            print("\n4️⃣ Testing semantic similarity...")
            if len(inference_results) >= 2:
                emb1 = inference_results[0]['output'][0]['data']
                emb2 = inference_results[1]['output'][0]['data']
                
                # Calculate cosine similarity
                import math
                dot_product = sum(a * b for a, b in zip(emb1, emb2))
                magnitude1 = math.sqrt(sum(a * a for a in emb1))
                magnitude2 = math.sqrt(sum(b * b for b in emb2))
                similarity = dot_product / (magnitude1 * magnitude2)
                
                print(f"✅ Cosine similarity between first two texts: {similarity:.4f}")
            
            return True
        else:
            print(f"❌ Model prediction failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing model prediction: {str(e)}")
        return False

def main():
    """Main test function"""
    print("🚀 OpenSearch Custom Model Test Suite")
    print(f"Testing {os.getenv('MODEL_NAME', 'paraphrase-multilingual-mpnet-base-v2')} model")
    
    success = test_opensearch_model()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 All tests passed! Your custom model is working correctly.")
        print("\n💡 You can now use this model for:")
        print("   • Semantic search")
        print("   • Text similarity")
        print("   • Document clustering")
        print("   • Multilingual text analysis")
    else:
        print("❌ Some tests failed. Check the logs and configuration.")
        print("\n🔧 Troubleshooting tips:")
        print("   • Ensure OpenSearch is fully started")
        print("   • Check if model registration completed")
        print("   • Verify model deployment status")
        print("   • Review container logs: docker logs opensearch-secure")
    
    return success

if __name__ == "__main__":
    success = main()
    if not success:
        exit(1)

