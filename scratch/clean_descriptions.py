# scratch/clean_descriptions.py
# Clean up existing static JSON model files to replace hardcoded fallback descriptions
# with intelligent capability-based descriptions.

import json
import os
import re

def get_dynamic_description(model_id, developer):
    model_id_lower = model_id.lower()
    developer_clean = developer if developer else "AI Developer"
    
    caps = []
    if "code" in model_id_lower or "coder" in model_id_lower:
        caps.append("software development, code synthesis, and advanced technical programming tasks")
    elif "math" in model_id_lower:
        caps.append("complex mathematical computation and structured algorithmic reasoning")
    elif "vision" in model_id_lower or "vl" in model_id_lower or "multimodal" in model_id_lower:
        caps.append("multimodal vision analysis and optical/contextual document understanding")
    elif "instruct" in model_id_lower or "-it" in model_id_lower or "chat" in model_id_lower:
        caps.append("instruction-following tasks and multi-turn interactive dialogue")
    else:
        caps.append("general purpose text generation, clean reasoning, and semantic parsing")
        
    cap_desc = " and ".join(caps[:2])
    return f"High-performance generative model developed by {developer_clean.capitalize()} designed for {cap_desc}."

def clean_shard(filepath):
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return
        
    print(f"Processing shard: {filepath}...")
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    updated_count = 0
    for model in data.get("models", []):
        desc = model.get("description", "")
        # Match any presence of "Recovered chat model" or "untested" or empty descriptions
        if not desc or "recovered" in desc.lower() or "untested" in desc.lower() or "general purpose tasks" in desc.lower():
            model_id = model.get("id", "")
            developer = model.get("developer", "")
            if not developer and '/' in model_id:
                developer = model_id.split('/')[0]
            
            new_desc = get_dynamic_description(model_id, developer)
            model["description"] = new_desc
            updated_count += 1
            
    if updated_count > 0:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"Successfully cleaned {updated_count} models in {filepath}!")
    else:
        print(f"No models needed description updates in {filepath}.")

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    shards_dir = os.path.join(base_dir, "resources", "model_json")
    
    print(f"Scanning models folder: {shards_dir}")
    shards = ["models_nvidia.json", "models_deepseek.json", "models_google.json"]
    
    for shard in shards:
        filepath = os.path.join(shards_dir, shard)
        clean_shard(filepath)
    
    print("\nDescription cleanup finished successfully!")
