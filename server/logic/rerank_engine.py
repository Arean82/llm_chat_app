# logic/rerank_engine.py
import re
import json
import urllib.request
from typing import List, Dict, Any, Optional

class RerankEngine:
    """
    Two-Stage Hybrid Reranker Engine.
    Coordinates local BGE ONNX/SentenceTransformers, remote Cohere v3, and custom OpenAPI endpoints.
    Applies Hybrid A (Structural Code Bias) and Hybrid B (Maximal Marginal Relevance Diversity).
    """
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        # Dynamic import checking to guarantee zero startup crashes
        self.onnx_available = False
        self.sentence_transformers_available = False
        
        try:
            import onnxruntime
            self.onnx_available = True
        except ImportError:
            pass

        try:
            import sentence_transformers
            self.sentence_transformers_available = True
        except ImportError:
            pass

        print(f"[RerankEngine] Initialized. ONNX Available: {self.onnx_available}, SentenceTransformers Available: {self.sentence_transformers_available}")

    def rerank(self, query: str, hits: List[Dict[str, Any]], top_k: int = 5, settings: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Executes the pluggable two-stage rerank pipeline.
        
        Args:
            query (str): The search query text.
            hits (List[Dict]): The candidate retrieved chunks (usually top 20).
            top_k (int): Number of final precise chunks to return (usually top 5).
            settings (Dict): Active configurations.
            
        Returns:
            List[Dict]: High-precision, diverse top-K chunks.
        """
        if not hits:
            return []
        
        if not settings:
            settings = {}

        # 1. Rerank scoring depending on engine selected
        rerank_enabled = str(settings.get("rerank_enabled", "false")).lower() == "true"
        if not rerank_enabled:
            return hits[:top_k]

        engine = str(settings.get("rerank_engine", "local")).lower().strip()
        api_key = settings.get("rerank_api_key", "")
        endpoint = settings.get("rerank_endpoint", "")

        scored_candidates = []

        if engine == "local":
            scored_candidates = self._rerank_local(query, hits)
        elif engine == "cloud_cohere":
            scored_candidates = self._rerank_cohere(query, hits, api_key)
        elif engine == "cloud_custom":
            scored_candidates = self._rerank_custom(query, hits, endpoint, api_key)
        else:
            scored_candidates = self._rerank_local(query, hits)

        # 2. Stage 2: Hybrid A - Structural Code Bias Boost
        boosted_candidates = self._apply_structural_bias(scored_candidates)

        # 3. Stage 3: Hybrid B - Diversity MMR (Maximal Marginal Relevance) Filter
        final_top_k = self._apply_diversity_mmr(boosted_candidates, top_k)

        return final_top_k

    def _rerank_local(self, query: str, hits: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Executes local Cross-Encoder ONNX/BGE, or falls back to robust Jaccard overlap if libraries are missing."""
        # Check if we can run sentence-transformers or ONNX
        if self.sentence_transformers_available:
            try:
                # Dynamic load to save startup speed
                from sentence_transformers import CrossEncoder
                model = CrossEncoder('BAAI/bge-reranker-v2-m3') # Downloads or loads cached weights
                pairs = [[query, h["payload"].get("text", "")] for h in hits]
                scores = model.predict(pairs)
                
                results = []
                for idx, h in enumerate(hits):
                    h_copy = h.copy()
                    h_copy["score"] = float(scores[idx])
                    results.append(h_copy)
                return results
            except Exception as e:
                print(f"[RerankEngine] sentence-transformers failed: {e}. Falling back to Jaccard...")
        
        # Safe, bulletproof fallback: high-precision Jaccard token overlap
        print("[RerankEngine] Using high-precision Jaccard Token Overlap as local offline fallback engine.")
        results = []
        query_words = self._tokenize(query)
        
        for h in hits:
            h_copy = h.copy()
            text = h["payload"].get("text", "")
            text_words = self._tokenize(text)
            
            # Jaccard calculation
            intersection = query_words.intersection(text_words)
            union = query_words.union(text_words)
            jaccard_score = len(intersection) / len(union) if union else 0.0
            
            # Combine original vector search similarity (e.g. 0.0 - 1.0) with lexical overlap
            orig_score = float(h.get("score", 0.0))
            h_copy["score"] = orig_score * 0.4 + jaccard_score * 0.6
            results.append(h_copy)
            
        return results

    def _rerank_cohere(self, query: str, hits: List[Dict[str, Any]], api_key: str) -> List[Dict[str, Any]]:
        """Queries Cohere Rerank v3 API directly over HTTPS."""
        if not api_key:
            print("[RerankEngine] Cohere Rerank requires an API Key. Falling back to local offline.")
            return self._rerank_local(query, hits)

        url = "https://api.cohere.com/v1/rerank"
        documents = [h["payload"].get("text", "") for h in hits]
        
        payload = {
            "model": "rerank-english-v3.0",
            "query": query,
            "documents": documents,
            "top_n": len(hits)
        }
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            req = urllib.request.Request(
                url, 
                data=json.dumps(payload).encode('utf-8'),
                headers=headers,
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=8) as response:
                res_data = json.loads(response.read().decode('utf-8'))
                
                # Parse scores and match back to original hits
                results = [h.copy() for h in hits]
                for item in res_data.get("results", []):
                    idx = int(item["index"])
                    if 0 <= idx < len(results):
                        results[idx]["score"] = float(item["relevance_score"])
                return results
        except Exception as e:
            print(f"[RerankEngine] Cohere Rerank Cloud API failed: {e}. Falling back to local offline.")
            return self._rerank_local(query, hits)

    def _rerank_custom(self, query: str, hits: List[Dict[str, Any]], endpoint: str, api_key: str) -> List[Dict[str, Any]]:
        """Queries custom OpenAPI-compatible Cohere format Rerank endpoint."""
        if not endpoint:
            print("[RerankEngine] Custom Rerank requires a valid Endpoint URL. Falling back to local offline.")
            return self._rerank_local(query, hits)

        documents = [h["payload"].get("text", "") for h in hits]
        payload = {
            "model": "rerank-english-v3.0",
            "query": query,
            "documents": documents,
            "top_n": len(hits)
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
            
        try:
            req = urllib.request.Request(
                endpoint, 
                data=json.dumps(payload).encode('utf-8'),
                headers=headers,
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=8) as response:
                res_data = json.loads(response.read().decode('utf-8'))
                results = [h.copy() for h in hits]
                for item in res_data.get("results", []):
                    idx = int(item["index"])
                    if 0 <= idx < len(results):
                        results[idx]["score"] = float(item["relevance_score"])
                return results
        except Exception as e:
            print(f"[RerankEngine] Custom Cloud Rerank API failed: {e}. Falling back to local offline.")
            return self._rerank_local(query, hits)

    def _apply_structural_bias(self, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Hybrid A: Structural Code Bias.
        Checks for programming language structures and applies a 20% score multiplier (1.2)
        to prioritize core architectural layers over comments or plain text.
        """
        structural_keywords = re.compile(
            r'\b(class|def|interface|function|struct|impl|namespace|import|from|export|package)\b'
        )
        
        boosted = []
        for c in candidates:
            c_copy = c.copy()
            text = c_copy["payload"].get("text", "")
            
            # If chunk declares systems skeleton, boost it!
            if structural_keywords.search(text):
                orig_score = c_copy.get("score", 0.0)
                c_copy["score"] = orig_score * 1.2
                c_copy["structural_boosted"] = True
            else:
                c_copy["structural_boosted"] = False
            boosted.append(c_copy)
            
        return boosted

    def _apply_diversity_mmr(self, candidates: List[Dict[str, Any]], top_k: int) -> List[Dict[str, Any]]:
        """
        Hybrid B: Diversity MMR (Maximal Marginal Relevance).
        Iteratively selects the highest-scoring candidate, then downweights remaining candidates
        if they share high conceptual token overlap (Jaccard similarity > 0.5) with already selected chunks.
        """
        # Sort candidates descending by score
        candidates = sorted(candidates, key=lambda x: x.get("score", 0.0), reverse=True)
        
        selected: List[Dict[str, Any]] = []
        remaining = [c.copy() for c in candidates]
        
        # Tokenize all remaining for fast lookup
        tokenized_remaining = [self._tokenize(c["payload"].get("text", "")) for c in remaining]
        
        while len(selected) < top_k and remaining:
            # Sort remaining on current scores
            paired = list(zip(remaining, tokenized_remaining))
            paired = sorted(paired, key=lambda x: x[0].get("score", 0.0), reverse=True)
            
            # Pop the best candidate
            best_cand, best_tokens = paired.pop(0)
            selected.append(best_cand)
            
            # Rebuild remaining lists
            remaining = [p[0] for p in paired]
            tokenized_remaining = [p[1] for p in paired]
            
            # Apply Jaccard overlap penalty to all remaining candidates based on new selection
            for idx, (cand, tokens) in enumerate(zip(remaining, tokenized_remaining)):
                # Calculate maximum Jaccard overlap with all currently selected
                max_overlap = 0.0
                for sel_cand in selected:
                    sel_tokens = self._tokenize(sel_cand["payload"].get("text", ""))
                    intersection = tokens.intersection(sel_tokens)
                    union = tokens.union(sel_tokens)
                    overlap = len(intersection) / len(union) if union else 0.0
                    max_overlap = max(max_overlap, overlap)
                
                # If similarity overlap is greater than 50%, apply heavy redundancy penalty
                if max_overlap > 0.5:
                    cand["score"] = cand.get("score", 0.0) * 0.5
                    cand["mmr_penalized"] = True
                    
        return selected

    def _tokenize(self, text: str) -> set:
        """Helper to lowercase, remove punctuation, and return unique alphanumeric tokens."""
        clean = re.sub(r'[^\w\s]', ' ', text.lower())
        return set(clean.split())
