from datasets import DatasetDict, load_dataset
from huggingface_hub import HfApi, HfFolder

from src._configs import settings
from src.utils import load_dataset_from_json, setup_logger

logger = setup_logger()

"""
from datasets import load_dataset, DatasetDict
from huggingface_hub import HfApi, HfFolder
import pandas as pd
from pathlib import Path

# ---------------- CONFIG ----------------
JSONL_PATH = DATA_DIR / "famous_people_wiki_0001.jsonl"  # your JSONL output file
REPO_ID = "8Opt/famous-people-wiki-0001"  # <- change this
SPLIT_RATIO = [0.8, 0.1, 0.1]  # train/val/test

# ---------------- LOAD DATA ----------------
# Hugging Face can directly load JSONL
dataset = load_dataset("json", data_files=str(JSONL_PATH))["train"]
print(f"✅ Loaded {len(dataset)} samples")


# ---------------- CLEAN DATA ----------------
keep_cols = [
    "description",
    "name",
    "occupation",
    "dob",
    "home_place",
    "image_url",
    "profile_url",
    "sunSign",
    "vietnamese",
    "german",
    "french",
    "ner",
]
dataset = dataset.filter(lambda x: all(x.get(c) for c in keep_cols))
print(f"🧹 After cleaning: {len(dataset)} samples")

# ---------------- SPLIT DATA ----------------
# Shuffle before split for randomness
dataset = dataset.shuffle(seed=42)

# 80% train, 10% val, 10% test
train_testvalid = dataset.train_test_split(test_size=0.2, seed=42)
test_valid = train_testvalid["test"].train_test_split(test_size=0.5, seed=42)

dataset_dict = DatasetDict(
    {
        "train": train_testvalid["train"],
        "validation": test_valid["train"],
        "test": test_valid["test"],
    }
)

print(dataset_dict)
print({k: len(v) for k, v in dataset_dict.items()})

# ---------------- PUSH TO HUB ----------------
# Login (if not already)
HfFolder.save_token(HF_TOKEN)
api = HfApi()

# Create dataset repo if not exist
api.create_repo(REPO_ID, repo_type="dataset", exist_ok=True)

# Push all splits at once
dataset_dict.push_to_hub(REPO_ID)
print(f"🚀 Successfully pushed dataset with 80/10/10 split to:")
print(f"🔗 https://huggingface.co/datasets/{REPO_ID}")
"""


class PushToHf:
    def __init__(self):
        self._init_hf()

    def _init_hf(self):
        try:
            HfFolder.save_token(settings.HF_TOKEN)
            self.hf_api = HfApi()
        except Exception as e:
            logger.error(f"Failed to initialize Hugging Face: {e}")
            raise e

    def _load_dataset(self, dataset_path: str):
        try:
            dataset = load_dataset("json", data_files=str(dataset_path))["train"]
            # dataset = load_dataset_from_json(dataset_path)
            return dataset
        except Exception as e:
            logger.error(f"Failed to load dataset: {e}")
            raise e

    def _push_to_hub(
        self,
        dataset: DatasetDict,
        dataset_name: str,
        split_ratio: List[float] = [0.8, 0.1, 0.1],  # train/val/test
        keep_cols: List[str] = [
            "description",
            "name",
            "occupation",
            "dob",
            "home_place",
            "image_url",
            "profile_url",
            "sunSign",
            "vietnamese",
            "german",
            "french",
            "ner",
        ],
    ):
        try:
            dataset = load_dataset("json", data_files=str(dataset_path))["train"]
            logger.info(f"✅ Loaded {len(dataset)} samples")

            # ---------------- CLEAN DATA ----------------
            if keep_cols:
                dataset = dataset.filter(lambda x: all(x.get(c) for c in keep_cols))
                logger.info(f"🧹 After cleaning: {len(dataset)} samples")

            # ---------------- SPLIT DATA ----------------
            # Shuffle before split for randomness
            dataset = dataset.shuffle(seed=42)

            # 80% train, 10% val, 10% test
            train_testvalid = dataset.train_test_split(
                test_size=split_ratio[0], seed=42
            )
            test_valid = train_testvalid["test"].train_test_split(
                test_size=split_ratio[1], seed=42
            )

            dataset_dict = DatasetDict(
                {
                    "train": train_testvalid["train"],
                    "validation": test_valid["train"],
                    "test": test_valid["test"],
                }
            )

            logger.info(dataset_dict)
            logger.info({k: len(v) for k, v in dataset_dict.items()})
            repo_id = settings.HF_REPO_ID + "/" + dataset_name
            dataset.push_to_hub(repo_id)
            logger.info(f"🚀 Successfully pushed dataset to {repo_id}")
        except Exception as e:
            logger.exception(f"Failed to push dataset to Hugging Face: {e}")
            raise e
