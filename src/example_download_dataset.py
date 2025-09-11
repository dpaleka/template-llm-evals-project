import asyncio
import json
import logging
from dataclasses import dataclass
from pathlib import Path

from datasets import load_dataset
from safetytooling.utils import utils
from safetytooling.utils.experiment_utils import ExperimentConfigBase
from simple_parsing import ArgumentParser

LOGGER = logging.getLogger(__name__)


@dataclass(kw_only=True)
class DatasetConfig(ExperimentConfigBase):
    dataset_name: str = "openai/gsm8k"


async def download_dataset(config: DatasetConfig) -> None:
    """Download and save dataset."""
    LOGGER.info(f"Downloading {config.dataset_name} dataset")

    # Download dataset - handle dataset config if needed
    if config.dataset_name == "openai/gsm8k":
        dataset = load_dataset(config.dataset_name, name="main", split="test")
    else:
        dataset = load_dataset(config.dataset_name, split="test")
    filename_base = config.dataset_name.split("/")[-1]

    # Prepare output path
    output_path = Path(config.output_dir) / f"{filename_base}_test.jsonl"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Save as JSONL
    with open(output_path, "w") as f:
        for item in dataset:
            f.write(json.dumps(item) + "\n")

    LOGGER.info(f"Saved {len(dataset)} examples to {output_path}")
    print(f"Dataset saved to: {output_path}")


async def main():
    """Main entry point."""
    parser = ArgumentParser()
    parser.add_arguments(DatasetConfig, dest="config")
    args = parser.parse_args()
    config = args.config

    # Replace slashes in dataset name for log file prefix
    log_file_prefix = config.dataset_name.replace("/", "_") + "_download"
    config.setup_experiment(log_file_prefix=log_file_prefix)

    # Setup environment after logging is configured
    utils.setup_environment()

    # Run the download logic
    await download_dataset(config)


if __name__ == "__main__":
    asyncio.run(main())
