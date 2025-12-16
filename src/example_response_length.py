import asyncio
import json
import logging
from dataclasses import dataclass
from pathlib import Path

from safetytooling.utils import utils
from safetytooling.utils.experiment_utils import ExperimentConfigBase
from simple_parsing import ArgumentParser

from src.common.safetytooling_wrappers import ask_single_question

LOGGER = logging.getLogger(__name__)


@dataclass(kw_only=True)
class ResponseLengthConfig(ExperimentConfigBase):
    """Configuration for response length experiment"""

    model_id: str = "gpt-4.1-mini-2025-04-14"
    num_tasks: int = 10
    seed: int = 42
    task_file: str


async def evaluate_response_length(
    task_dict: dict,
    cfg: ResponseLengthConfig,
) -> dict:
    """Evaluate a single task's response length."""
    task_text = task_dict["question"]

    # Have the model complete the task
    completion_response = (
        await ask_single_question(
            cfg.api,
            model_id=cfg.model_id,
            question=task_text,
            temperature=1.0,
            seed=cfg.seed,
        )
    )[0]

    # Calculate response length metrics
    char_length = len(completion_response)
    word_length = len(completion_response.split())

    return {
        "question": task_text,
        "completion": completion_response,
        "response_char_length": char_length,
        "response_word_length": word_length,
    }


async def run_response_length_experiment(config: ResponseLengthConfig) -> None:
    """Run the response length experiment."""
    # Load dataset
    data_file = Path(config.task_file)
    tasks = []
    with open(data_file, "r") as f:
        for i, line in enumerate(f):
            if i >= config.num_tasks:
                break
            tasks.append(json.loads(line))

    LOGGER.info(f"Loaded {len(tasks)} tasks from {data_file}")

    # Process tasks
    results = []
    for task_dict in tasks:
        result = await evaluate_response_length(task_dict, config)
        results.append(result)

    # Save results
    config.output_dir.mkdir(parents=True, exist_ok=True)
    output_file = config.output_dir / f"{config.model_id.replace('/', '_').replace('.', '_')}_length_results.jsonl"

    with open(output_file, "w") as f:
        for result in results:
            f.write(json.dumps(result) + "\n")

    LOGGER.info(f"Results saved to: {output_file}")
    print(f"Results saved to: {output_file}")


async def main():
    """Main entry point."""
    parser = ArgumentParser()
    parser.add_arguments(ResponseLengthConfig, dest="config")
    args = parser.parse_args()
    config = args.config

    # Replace problematic characters in model_id for log file prefix
    log_file_prefix = f"{config.model_id.replace('/', '_').replace('.', '_')}_response_length"
    config.setup_experiment(log_file_prefix=log_file_prefix)

    # Setup environment after logging is configured
    utils.setup_environment()

    # Run the experiment logic
    await run_response_length_experiment(config)


if __name__ == "__main__":
    asyncio.run(main())
