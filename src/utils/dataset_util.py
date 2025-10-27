from typing import Dict

from datasets import DatasetDict, load_dataset

from src.utils.file_util import read_json
from src.utils.logger_util import setup_logger

logger = setup_logger()


def load_dataset_from_hf(dataset_name: str) -> DatasetDict:
    try:
        dataset = load_dataset(dataset_name)
        logger.info(f"Successfully loaded dataset {dataset_name}")
        return dataset
    except Exception as e:
        logger.error(f"Failed to load dataset {dataset_name}: {e}")
        raise


def load_dataset_from_json(filepath: str) -> Dict:
    try:
        dataset = read_json(filepath)
        # dataset = load_dataset("json", data_files=str(JSONL_PATH))["train"]

        logger.info(f"Successfully loaded dataset from {filepath}")
        return dataset
    except Exception as e:
        logger.error(f"Failed to load dataset from {filepath}: {e}")
        raise
