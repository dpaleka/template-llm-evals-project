import hashlib
import json
import os
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any

import aiofiles
import jsonlines
import numpy as np
from pydantic import BaseModel


def round_floats(x, precision: int = 3, convert_ints: bool = False) -> Any:
    if isinstance(x, float):
        return round(x, precision)
    if convert_ints and isinstance(x, int):
        return round(float(x), precision)
    if isinstance(x, dict):
        return {k: round_floats(v, precision, convert_ints) for k, v in x.items()}
    if isinstance(x, tuple):
        return tuple(round_floats(v, precision, convert_ints) for v in x)
    if isinstance(x, list):
        return [round_floats(v, precision, convert_ints) for v in x]
    return x


def stringify_params(*args, **kwargs):
    args_stringified = tuple(json.dumps(arg, sort_keys=True) for arg in args)
    kwargs_stringified = {key: json.dumps(value, sort_keys=True) for key, value in kwargs.items()}
    return (args_stringified, tuple(sorted(kwargs_stringified.items())))


def json_serializable(value):
    try:
        json.dumps(value)
        return True
    except (TypeError, ValueError):
        return False


def make_json_serializable(value):
    if isinstance(value, dict):
        return {k: make_json_serializable(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [make_json_serializable(v) for v in value]
    elif isinstance(value, tuple):
        return tuple(make_json_serializable(v) for v in value)
    elif not json_serializable(value):
        return str(value)
    return value


def hash_params(*args, **kwargs):
    # Copy the arguments so we don't modify them
    args = deepcopy(args)
    kwargs = deepcopy(kwargs)

    # Make all values JSON serializable
    args = tuple(make_json_serializable(arg) for arg in args)
    kwargs = {key: make_json_serializable(value) for key, value in kwargs.items()}

    # Stringify the arguments
    str_args, str_kwargs = stringify_params(*args, **kwargs)
    return hashlib.md5(str(str_args).encode() + str(str_kwargs).encode()).hexdigest()[0:8]


def write_jsonl(path: str, data: list[dict], append: bool = False):
    with jsonlines.open(path, mode="a" if append else "w") as writer:
        for item in data:
            writer.write(item)


def load_jsonl(path: str) -> list[dict]:
    with open(path, "r") as f:
        jsonl_content = f.read()
    return [json.loads(jline) for jline in jsonl_content.splitlines()]


def write_jsonl_from_str(path: str, data: list[str], append: bool = False):
    with open(path, "a" if append else "w") as file:
        for item in data:
            file.write(item + "\n")


async def write_jsonl_async(path: str, data: list[dict], append: bool = True):
    mode = "a" if append else "w"
    async with aiofiles.open(path, mode=mode, encoding="utf-8") as file:
        for item in data:
            json_line = json.dumps(item) + "\n"
            await file.write(json_line)


async def write_jsonl_async_from_str(path: str, data: list[str], append: bool = False):
    mode = "a" if append else "w"
    async with aiofiles.open(path, mode=mode, encoding="utf-8") as file:
        for item in data:
            await file.write(item + "\n")


def shallow_dict(model: BaseModel) -> dict:
    return {
        field_name: (getattr(model, field_name) if isinstance(getattr(model, field_name), BaseModel) else value)
        for field_name, value in model
    }


def update_recursive(source, overrides):
    for key, value in overrides.items():
        if isinstance(value, dict) and key in source and isinstance(source[key], dict):
            update_recursive(source[key], value)
        else:
            source[key] = value
    return source


def normalize_date_format(date: str) -> datetime | None:
    for fmt in (
        "%Y-%m-%d %H:%M:%S",  # 2029-12-31 00:00:00
        "%Y-%m-%dT%H:%M:%S",  # 2029-12-31T00:00:00
        "%Y-%m-%d",  # 2029-12-31
        "%Y-%m-%dT%H:%M:%SZ",  # 2029-12-31T00:00:00Z
        "%d/%m/%Y",  # 31/12/2029
    ):
        try:
            return datetime.strptime(date, fmt)
        except ValueError:
            pass

    print(f"\033[1mWARNING:\033[0m Date format invalid and cannot be normalized: {date=}")
    return None


def ensure_directory_exists(file_path: str):
    """
    Ensure that the directory for the given file path exists.
    If it doesn't exist, create it.

    :param file_path: The path to the file
    """
    directory = os.path.dirname(file_path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)
        print(f"Created directory: {directory}")


def strip_hours(date: datetime | str | None) -> str:
    """
    Strip the hours from a datetime object and return a string in the format YYYY-MM-DD.
    If the date is provided as a string, first convert it to a datetime object.
    """
    if date is None:
        return ""
    if isinstance(date, str):
        date = datetime.fromisoformat(date)
    return date.strftime("%Y-%m-%d")


def compare_dicts(dict1, dict2, path=""):
    differences = []
    for key in set(dict1.keys()) | set(dict2.keys()):
        current_path = f"{path}.{key}" if path else key
        if key not in dict1:
            differences.append(f"Key '{current_path}' missing in first dict")
        elif key not in dict2:
            differences.append(f"Key '{current_path}' missing in second dict")
        elif isinstance(dict1[key], dict) and isinstance(dict2[key], dict):
            differences.extend(compare_dicts(dict1[key], dict2[key], current_path))
        elif dict1[key] != dict2[key]:
            if isinstance(dict1[key], str) and isinstance(dict2[key], str):
                try:
                    date1 = normalize_date_format(dict1[key])
                    date2 = normalize_date_format(dict2[key])
                    if date1 == date2:
                        continue
                except ValueError:
                    pass
            differences.append(f"Mismatch for key '{current_path}':")
            differences.append(f"  First dict:  {dict1[key]}")
            differences.append(f"  Second dict: {dict2[key]}")
    return differences


def recombine_filename(filename: Path, suffix: str) -> Path:
    # Remove the current suffix (if any) and add the new one
    current_suffix = filename.suffix
    return filename.with_name(f"{filename.stem}{suffix}").with_suffix(current_suffix)


def shorten_model_name(model_name: str) -> str:
    if "/" in model_name:
        return model_name.split("/")[-1]
    return model_name


def delist(item):
    if isinstance(item, list):
        return item[0]
    return item


def truncate_str(s: str, max_len: int = 80) -> str:
    pref, suf = int(max_len * 0.75), int(max_len * 0.25)
    if len(s) > max_len:
        return s[:pref] + "..." + s[-suf:]
    else:
        return s


def extract_tag(response: str, tag: str) -> str | None:
    """Extract content between XML-style tags.

    Args:
        response: String containing tagged content
        tag: Tag name to extract content from

    Returns:
        Content between tags if found, None otherwise

    Example:
        >>> extract_tag("<score>30</score> bar 40", "score")
        '30'
        >>> extract_tag("The score is 50", "score")
        None
    """
    assert "<" not in tag, "You probably meant to pass the tag name without angle brackets"
    start_idx = response.find(f"<{tag}>")
    end_idx = response.find(f"</{tag}>")
    if start_idx == -1 or end_idx == -1:
        return None
    start_idx += len(f"<{tag}>")
    return response[start_idx:end_idx].strip()


def extract_tag_onesided(response: str, tag: str) -> str | None:
    """
    Extracts everything in the line after the left tag, even if the right tag is not present.
    """
    tag_pattern = f"<{tag}>"
    start_idx = response.find(tag_pattern)
    if start_idx == -1:
        return None
    # Move start_idx to after the tag
    start_idx += len(tag_pattern)
    end_idx = response.find("\n", start_idx)
    if end_idx == -1:
        end_idx = len(response)
    return response[start_idx:end_idx].strip()


def read_json_or_jsonl(file_path: Path):
    print(f"Reading file: {file_path}")
    if not file_path.exists():
        return []

    if file_path.suffix == ".json":
        with open(file_path, "r") as file:
            return json.load(file)
    elif file_path.suffix == ".jsonl":
        with open(file_path, "r") as file:
            return [json.loads(line) for line in file]
    else:
        raise ValueError("Unsupported file format. Only '.json' and '.jsonl' files are supported.")


def std_dev_binomial(n_successes: int, n_samples: int) -> float:
    """Calculate standard deviation for a binomial proportion.
    where the proportion is very close to 0 or 1.

    Args:
        n_successes: Number of successes
        n_samples: Total number of samples

    Returns:
        Standard deviation of the proportion estimate
    """
    if n_samples <= 0:
        return 0.0
    p = (n_successes + 1) / (n_samples + 2)
    return (p * (1 - p) / n_samples) ** 0.5


def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """Calculate cosine similarity between two vectors.

    Args:
        vec1: First vector
        vec2: Second vector

    Returns:
        Cosine similarity score between 0 and 1
    """
    return float(np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2)))


def insert_after_field(original_dict: dict, target_field: str, new_fields: dict) -> dict:
    """Insert new fields in a dictionary immediately after a specific field.

    Args:
        original_dict: The original dictionary to modify
        target_field: The field after which to insert new fields
        new_fields: Dictionary of new fields to insert

    Returns:
        A new dictionary with fields inserted in the desired position

    Raises:
        ValueError: If the target field is not present in the original dictionary
    """
    if target_field not in original_dict:
        raise ValueError(f"Target field '{target_field}' not found in dictionary")

    # Create a new ordered dictionary
    result = {}

    # Add all items up to and including the target field
    for key, value in original_dict.items():
        result[key] = value
        if key == target_field:
            # Insert the new fields after the target field
            for new_key, new_value in new_fields.items():
                result[new_key] = new_value

    return result
