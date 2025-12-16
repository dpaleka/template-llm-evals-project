**Check the global CLAUDE.md (`~/.claude/CLAUDE.md`) if present for additional instructions.**

# Setup

**IMPORTANT**: Before running any code in this project, follow the instructions in `setup.md` to install `safetytooling` and other dependencies. The `safetytooling` library is a git submodule that must be initialized and installed in editable mode.

# General Project Guidelines
## Key principles
- All core code resides in the src/ directory.
- All data resides in data/.
- All tests reside in the tests/ directory.
- For any complex functionality in src/, implement tests in tests/. Check existing tests to see if it fits in some existing test file, otherwise create a new one. Tests should not be expensive.
- We run everything with `uv run -m ...`. YOU MUST NEVER USE `python -m ...`.
  - If anything is unclear, look up uv documentation at [https://docs.astral.sh/uv/llms.txt](https://docs.astral.sh/uv/llms.txt).
- Prefer iteration and modularization over code duplication.
- Use descriptive variable names with auxiliary verbs (e.g., is_active, has_permission).
- Use lowercase with underscores for directories and files (e.g., routers/user_routes.py).

## Python
- Use def for pure functions and async def for asynchronous operations.
- All functions that have LLM API requests downstream of them should be async.
- Use type hints for all function signatures. We use dict, |, list, tuple, | None instead of typing.Dict, typing.Union, typing.List, typing.Tuple, typing.Optional.
- Prefer Pydantic models over raw dictionaries or dataclasses for input validation, unless the code is already using certain dictionaries or dataclasses.
  - The `dict` method is deprecated; use `model_dump` instead. Deprecated in Pydantic V2.0 to be removed in V3.0.
- Import at the top of the file.
- Avoid unnecessary curly braces in conditional statements.
- For single-line statements in conditionals, omit curly braces.
- Use concise, one-line syntax for simple conditional statements (e.g., if condition: do_something()).
- **IMPORTANT**: We try to avoid using try-except blocks as much as possible, especially when creating data. LET IT FAIL. Silent failure is the worst, and you can assume basically all failures will be silent unless something fails or you yell about it in multiple places. *Do or do not. There is no try.*

## Ruff
- Your code will be Ruff-formatted by a pre-commit hook.
- We don't care about: E501 (line too long), E402 (module level import not at top of file), E741 (ambiguous variable name), F841 (local variable name is assigned to but never used), F403 (import star), F401 (unused import).

## LLM API requests
Always use the wrapper functions in `src/common/safetytooling_wrappers.py`:
```python
from src.common.safetytooling_wrappers import ask_single_question

# Use wrapper instead of direct API calls
response = await ask_single_question(
    api=api,
    model_id="gpt-5-mini-2025-08-07",
    question=question,
    system_prompt=system_prompt
)
```

- We use `InferenceAPI` from `safetytooling.apis` to make requests to LLMs.
- **In scripts using `ExperimentConfigBase`, always use `config.api` to get the API instance** - never call `InferenceAPI()` directly. The config's `.api` property ensures CLI arguments like `--openai_num_threads` are respected.
- For LLM requests, use the wrapper function `ask_single_question` from `common.safetytooling_wrappers` instead of calling `api.ask_single_question` directly.
  - The signature is `async def ask_single_question(api: InferenceAPI, model_id: str, question: str, system_prompt: str | None = None, **api_kwargs,) -> list[str]:`, and the list contains a single response.
  - For requests that run on prompts spanning multiple messages, use `api_call` from `common.safetytooling_wrappers`.
- The LLM query results are automatically cached.
- By default, use `tqdm.gather` without batches around async coroutines that involve making LLM requests.
- Take care and log failed requests, or print them prominently. Do not let failed requests slide silently. Also do not let them crash the script.
- safety-tooling manages internal async parallelization and max-concurrency; the `--*_num_threads` flags only control upstream caller concurrency.

### Model Configuration
- **Default debug model**: `gpt-5-mini-2025-08-07` (for testing if code runs)
  - If LLM cognition required in the test is more demanding, use `gpt-5-2025-08-07` instead
- **Default production models**: `claude-sonnet-4-20250514` or `gpt-5-2025-08-07`
- **Provider prefixes supported**: `openai:model-name`, `anthropic:model-name`, `openrouter:model-name`. In case of no provider prefix, safety-tooling will try to infer a default provider from the model name; this is not robust.
- Any sample commands you write should be for one of the above models. Do not use other models when writing sample commands.
- For non-standard models, it is useful to specify the provider (almost always `openrouter`) when calling scripts, e.g. `--model_id openrouter:deepseek/deepseek-r1-0528`
- **OpenRouter model lookup**: To look up OpenRouter model IDs, call `curl https://openrouter.ai/api/v1/models`. Model ID format examples: `openai/gpt-5`, `anthropic/claude-opus-4.5`. Always use the newest/latest model versions when possible.

### API Parameters to Avoid
- **NEVER set `temperature`** - The safetytooling library handles this. Do not pass temperature to any LLM call, do not add temperature parameters to config classes, do not mention temperature in example commands.
- **NEVER set `max_tokens`** - Let safetytooling use defaults.

### Error Handling
- All LLM API calls should be async with proper error handling
- Failed requests should be logged prominently, not silently ignored
- Processing should continue on individual failures when possible
- Use rate limiting to respect API constraints

## Scripts For Experiments
- We always inherit from the `safetytooling` library's `ExperimentConfigBase` class to configure experiments.
  - You seem to often fail to do this correctly: the correct import is `from safetytooling.utils.experiment_utils import ExperimentConfigBase`.
- Every derived class of `ExperimentConfigBase` should be decorated with `@dataclass(kw_only=True)`. This is to prevent "non-default argument follows default argument" errors.
- We always use ArgumentParser from `simple_parsing` to parse arguments.
- We do everything in JSONL files.
- Some additional common argument patterns:
 - `--num_tasks` is the number of tasks (the size of the prefix of the JSONL file) to use for the experiment.
 - `--num_[sth]` is the number of [sth] to use for the experiment, especially when using subsets of tasks. For example, `--num_pairs 100` with `--num_tasks 50` should pick 100 pairs of tasks out of the first 50 tasks in the JSONL file
 - `--n_repeats` is the number of times to repeat each LLM call (with a different random seed). We usually use `ask_single_question(..., seed=repeat_idx)` for `repeat_idx = 0, 1, ..., n_repeats - 1`.
- If the script is saving results to a file, you MUST *print the filename of the output file to stdout*, along with a very short description of what is being saved.
- When a script produces data that can be visualized and there is a separate plotting/visualization script, the data production script should print out the command to plot at the end.
- In output filenames, normalize names of models and datasets to not use `/` or whitespace; use underscores instead.
- The LLM queries are cached. This means that you do not need to worry about continuing an experiment from where it left off, unless explicitly specified by the user. This also means you do not need to check if the output file already exists.
- Before adding new fields to a config class derived from `ExperimentConfigBase`, check if the desired functionality already exists in an ancestor class. It is more likely to exist for general parameters like `model_id`, `num_tasks`, etc.

## Documentation Requirements
- **CRITICAL**: Every script MUST have example commands in its README that include an example input path or clear description of the input data.
- Example commands must show users exactly what data the script operates on and where it comes from.
- Never use vague descriptions like "loads data" - always specify the exact file/directory structure expected.

## Input Data Policy
- **NEVER use default paths for input data in any script**.
- All input data paths must be explicitly provided via command-line arguments.
- Users must always specify `--dataset_path` or equivalent parameters.
- This ensures clarity about what data is being processed and prevents accidental runs on wrong datasets.

## Logging
- Scripts using ExperimentConfigBase will automatically create a logging file in the `output_dir` directory.
- Every script should have `LOGGER = logging.getLogger(__name__)` after imports. Do not specify any other logger options in the script.
- IMPORTANT: Must call `config.setup_experiment(log_file_prefix="experiment_name")` in main() to enable logging to file.
- Log useful information using `LOGGER.info`. Log suspicious events using `LOGGER.warning`. Log errors using `LOGGER.error`.
- Do not print too many things to stdout unless in debugging mode. Use the library-specific logging functions to log things that are happening in the codebase.

## Dumping data
- The default data dump format for anything over a dataset is JSONL. For example, if you want to dump a dict indexed by an id, use a jsonl where each line is a JSON object, and the first field is `id`.
- The default config dump format is JSON. Dumps should be human-readable, with proper indentation.
- Always round floats to at most 4 decimal places before dumping them in a JSONL file.

## Plots
- Titles and labels are sentence-case.
- Include the model and the relevant config parameters in the plot title. Feel free to add linebreaks in the title if needed.

## Debugging
- We do not use the debugger. We mostly use print statements and iterating.
- When it's not clear why some code is not working, always err on the side of printing very informative stdout so that it is easier to find bugs/issues and debug the code.
- If you find a particular point in code very informative, add `import code; code.interact(local=dict(globals(), **locals()))` there and run the code, or ask the user to run the code and tell you what is happening. This will make you jump into an interactive Python shell where you can inspect variables and run code.
- When printing stuff to stdout, use print(f"{varname=}") to print the variable name and value.
- Do not use fstrings if you're just printing a string without any variables.

- **Background processes**: When testing servers with `&`, always `kill` the actual process PID, not just the shell. Use `ps aux | grep process_name` then `kill <PID>`.

## Testing and Quality

### Running Tests
```bash
# Standard tests
uv run -m pytest tests/ -v -s

# For slow tests (batch API, etc.)
SAFETYTOOLING_SLOW_TESTS=True uv run -m pytest -v -s -n 6
```

### Code Style
- Line length: 120 characters
- Use ruff for linting and formatting
- Type hints required for all functions
- Async functions for any LLM API interactions

### Test Guidelines
- Write tests for new functions. Do not mock things. If you are testing an LLM-based function, use a real datapoint, and call it with an OpenAI model.
- Before importing `safetytooling` in tests, you need to import something from `src` first, so that the `safetytooling` library gets in the $PYTHONPATH. Do this at the top of the test file, for example:
```
from src.common.safetytooling_wrappers import ask_single_question
```
- For tests that rely on InferenceAPI, you need to set up the environment variables for the API keys:
```
from safetytooling.utils import utils
utils.setup_environment()
```
- We run tests as follows:
```
uv run -m pytest tests/[test_file].py -v -s
```
or
```
uv run -m pytest tests/[test_file].py::[test_name] -v -s
```
- When writing a function, first write the tests and confirm they fail, before progressing further.
- Make sure the tests pass before committing. If a particular test is failing, think deeply about whether your implementation is correct or the test is wrong.
- You should never mock things to make the tests pass.

## Tmux Policy
- **ALWAYS run commands where Daniel might want to see output in tmux sessions**
- This includes: training runs, playthroughs, servers, long-running processes, interactive scripts
- **Start the session first, then send keys** - don't pass commands directly to `new-session`
- **ALWAYS source .env first** in new tmux sessions for API keys (TINKER_API_KEY, etc.)
- Use `tmux send-keys` to interact with running sessions
- Example:
  ```bash
  tmux new-session -d -s myrun
  tmux send-keys -t myrun "source .env" Enter
  tmux send-keys -t myrun "uv run -m my_script" Enter
  ```
- This way the shell persists after commands finish, and Daniel can `tmux attach -t myrun` anytime

## Calling Scripts
- Every call to a script has to have `--output_dir` provided as an argument.
- Use `--openai_num_threads 50` for OpenAI models, and `--anthropic/together/openrouter_num_threads 20` for Anthropic/Together/OpenRouter models.
- Even when using non-OpenAI models, use `--openai_num_threads 20` because we use OpenAI's API for parsing and classification glue code.
- Use `--seed 42` to set the random seed.
- To test whether a script works, run it in a single line with all the required arguments.
```
uv run -m src.example_script --input_path data/example_data.jsonl --output_dir data/experiments --model_id gpt-5-mini-2025-08-07 --num_tasks 10 --openai_num_threads 50 --seed 42
```
- When testing scripts, use a smaller `--num_tasks` value, preferably 10.



# Github and git
- You may use the `gh` CLI to interact with Github, for example, to create a new branch and open a PR. The authentication command is `gh auth login --with-token < <(echo $GH_TOKEN)`.
- Use the `gh` CLI for all GitHub interactions (issues, PRs, checks, etc). When given a GitHub URL, use gh commands to fetch the information.
- You can commit. Make sure you add only the files you have changed as part of a coherent change.
- **ALWAYS run `pre-commit run --all-files` before every commit to avoid formatting issues and unstaged changes after commit. Then run `git status` to see what files were modified by the pre-commit hooks and stage those changes.**
- When asked to commit, commit and push.
- When adding changes to commit and push, you should ALWAYS do `git status` first, then add only the files you want to add in this commit.
- **CRITICAL: ONLY create PRIVATE repositories. NEVER create public repos. User will change to public if needed.**

## Pull Request Planning and Documentation
- **CRITICAL**: When working on PRs, create and maintain a `plan.md` file throughout the development process
- This plan should document:
  - Current implementation progress
  - Key decisions and rationale
  - Test results and verification steps
  - Next steps and remaining work
- **At the end of the PR work**, append the content of `plan.md` to the TOP of `research_log.md` with proper formatting
- Follow the format shown in `research_log.md` with clear headers, status indicators (✅/❌), and structured sections
- This creates a persistent record of all research and development work done on each issue

## Git Worktrees
Git worktrees allow working on multiple branches simultaneously without switching between branches:

### Intelligent Worktree Management
Use the provided `claude-worktree.sh` script for streamlined worktree creation:

```bash
# For GitHub issues (auto-generates branch name using Claude)
source claude-worktree.sh 42

# For specific branch names
source claude-worktree.sh feature-branch
```

**Key features:**
- Creates worktrees in parallel directories (e.g., `../project-name-issue-42`)
- Uses Claude to suggest branch names based on GitHub issue titles
- Handles existing local/remote branches intelligently
- Automatically symlinks shared resources (.venv, .cache, .pytest_cache, uv.lock)
- Copies environment files (.env)
- Sets up GitHub authentication if GH_TOKEN is available

### Automated Cleanup
Use `clean-worktrees.sh` to remove worktrees for merged branches:

```bash
./clean-worktrees.sh
```

**Features:**
- Finds branches from merged PRs using GitHub CLI
- Prompts once for "yes to all" removals
- Uses `trash` command for safe file deletion
- Automatically deletes local branches after removing worktrees
- Lists remaining worktrees when complete

### Worktree Best Practices
- **Shared dependencies**: Symlink `.venv` and lock files to avoid duplicate installations
- **Shared caches**: Symlink `.cache`, `.pytest_cache` for performance
- **Environment consistency**: Copy `.env` files to new worktrees
- **Branch naming**: Use descriptive names like `issue-42-fix-auth-bug`
- **Regular cleanup**: Run cleanup script periodically to maintain repository health

### Benefits Over Branch Switching
- No need to stash/unstash work when switching contexts
- Maintain multiple development environments simultaneously
- Avoid rebuilding caches when switching between tasks
- Enable concurrent testing across different feature branches

# Recent command history
- If running on my machine, you will often find my recent command history helpful if you do not know how to run some command.
- You can do e.g. `rg "uv run -m src." ~/.histfile | tail -n 10` to see the ten most recent commands that start with `uv run -m src.`; or search for `./src/scripts/` to see the most recent bash script runs.

# File management and exploration
- ALWAYS use `trash` instead of `rm` unless the user says otherwise.
- Use `rg` to search for files instead of `grep`.
- USE `tree` FREQUENTLY instead of `ls` to remind yourself of the structure of a directory. You only use `ls` in very rare cases.

# Opening webpages
- If the user provides a documentation in text form (e.g. https://docs.astral.sh/uv/llms.txt), open the links, but keep
- You have a Playwright MCP installed. If not, tell the user to install it using `claude mcp add playwright npx '@playwright/mcp@latest`. This can help you open webpages in the browser and see them as the user sees them.


# Local models

## Server Pattern for Heavy Models
For computationally expensive models (e.g., large vision models, embeddings models) that we have to interact with in a customized fashion (not supported by the vllm default used in safety-tooling), we use a server-client pattern:

**Design principles:**
   - Run heavy models in a dedicated server process using Starlette/FastAPI (example: `src/clip_server.py`). The default port is 8080.
   - Keep only the computationally expensive operations in the server (e.g., embedding generation is in the server, but similarity computation is in the client)
   - Implement separate endpoints for different model operations (e.g., `/embed_text`, `/embed_image`)
   - Use async/await with queuing to handle requests efficiently
   - Server: Loads model once, generates embeddings/features. Logs all errors with context for debugging
   - Client: Handles all lightweight operations (similarity computation, ranking, filtering)
   - *Performance considerations:*: - Use dynamic batching (accumulate requests before processing, wait for a few miliseconds or for a batch to be full); batch size is specified when running the server but has a default value; -


# Visualization of results
- The default visualization is just stdout. Use stdout if there are only a few numbers to display.
- Whenever needed (e.g. for a dataset), create nice-looking HTML visualizations after processing data; the default location is `localhost:8765/{visualization_name}.html`. Always allow the user to sort/filter the results by key parameters in the displayed HTML.


# Research principles

**Experiment tracking:** After developing code for an experiment, write a one-sentence explanation of the experiment in the relevant `README.md`, together with the full bash command used to run the experiment. Add what the script expects and what it outputs too.

**Visualize early:** Create simple visualizations of results for every experiment. If you are running something, something needs to be visualized. Think about what the most informative plot/table is and create that.

**Trying out with small models on a small dataset:** Run with the default small models and a very small `num_tasks` (e.g. `--num_tasks 2`) before running a full experiment.

**Systematic exploration:** If asked to analyze results, suggest targeted experiments that would provide the next most valuable bits of information.
