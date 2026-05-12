# logic/rag_manager.py
import re
import math
import numpy as np
from collections import Counter

class RAGManager:
    """
    Lightweight, ultra-fast Vector Retrieval engine.
    Performs overlap chunking and utilizes normalized cosine similarity scoring 
    via optimized NumPy linear algebra. Zero external server dependencies required.
    """
    
    def __init__(self):
        self.chunks = []        # Raw textual slices
        self.vocab = {}         # Map: word -> vector index
        self.idf = []           # Inverse Document Frequency array
        self.tfidf_matrix = None # Sparse-dense optimized lookup matrix
        
    def clear(self):
        """Wipes the current memory matrix to free RAM."""
        self.chunks = []
        self.vocab = {}
        self.idf = []
        self.tfidf_matrix = None

    def _tokenize(self, text: str) -> list:
        """Converts corpus slice into standardized lexeme tokens."""
        return re.findall(r'\w+', text.lower())

    def ingest_document(self, text: str, chunk_size: int = 1000, overlap: int = 200):
        """
        Segments a massive textual body into digestible, semantic overlaps, 
        generates a hyper-dimensional feature space, and fits vectorized matrix.
        """
        if not text or len(text.strip()) < 50:
            return # Ignore insignificant fragments

        # 1. Automated Overlap Chunking
        words = text.split()
        raw_chunks = []
        step = max(1, chunk_size - overlap)
        
        for i in range(0, len(words), step):
            chunk = " ".join(words[i:i + chunk_size])
            if len(chunk.strip()) > 20:
                raw_chunks.append(chunk)
        
        self.chunks = raw_chunks
        num_docs = len(raw_chunks)
        
        if num_docs == 0: return

        # 2. Build High-Dimensional Vocabulary Index
        tokenized_docs = [self._tokenize(c) for c in raw_chunks]
        all_words = set(word for doc in tokenized_docs for word in doc)
        self.vocab = {word: i for i, word in enumerate(sorted(all_words))}
        vocab_size = len(self.vocab)
        
        if vocab_size == 0: return
        
        # 3. Compute Inverse Document Frequency (IDF)
        doc_counts = Counter()
        for doc_tokens in tokenized_docs:
            for token in set(doc_tokens):
                doc_counts[token] += 1
        
        self.idf = np.zeros(vocab_size, dtype=np.float32)
        for word, idx in self.vocab.items():
            # Standard smooth IDF
            self.idf[idx] = math.log((1 + num_docs) / (1 + doc_counts[word])) + 1

        # 4. Generate TF-IDF Search Matrix (NumPy Fast Mode)
        matrix = np.zeros((num_docs, vocab_size), dtype=np.float32)
        for d_idx, doc_tokens in enumerate(tokenized_docs):
            counts = Counter(doc_tokens)
            total_tokens = len(doc_tokens) or 1
            for word, count in counts.items():
                if word in self.vocab:
                    v_idx = self.vocab[word]
                    tf = count / total_tokens
                    matrix[d_idx, v_idx] = tf * self.idf[v_idx]
        
        # L2 Normalize Matrix for instantaneous dot-product cosine similarity
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1.0 # Prevent div-by-zero
        self.tfidf_matrix = matrix / norms

    def search(self, query: str, top_k: int = 5) -> str:
        """
        Performs instant vector projection of the query and calculates 
        Dot-Product angles against the document space to harvest top semantic matches.
        """
        if self.tfidf_matrix is None or not query or not self.vocab:
            return ""
            
        # 1. Project query into existing vector space
        q_tokens = self._tokenize(query)
        q_vec = np.zeros(len(self.vocab), dtype=np.float32)
        q_counts = Counter(q_tokens)
        
        for word, count in q_counts.items():
            if word in self.vocab:
                v_idx = self.vocab[word]
                tf = count / (len(q_tokens) or 1)
                q_vec[v_idx] = tf * self.idf[v_idx]
        
        # Normalize Query
        q_norm = np.linalg.norm(q_vec)
        if q_norm > 0:
            q_vec /= q_norm
            
        # 2. Execute Instant Numpy Linear Algebra Dot Product
        # Resulting shape: (num_docs,) containing values -1.0 to 1.0
        scores = np.dot(self.tfidf_matrix, q_vec)
        
        # 3. Extract Top Semantic Hits
        top_indices = np.argsort(scores)[::-1][:top_k]
        
        # Only return matches with active relevance
        hits = []
        for idx in top_indices:
            if scores[idx] > 0.01: # Relevance threshold gating
                hits.append(self.chunks[idx])
                
        if not hits:
            return ""
            
        # 4. Format grounded output wrapper
        results = ["--- LOCAL VECTOR MEMORY (RAG HITS) ---"]
        for i, content in enumerate(hits, 1):
            results.append(f"--- Segment {i} ---\n{content.strip()}")
            
        return "\n\n".join(results) + "\n\n--- END RAG CONTEXT ---"
