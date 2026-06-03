# Headless Chat & Terminal CLI Engine

This directory implements the interactive command-line interface (CLI) chat loop and credentials management, allowing developers to interact with LLM providers directly from the terminal.

## File Structure
- **`auth.py`**: Handles API key inputs and authentication sessions for CLI clients.
- **`engine.py`**: The execution context running the text-only loop.
- **`models.py`**: Logic for showing and swapping active models in the CLI.
- **`worker.py`**: Orchestrates streaming generation chunks and print formatting.

## Usage
Run the following from the root directory to enter the CLI console:
```bash
python desktop/main.py --cli
```
Note: This module is strictly excluded from remote server deployment environments to keep production hosting packages minimal.
