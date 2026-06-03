# Central Headless Core Engine (Backend Server) (v9.0)

This directory houses the core backend logic, AI runtime orchestration, vector database interfaces, and background tasks. It is strictly **UI-agnostic** and contains no desktop UI or web-route definitions.

## Directory Structure
- **`logic/`**: Unified LLM Client router (Google/NVIDIA/OpenAI/Custom), embedding services, database connection adapters (PostgreSQL/Turso), and background chat worker queues.
- **`utils/`**: Shared settings helpers, secure credential resolvers, storage path configurations, and system-wide constants.
- **`workers/`**: Asynchronous task consumers executing vector embeddings, token usage tracking, background log ingestion, and indexing.
- **`resources/`**: Static metadata assets such as the providers schema and model registration manifests.
- **`run_server.py`**: Runs the standalone server routing API (port 5000) for local offline gateways.

## Local Configuration & Packaging Files
To support decoupled modular compilation, this directory contains its own self-contained packaging files:
- **`server.spec`**: PyInstaller spec file specific to packaging the API server.
- **`build.py`**: Local Python build script executing PyInstaller commands targeting `server.spec`. (Global orchestrator is in `scripts/build.py`).
- **`file_version_info.txt`**: OS-level metadata defining the executable's version (v9.0.0.0), copyrights, and descriptions.
- **`installer_script.iss`**: Local Inno Setup configuration to package the compiled server application.

## Features
- **Intelligent LLM Router**: Polymorphic interface resolving requests dynamically.
- **Decoupled RAG**: Caching vectors directly using decoupled embedding utilities.
- **Secure Storage Gateway**: Integrates Turso database bootstrap with dynamic failovers.

## Executable Compilation
To compile the standalone binary `API_Server.exe` using PyInstaller:
```bash
pyinstaller server.spec
```
