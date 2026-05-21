# test_reranker.py
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from logic.rerank_engine import RerankEngine

def run_test():
    print("=== Testing RerankEngine Offline Fallback & Advanced Stages ===")
    
    engine = RerankEngine.get_instance()
    
    # We will simulate a query and a set of top-20 retrieved candidate chunks.
    # Some chunks will have programming structural keywords.
    # Some chunks will be highly redundant to test MMR.
    query = "How do we define class MainWindow in PySide6?"
    
    hits = [
        # Candidate 1: Perfect match with structural keywords
        {
            "payload": {
                "text": "class MainWindow(QMainWindow):\n    def __init__(self):\n        super().__init__()\n        self.setWindowTitle('Test App')"
            },
            "score": 0.8
        },
        # Candidate 2: Highly similar to Candidate 1 (conceptually redundant)
        {
            "payload": {
                "text": "class MainWindow(QMainWindow):\n    def __init__(self):\n        super().__init__()\n        # Just a slightly different comment\n        self.setWindowTitle('Test App')"
            },
            "score": 0.79
        },
        # Candidate 3: General plain text without structural keywords
        {
            "payload": {
                "text": "This guide explains how to build a basic user interface with PySide6 and set up your windows and controls."
            },
            "score": 0.5
        },
        # Candidate 4: Another code block with functions but different content
        {
            "payload": {
                "text": "def setup_ui(dialog):\n    dialog.resize(400, 300)\n    button = QPushButton('Save', dialog)"
            },
            "score": 0.6
        }
    ]
    
    # Run local engine (offline Jaccard / ONNX fallback)
    settings = {
        "rerank_enabled": "true",
        "rerank_engine": "local"
    }
    
    print("\nRunning Rerank...")
    results = engine.rerank(query, hits, top_k=3, settings=settings)
    
    print("\n--- Rerank Results ---")
    for idx, r in enumerate(results):
        text_snippet = r["payload"]["text"].replace('\n', ' ')[:80]
        print(f"Rank {idx+1}: Score={r.get('score'):.4f} | Structural Boosted={r.get('structural_boosted')} | MMR Penalized={r.get('mmr_penalized', False)} | Snippet: {text_snippet}")

if __name__ == "__main__":
    run_test()
