# Setup Instructions

## Installing safetytooling

To use the safetytooling library in this project, clone it and install in editable mode:

```bash
git submodule update --init --recursive
#git clone https://github.com/safety-research/safety-tooling.git # deprecated in favor of submodule

uv venv --python 3.12
source .venv/bin/activate
cd safety-tooling
uv pip install -e .
uv pip install -r requirements_dev.txt
deactivate
```

## Installing Optional Dependencies

The project has optional machine learning dependencies (torch, transformers, opencv-python) that can be installed when needed:

```bash
uv pip install -e ".[ml]"
```

## Project Structure

- `src/` - All core code
- `data/` - All data files
- `tests/` - All tests
- `src/common/safetytooling_wrappers.py` - Wrapper functions for safetytooling APIs

## Running Scripts

Always use `uv run -m ...` instead of `python -m ...` when running scripts.

Example:
```bash
uv run -m src.example_download_dataset --dataset_name openai/gsm8k --output_dir data/
```

```bash
uv run -m src.example_response_length --task_file data/gsm8k_test.jsonl --output_dir data/experiments --model_id gpt-4.1-mini-2025-04-14 --num_tasks 10 --seed 42
```

## Running servers

Example:
```bash
uv run -m src.clip_server
```

The server will start on `http://localhost:8080` and load the LAION CLIP-ViT-B-32-laion2B-s34B-b79K model.

**Batching Options:**
- `--max-batch-size 8`: Maximum batch size for processing (default: 8)
- `--batch-timeout-ms 2`: Batch timeout in milliseconds (default: 2)
- `--host 0.0.0.0`: Host to bind to
- `--port 8080`: Port to bind to

Example with custom batching:
```bash
uv run -m src.clip_server --max-batch-size 16 --batch-timeout-ms 5
```