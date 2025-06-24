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