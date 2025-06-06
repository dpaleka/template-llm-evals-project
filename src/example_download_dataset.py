import asyncio
import json
import logging
from dataclasses import dataclass
from pathlib import Path

from datasets import load_dataset
from safetytooling.utils.experiment_utils import ExperimentConfigBase
from simple_parsing import ArgumentParser

LOGGER = logging.getLogger(__name__)


@dataclass(kw_only=True)
class DatasetConfig(ExperimentConfigBase):
    dataset_name: str = "openai/gsm8k"


async def main(cfg: DatasetConfig) -> None:
    """Download and save GSM8K test dataset."""
    LOGGER.info(f"Downloading {cfg.dataset_name} dataset")

    # Download GSM8K test split
    dataset = load_dataset(cfg.dataset_name, split="test")
    filename_base = cfg.dataset_name.split("/")[-1]

    # Prepare output path
    output_path = Path(cfg.output_dir) / f"{filename_base}_test.jsonl"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Save as JSONL
    with open(output_path, "w") as f:
        for item in dataset:
            f.write(json.dumps(item) + "\n")

    LOGGER.info(f"Saved {len(dataset)} examples to {output_path}")
    print(f"Dataset saved to: {output_path}")


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_arguments(DatasetConfig, dest="config")
    args = parser.parse_args()
    cfg: DatasetConfig = args.config

    cfg.setup_experiment(log_file_prefix=f"{cfg.dataset_name}_download")
    asyncio.run(main(cfg))
