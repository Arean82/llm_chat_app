# Central Headless Core Engine (Backend Server)

This directory houses the core backend logic, AI runtime orchestration, vector database interfaces, and background tasks. It is strictly **UI-agnostic** and contains no desktop UI or web-route definitions.

## Directory Structure
- **`logic/`**: Unified LLM Client router (Google/NVIDIA/OpenAI/Custom), embedding services, database connection adapters (PostgreSQL/Turso), and background chat worker queues.
- **`utils/`**: Shared settings helpers, secure credential resolvers, storage path configurations, and system-wide constants.
- **`workers/`**: Asynchronous task consumers executing vector embeddings, token usage tracking, background log ingestion, and indexing.
- **`resources/`**: Static metadata assets such as the providers schema and model registration manifests.
- **`run_server.py`**: Runs the standalone server routing API (port 5000) for local offline gateways.

## Features
- **Intelligent LLM Router**: Polymorphic interface resolving requests dynamically.
- **Micro-service decoupled RAG**: Caching vectors directly using decoupled embedding utilities.
- **Secure Storage Gateway**: Integrates Turso database bootstrap with dynamic failovers.
