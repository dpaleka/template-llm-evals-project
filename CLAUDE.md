# Refresh notes
You must maintain a "CLAUDE.md refresh counter" that starts at 10.
Decrement this counter by 1 after each of your responses to me.
At the end of each response, explicitly state "CLAUDE.md refresh counter: [current value]".
When the counter reaches 1, you MUST include the entire contents of CLAUDE.md in your next response to refresh your memory,
and then reset the counter to 10.

# General Project Guidelines
## Key principles
- All core code resides in the src/ directory.
- All data resides in data/.
- All tests reside in the tests/ directory.
- For any complex functionality in src/, implement tests in tests/. Check existing tests to see if it fits in some existing test file, otherwise create a new one. Tests should not be expensive.
- We run everything with `uv run python -m ...`. YOU MUST NEVER USE `python -m ...`.
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

## Ruff
- Your code will be Ruff-formatted by a pre-commit hook.
- We don't care about: E501 (line too long), E402 (module level import not at top of file), E741 (ambiguous variable name), F841 (local variable name is assigned to but never used), F403 (import star).

## LLM API requests
- We use `InferenceAPI` from `safetytooling.apis` to make requests to LLMs.
- For LLM requests, use the wrapper function `ask_single_question` from `common.safetytooling_wrappers` instead of calling `api.ask_single_question` directly.
  - The signature is `async def ask_single_question(api: InferenceAPI, model_id: str, question: str, system_prompt: str | None = None, **api_kwargs,) -> list[str]:`, and the list contains a single response.
  - For requests that run on prompts spanning multiple messages, use `api_call` from `common.safetytooling_wrappers`.
- The LLM query results are automatically cached.
- By default, use `tqdm.gather` without batches around async coroutines that involve making LLM requests.
- Take care and log failed requests, or print them prominently. Do not let failed requests slide silently. Also do not let them crash the script.

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
- In output filenames, normalize names of models and datasets to not use `/` or whitespace; use underscores instead.
- The LLM queries are cached. This means that you do not need to worry about continuing an experiment from where it left off, unless explicitly specified by the user. This also means you do not need to check if the output file already exists.
- Before adding new fields to a config class derived from `ExperimentConfigBase`, check if the desired functionality already exists in an ancestor class. It is more likely to exist for general parameters like `model_id`, `temperature`, `num_tasks`, etc.

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

## Tests
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
uv run python -m pytest tests/[test_file].py -v -s
```
or
```
uv run python -m pytest tests/[test_file].py::[test_name] -v -s
```
- When writing a function, first write the tests and confirm they fail, before progressing further.
- Make sure the tests pass before committing. If a particular test is failing, think deeply about whether your implementation is correct or the test is wrong.
- You should never mock things to make the tests pass.

## Calling Scripts
- Every call to a script has to have `--output_dir` provided as an argument.
- Use `--openai_num_threads 50` for OpenAI models, and `--anthropic/together/openrouter_num_threads 20` for Anthropic/Together/OpenRouter models.
- Even when using non-OpenAI models, use `--openai_num_threads 20` because we use OpenAI's API for parsing and classification glue code.
- Use `--seed 42` to set the random seed.
- To test whether a script works, run it in a single line with all the required arguments.
```
uv run python -m src.example_script --output_dir data/experiments --model_id gpt-4.1-mini-2025-04-14 --temperature 0.0 --num_tasks 10 --openai_num_threads 50 --seed 42
```
- When testing scripts, use a smaller `--num_tasks` value, preferably 10.


## Models
- The default model to debug code (in the sense that "does the code even run?") is `gpt-4.1-mini-2025-04-14`. By default, use this in tests.
  - If the LLM cognition required in the test is more demanding, use `gpt-4.1-2025-04-14` instead.
- The default model to run any experiment where we want to get a sense of what the model is doing is `claude-3-5-sonnet-20240620`.
- Any sample commands you write should be for one of the above models. Do not use other models when writing sample commands.
- Some other models we will be interested in are `claude-3-opus-20240229` and `claude-3-7-sonnet-20250219`.
- For non-standard models, it is useful to specify the provider when calling Python or bash scripts, e.g. ``--model_id together:deepseek-ai/DeepSeek-R1`.

# Github and git
- You may use the `gh` CLI to interact with Github, for example, to create a new branch and open a PR. The authentication command is `gh auth login --with-token < <(echo $GH_TOKEN)`.
- You can commit. Make sure you add only the files you have changed as part of a coherent change. Before adding any files, run `pre-commit run --all-files`.

# Recent command history
- If running on my machine, you will often find my recent command history helpful if you do not know how to run some command.
- You can do e.g. `rg "uv run python -m src." ~/.histfile | tail -n 10` to see the ten most recent commands that start with `uv run python -m src.`; or search for `./src/scripts/` to see the most recent bash script runs.

# File management and exploration
- Use `trash` instead of `rm` unless the user says otherwise.
- Use `rg` to search for files.
- Use `tree` to quickly understand the structure of a directory.


## Research principles

**Experiment tracking:** After developing code for an experiment, write a one-sentence explanation of the experiment in `README.md`, together with the full bash command used to run the experiment.

**Visualize early:** Create simple visualizations of results for every experiment. If you are running something, something needs to be visualized. Think about what the most informative plot/table is and create that.

**Model simplification:** Run with the default small models and a smaller dataset (or smaller `num_tasks`) before running the full experiment.

**Systematic exploration:** If asked to analyze results, suggest targeted experiments that would provide the next most valuable bits of information.