import json
import os
from pathlib import Path
from typing import Any, Dict, List, Union

from src.utils.logger_util import setup_logger

JsonData = Union[Dict[str, Any], List[Any]]
logger = setup_logger()


def write_json(filepath: str, data: JsonData) -> bool:
    """
    Writes data to a specified JSON file path.

    Args:
        filepath: The path to the output JSON file.
        data: The Python data structure (dict or list) to save.

    Returns:
        True if the write was successful, False otherwise.
    """
    try:
        # Open file in write mode ('w'), specifying UTF-8 encoding
        with open(filepath, "w", encoding="utf-8") as f:
            # Use json.dump for writing. indent=4 makes the file human-readable.
            json.dump(data, f, indent=4)
        # logger.info(f"Successfully wrote data to {filepath}")
        return True
    except IOError as e:
        logger.error(f"Error writing to file {filepath}: {e}")
        return False
    except TypeError as e:
        logger.error(
            f"Data type error during serialization: {e}. Check if data is JSON serializable."
        )
        return False


def read_json(filepath: str) -> Union[JsonData, None]:
    """
    Reads and parses data from a specified JSON file path.

    Args:
        filepath: The path to the input JSON file.

    Returns:
        The Python data structure (dict or list) loaded from the file,
        or None if an error occurred.
    """
    if not os.path.exists(filepath):
        logger.error(f"Error: File not found at {filepath}")
        return None

    try:
        # Open file in read mode ('r'), specifying UTF-8 encoding
        with open(filepath, "r", encoding="utf-8") as f:
            # Use json.load to parse the JSON content
            data = json.load(f)
            # logger.info(f"Successfully read data from {filepath}")
            return data
    except json.JSONDecodeError as e:
        logger.error(
            f"Error decoding JSON from {filepath}. File might be empty or corrupted: {e}"
        )
        return None
    except IOError as e:
        logger.error(f"Error reading file {filepath}: {e}")
        return None


def write_jsonl(result: Dict[str, Any], filename: Path):
    """Append a single record to a JSONL file (safe for concurrent writes)."""
    try:
        with open(filename, "a", encoding="utf-8") as f:
            line = json.dumps(result, ensure_ascii=False)
            f.write(line + "\n")
            f.flush()
    except Exception as e:
        logger.error(f"⚠️ Failed to append to {filename.name}: {e}")
