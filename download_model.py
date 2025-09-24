#!/usr/bin/env python

import os
import json
import torch
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer, AutoModel

def download_and_prepare_model():
    """Download and prepare the paraphrase-multilingual-mpnet-base-v2 model for OpenSearch"""
    # Read configuration from environment variables with sensible defaults
    hf_id = os.getenv("MODEL_HF_ID", "sentence-transformers/paraphrase-multilingual-mpnet-base-v2")
    model_name = os.getenv("MODEL_NAME", "paraphrase-multilingual-mpnet-base-v2")
    embed_dim = int(os.getenv("MODEL_EMBED_DIM", "768"))
    max_seq_len = int(os.getenv("MODEL_MAX_SEQ_LEN", "384"))
    model_dir = os.getenv("MODEL_DIR", "/usr/share/opensearch/ml_models")
    model_path = os.path.join(model_dir, model_name)
    
    print(f"📥 Downloading model from HF: {hf_id}")
    print(f"   Saving as: {model_name} in {model_dir}")
    
    try:
        # Download the sentence transformer model
        model = SentenceTransformer(hf_id)
        
        # Save the complete model
        model.save(model_path)
        print(f"✅ Model saved to: {model_path}")
        
        # Create model configuration for OpenSearch
        model_config = {
            "name": model_name,
            "version": "1.0.0",
            "description": "Sentence-Transformers model for semantic search",
            "model_format": "TORCH_SCRIPT",
            "model_config": {
                "model_type": "sentence_transformers",
                "embedding_dimension": embed_dim,
                "framework_type": "sentence_transformers",
                "all_config": json.dumps({
                    "model_name": hf_id,
                    "normalize_embeddings": True,
                    "pooling_mode": "mean",
                    "max_seq_length": max_seq_len
                })
            }
        }
        
        # Save model configuration
        config_path = os.path.join(model_path, "ml-model-config.json")
        with open(config_path, 'w') as f:
            json.dump(model_config, f, indent=2)
        
        print(f"✅ Model configuration saved to: {config_path}")
        
        # Create a simple test to verify the model works
        test_sentences = ["This is a test sentence", "This is another test"]
        embeddings = model.encode(test_sentences)
        print(f"✅ Model test successful. Embedding shape: {embeddings.shape}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error downloading model: {str(e)}")
        return False

if __name__ == "__main__":
    success = download_and_prepare_model()
    if success:
        print("🎉 Model download and preparation completed successfully!")
    else:
        print("💥 Model download failed!")
        exit(1)

