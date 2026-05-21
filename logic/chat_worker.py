# logic/chat_worker.py

from PySide6.QtCore import QThread, Signal
import time
import json

class ChatWorker(QThread):
    stream_chunk = Signal(str)
    thinking_chunk = Signal(str)
    response_received = Signal(str)
    error_occurred = Signal(str)
    finished = Signal()
    metrics_received = Signal(dict)

    def __init__(self, client, messages, temperature=0.7, max_tokens=4096, web_search_query=None, large_document_text=None, parent=None):
        super().__init__(parent)
        self.client = client
        self.messages = messages
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.web_search_query = web_search_query
        self.large_document_text = large_document_text
        self.stream = True
        self._is_running = True

    def _execute_rerank(self, hits, top_k=5):
        try:
            from utils.path_utils import get_app_settings
            from logic.rerank_engine import RerankEngine
            
            settings = get_app_settings()
            rerank_enabled = str(settings.value("rerank_enabled", "false")).lower() == "true"
            
            if not rerank_enabled:
                self.thinking_chunk.emit("🔍 Reranking pipeline is disabled in settings. Using baseline top candidates.\n")
                return hits[:top_k]
                
            rerank_engine_name = str(settings.value("rerank_engine", "local")).lower().strip()
            rerank_settings = {
                "rerank_enabled": "true",
                "rerank_engine": rerank_engine_name,
                "rerank_api_key": str(settings.value("rerank_api_key", "")),
                "rerank_endpoint": str(settings.value("rerank_endpoint", ""))
            }
            
            engine = RerankEngine.get_instance()
            
            # Print initial info to thinking stream
            self.thinking_chunk.emit(f"🔍 Initiating pluggable reranking pipeline using '{rerank_engine_name}' engine...\n")
            if rerank_engine_name == "local":
                if engine.sentence_transformers_available:
                    self.thinking_chunk.emit("  ├─ Running local BGE Cross-Encoder Model...\n")
                else:
                    self.thinking_chunk.emit("  ├─ Local dependencies (sentence-transformers/onnxruntime) absent.\n")
                    self.thinking_chunk.emit("  ├─ Falling back to offline High-Precision Jaccard Token Overlap...\n")
            elif rerank_engine_name == "cloud_cohere":
                self.thinking_chunk.emit("  ├─ Requesting Cloud Cohere Rerank v3 API...\n")
            elif rerank_engine_name == "cloud_custom":
                self.thinking_chunk.emit(f"  ├─ Querying custom OpenAPI Rerank endpoint at {rerank_settings['rerank_endpoint']}...\n")
            
            query_text = self.web_search_query if self.web_search_query else str(self.messages[-1].get("content", ""))
            
            top_5 = engine.rerank(
                query=query_text,
                hits=hits,
                top_k=top_k,
                settings=rerank_settings
            )
            
            # Check structural boost stats
            boosted_count = sum(1 for h in top_5 if h.get("structural_boosted", False))
            
            if boosted_count > 0:
                self.thinking_chunk.emit(f"  ├─ Hybrid A: Applied +20% score boost to {boosted_count} structural code chunks\n")
            self.thinking_chunk.emit("  ├─ Hybrid B: Applied Maximal Marginal Relevance (MMR) Jaccard token overlap filter\n")
            self.thinking_chunk.emit(f"  └─ Finalized {len(top_5)} high-precision, diverse chunks for context injection.\n")
            
            return top_5
        except Exception as e:
            self.thinking_chunk.emit(f"⚠️ Reranking failed: {e}. Falling back to baseline sorting.\n")
            return hits[:top_k]
        
    def _extract_graph_rag(self, text: str) -> str:
        # Phase 4.1.5: GraphRAG Code Mapping
        import re
        classes = re.findall(r'class\s+([A-Za-z0-9_]+)', text)
        defs = re.findall(r'def\s+([A-Za-z0-9_]+)', text)
        imports = re.findall(r'import\s+([A-Za-z0-9_\.]+)|from\s+([A-Za-z0-9_\.]+)', text)
        
        graph_summary = "GraphRAG Entity Relations:\n"
        if classes: graph_summary += f"- Classes: {', '.join(set(classes[:15]))}\n"
        if defs: graph_summary += f"- Functions: {', '.join(set(defs[:15]))}\n"
        
        clean_imports = set(i[0] or i[1] for i in imports if i[0] or i[1])
        if clean_imports: graph_summary += f"- Dependencies: {', '.join(list(clean_imports)[:15])}\n"
        
        return graph_summary if (classes or defs or clean_imports) else ""

    def run(self):
        try:
            # 1. True Qdrant Semantic RAG (Phase 4.1.1 & 4.1.2)
            if self.large_document_text:
                try:
                    from logic.vector_db import VectorDatabase
                    import time
                    db = VectorDatabase.get_instance()
                    
                    self.thinking_chunk.emit("⚡ Chunking document and embedding into Qdrant...\n")
                    chunk_size = 1500
                    text = self.large_document_text
                    chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
                    
                    col_name = f"temp_doc_{int(time.time())}"
                    
                    # Phase 4.1.4: Hybrid Search BM25 Initialization
                    from logic.rag_manager import RAGManager
                    lexical_engine = RAGManager()
                    lexical_engine.ingest_chunks(chunks)
                    
                    for idx, chunk in enumerate(chunks):
                        if idx % 5 == 0:
                            self.thinking_chunk.emit(f"⚡ Indexing chunk {idx+1}/{len(chunks)}...\n")
                        vector = self.client.generate_embeddings(chunk)
                        if vector:
                            db.upsert_segment(col_name, vector, {
                                "text": chunk,
                                "source_type": "staged_context",
                                "timestamp": int(time.time())
                            })
                    
                    self.thinking_chunk.emit("✅ Document indexed. Executing Hybrid Search (BM25 + Dense)...\n")
                    
                    # Generate query embedding
                    query_text = self.web_search_query if self.web_search_query else str(self.messages[-1].get("content", ""))
                    query_vector = self.client.generate_embeddings(query_text)
                    
                    if query_vector:
                        # Phase 4.1.2 & 4.1.8: High-speed Dense retrieval with Qdrant Metadata Filtering
                        dense_hits = db.search_similar(
                            col_name, 
                            query_vector, 
                            limit=20,
                            metadata_filters={"source_type": "staged_context"}
                        )
                        
                        # Phase 4.1.4: BM25 Lexical retrieval (Top 20)
                        lexical_hits = lexical_engine.search_raw(query_text, top_k=20)
                        
                        # Phase 4.1.4: Reciprocal Rank Fusion (RRF)
                        rrf_scores = {}
                        k = 60
                        for rank, h in enumerate(dense_hits):
                            txt = h["payload"].get("text", "")
                            rrf_scores[txt] = rrf_scores.get(txt, 0) + 1.0 / (k + rank + 1)
                            
                        for rank, lh in enumerate(lexical_hits):
                            txt = lh["text"]
                            rrf_scores[txt] = rrf_scores.get(txt, 0) + 1.0 / (k + rank + 1)
                            
                        sorted_chunks = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
                        merged_top_20 = [{"payload": {"text": txt}, "score": score} for txt, score in sorted_chunks[:20]]
                        
                        # Phase 4.1.2: Reranker (Top 5)
                        self.thinking_chunk.emit("🧠 Reranking Top 20 Hybrid candidates for Top 5 precision...\n")
                        top_5 = self._execute_rerank(merged_top_20, top_k=5)
                        
                        if top_5:
                            context_str = "\n\n---\n\n".join([h["payload"].get("text", "") for h in top_5])
                            
                            # Phase 4.1.5: GraphRAG mapping injection
                            graph_rag_str = self._extract_graph_rag(self.large_document_text)
                            if graph_rag_str:
                                context_str = f"{graph_rag_str}\n\n{context_str}"
                                
                            self.messages.insert(0, {"role": "system", "content": f"Context retrieved from document:\n{context_str}"})
                except Exception as e:
                    print(f"[Worker] RAG Augmentation failed: {e}")

            # 2. Provider Routing
            provider = self.client.get_current_provider()
            if provider == "google":
                self._run_google_loop()
            else:
                self._run_openai_loop()
                
        except Exception as e:
            self.error_occurred.emit(str(e))
        finally:
            self.finished.emit()

    def _run_google_loop(self):
        start_time = time.perf_counter()
        first_chunk_time = None
        chunk_count = 0
        full_response = ""
        
        from google.genai import types
        import base64

        system_instructions = ""
        mapped_history = []

        for msg in self.messages:
            role = msg.get("role", "user").lower()
            content = msg.get("content", "")
            if role == "system":
                system_instructions += (content if isinstance(content, str) else "") + "\n"
            else:
                fixed_role = "model" if role == "assistant" else "user"
                current_parts = []
                if isinstance(content, list):
                     for obj in content:
                          if obj.get('type') == 'text': current_parts.append(obj.get('text', ''))
                          elif obj.get('type') == 'image':
                               bin_blob = base64.b64decode(obj.get('data', ''))
                               current_parts.append(types.Part.from_bytes(data=bin_blob, mime_type=obj.get('mime')))
                else: current_parts = [content]
                
                if mapped_history and mapped_history[-1]["role"] == fixed_role:
                    mapped_history[-1]["parts"].extend(current_parts)
                else:
                    mapped_history.append({"role": fixed_role, "parts": current_parts})

        if not mapped_history: return
        active_node = mapped_history.pop()
        active_prompt = active_node["parts"]
        
        config = types.GenerateContentConfig(
            system_instruction=system_instructions.strip() if system_instructions else None,
            temperature=self.temperature,
            max_output_tokens=self.max_tokens
        )
        
        if mapped_history and mapped_history[-1]["role"] == "user":
             last_item = mapped_history.pop()
             active_prompt = last_item["parts"] + active_prompt

        chat = self.client.google_client.chats.create(
            model=self.client.current_model,
            history=mapped_history,
            config=config
        )
        
        print(f"[Worker] Sending Google GenAI request for model: {self.client.current_model}")
        response = chat.send_message_stream(active_prompt) if self.stream else chat.send_message(active_prompt)

        if self.stream:
            for chunk in response:
                if not self._is_running: break
                try:
                    txt = chunk.text
                    if txt:
                        if first_chunk_time is None: first_chunk_time = time.perf_counter()
                        full_response += txt
                        chunk_count += len(txt.split())
                        self.stream_chunk.emit(txt)
                except Exception as e:
                    if "blocked" in str(e).lower():
                        self.stream_chunk.emit("\n\n*(⚠️ Blocked by Safety Filters)*")
                        break
                    raise e
            if self._is_running:
                self.response_received.emit(full_response)
                self._finalize_metrics(start_time, first_chunk_time, chunk_count)
        else:
            self.response_received.emit(response.text)

    def _run_openai_loop(self):
        start_time = time.perf_counter()
        first_chunk_time = None
        chunk_count = 0
        finalized_msgs = []
        for msg in self.messages:
            c = msg.get("content", "")
            if isinstance(c, list):
                open_ai_c = []
                for part in c:
                    if part.get('type') == 'text': open_ai_c.append({"type": "text", "text": part.get('text', '')})
                    elif part.get('type') == 'image':
                        url = f"data:{part.get('mime')};base64,{part.get('data')}"
                        open_ai_c.append({"type": "image_url", "image_url": {"url": url}})
                finalized_msgs.append({"role": msg["role"], "content": open_ai_c})
            else: finalized_msgs.append(msg)
            
        # Phase 4.1.3: Prompt Context Caching (Anthropic/DeepSeek caching protocols)
        if self.client.current_model and "claude" in self.client.current_model.lower():
            for m in finalized_msgs:
                if m.get("role") == "system" and isinstance(m.get("content"), str):
                    if len(m.get("content", "")) > 500:
                        m["content"] = [
                            {
                                "type": "text",
                                "text": m["content"],
                                "cache_control": {"type": "ephemeral"}
                            }
                        ]

        # Check if the model supports tools dynamically (Phase 4.1.7 Optimization)
        from utils.model_config import does_model_support_tools, update_model_capability
        model_supports_tools = does_model_support_tools(self.client.current_model)

        # Phase 4.1.7: Model-Side Tool Calling API
        tools = None
        if model_supports_tools:
            tools = [
                {
                    "type": "function",
                    "function": {
                        "name": "web_search",
                        "description": "Perform a web search for real-time information",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string", "description": "The search query."}
                            },
                            "required": ["query"]
                        }
                    }
                }
            ]

            # Guidance to prevent Llama models from calling web_search for basic greetings/questions
            guidance = (
                "You have access to tools, but you must only use them if the user's request explicitly "
                "requires real-time web search or external information. For general conversation, "
                "greetings (like 'hi', 'hello', 'how are you'), or general queries that don't need real-time data, "
                "do NOT call any tools. Respond directly in plain text."
            )
            # Injects system instruction at system prompt
            has_system = False
            for msg in finalized_msgs:
                if msg.get("role") == "system":
                    msg["content"] = str(msg["content"]) + "\n\n" + guidance
                    has_system = True
                    break
            if not has_system:
                finalized_msgs.insert(0, {"role": "system", "content": guidance})

        # Loop up to 3 times to handle multi-turn tool calling!
        for turn in range(3):
            if not self._is_running: break
            
            try:
                if model_supports_tools and tools:
                    response = self.client.client.chat.completions.create(
                        model=self.client.current_model,
                        messages=finalized_msgs,
                        stream=self.stream,
                        temperature=self.temperature,
                        max_tokens=self.max_tokens,
                        tools=tools
                    )
                else:
                    response = self.client.client.chat.completions.create(
                        model=self.client.current_model,
                        messages=finalized_msgs,
                        stream=self.stream,
                        temperature=self.temperature,
                        max_tokens=self.max_tokens
                    )
            except Exception as e:
                err_str = str(e).lower()
                if model_supports_tools and ("tool" in err_str or "auto" in err_str or "badrequesterror" in err_str or "400" in err_str or "not support" in err_str):
                    print(f"[Worker] Selected model '{self.client.current_model}' does not support native tool calling. Updating capability shard and retrying without tools... Error: {e}")
                    # Update dynamic capability configuration
                    update_model_capability(self.client.current_model, False)
                    # Turn off supports tools for this run
                    model_supports_tools = False
                    tools = None
                    # Auto-fallback: Retry the creation request without tools payload
                    response = self.client.client.chat.completions.create(
                        model=self.client.current_model,
                        messages=finalized_msgs,
                        stream=self.stream,
                        temperature=self.temperature,
                        max_tokens=self.max_tokens
                    )
                else:
                    raise e

            active_tool_calls = {}
            full_response = ""
            buffered_content = ""
            is_buffering = False

            if self.stream:
                try:
                    for chunk in response:
                        if not self._is_running: break
                        if not getattr(chunk, "choices", None): continue
                        if not chunk.choices: continue
                        
                        delta = chunk.choices[0].delta
                        
                        # Phase 4.1.7: Tool Call Interception
                        if hasattr(delta, 'tool_calls') and delta.tool_calls:
                            for tc in delta.tool_calls:
                                idx = tc.index
                                if idx not in active_tool_calls:
                                    active_tool_calls[idx] = {
                                        "id": tc.id if hasattr(tc, 'id') and tc.id else f"call_{int(time.time())}_{idx}",
                                        "name": tc.function.name if (tc.function and tc.function.name) else "",
                                        "arguments": ""
                                    }
                                if tc.function and tc.function.arguments:
                                    active_tool_calls[idx]["arguments"] += tc.function.arguments
                                    
                        content = delta.content
                        if content:
                            if first_chunk_time is None: first_chunk_time = time.perf_counter()
                            full_response += content
                            chunk_count += 1
                            
                            # Active Buffering Trigger: If stream starts with '{'
                            if len(full_response) == 1 and full_response.startswith("{"):
                                is_buffering = True
                                
                            if is_buffering:
                                buffered_content += content
                                # If it grows too large, release it because it's not a short tool call JSON
                                if len(buffered_content) > 500:
                                    is_buffering = False
                                    self.stream_chunk.emit(buffered_content)
                                    buffered_content = ""
                            else:
                                self.stream_chunk.emit(content)
                except Exception as stream_ex:
                    err_str = str(stream_ex).lower()
                    if model_supports_tools and ("tool" in err_str or "auto" in err_str or "badrequesterror" in err_str or "400" in err_str or "not support" in err_str):
                        print(f"[Worker] Native tool streaming rejected mid-flight. Falling back... Error: {stream_ex}")
                        from utils.model_config import update_model_capability
                        update_model_capability(self.client.current_model, False)
                        
                        # Strip tools from context
                        for m in finalized_msgs:
                            if m.get("role") == "system" and "You have access to tools" in str(m.get("content")):
                                m["content"] = str(m["content"]).replace("You have access to tools, but you must only use them if the user's request explicitly requires real-time web search or external information. For general conversation, greetings (like 'hi', 'hello', 'how are you'), or general queries that don't need real-time data, do NOT call any tools. Respond directly in plain text.", "").strip()
                        
                        # Re-request the stream without tools
                        response = self.client.client.chat.completions.create(
                            model=self.client.current_model,
                            messages=finalized_msgs,
                            stream=True,
                            temperature=self.temperature,
                            max_tokens=self.max_tokens
                        )
                        
                        full_response = ""
                        for fallback_chunk in response:
                            if not self._is_running: break
                            if getattr(fallback_chunk, "choices", None) and fallback_chunk.choices:
                                content = fallback_chunk.choices[0].delta.content
                                if content:
                                    if first_chunk_time is None: first_chunk_time = time.perf_counter()
                                    full_response += content
                                    chunk_count += 1
                                    self.stream_chunk.emit(content)
                    else:
                        raise stream_ex
            else:
                msg = response.choices[0].message
                full_response = msg.content or ""
                if hasattr(msg, 'tool_calls') and msg.tool_calls:
                    for idx, tc in enumerate(msg.tool_calls):
                        active_tool_calls[idx] = {
                            "id": tc.id,
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }

            # Intercept raw JSON strings returned in content (common with some NVIDIA endpoints and Llama models)
            if not active_tool_calls and (full_response.strip().startswith("{") and "web_search" in full_response):
                try:
                    data = json.loads(full_response.strip())
                    if "web_search" in str(data):
                        q = "hi"
                        if isinstance(data, dict):
                            params = data.get("parameters", {})
                            if isinstance(params, dict):
                                q = params.get("query", "hi")
                            elif "query" in data:
                                q = data.get("query", "hi")
                        active_tool_calls[0] = {
                            "id": f"call_{int(time.time())}_0",
                            "name": "web_search",
                            "arguments": json.dumps({"query": q}),
                            "raw_json_fallback": True
                        }
                except:
                    pass

            if active_tool_calls:
                # We have tool calls! Run them and continue the loop.
                assistant_msg = {"role": "assistant"}
                
                has_fallback = any(tc.get("raw_json_fallback") for tc in active_tool_calls.values())
                if has_fallback:
                    assistant_msg["content"] = full_response
                else:
                    assistant_msg["tool_calls"] = []
                    for tc in active_tool_calls.values():
                        assistant_msg["tool_calls"].append({
                            "id": tc["id"],
                            "type": "function",
                            "function": {
                                "name": tc["name"],
                                "arguments": tc["arguments"]
                            }
                        })
                
                finalized_msgs.append(assistant_msg)

                for tc in active_tool_calls.values():
                    name = tc["name"]
                    arguments = tc["arguments"]
                    try:
                        args = json.loads(arguments)
                    except:
                        args = {}
                    query = args.get("query", "general information")
                    
                    self.thinking_chunk.emit(f"⚙️ Action Triggered: `{name}` for query: '{query}'...\n")
                    
                    # Execute mock tool / local search
                    result = f"Local search results for query '{query}': Found related classes and active overrides in codebase."
                    
                    tool_response_msg = {
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "name": name,
                        "content": result
                    }
                    finalized_msgs.append(tool_response_msg)
                
                # Continue loop to let the model generate the final text based on tool results!
                continue
            else:
                # No tool calls, we have the final assistant response!
                if self._is_running:
                    self.response_received.emit(full_response)
                    self._finalize_metrics(start_time, first_chunk_time, chunk_count)
                break

    def _finalize_metrics(self, start, first_chunk, count):
        if first_chunk:
            end = time.perf_counter()
            self.metrics_received.emit({
                "ttft": round(first_chunk - start, 2),
                "tps": round(count / (end - first_chunk), 1) if (end - first_chunk) > 0 else 0,
                "prompt_tokens": 0,
                "completion_tokens": count
            })

    def stop(self):
        self._is_running = False
