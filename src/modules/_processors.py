import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Callable, Dict, List

from openai import OpenAI

from src._configs import settings
from src.utils.file_util import write_jsonl
from src.utils.logger_util import setup_logger

logger = setup_logger()


def safe_extract(
    llm: OpenAI,
    item: Dict[str, Any],
    func: Callable,
    model_name: str,
    idx: int,
    output_path: Path,
    failed_path: Path,
) -> Dict[str, Any]:
    """
    Wrapper for data_extraction with error handling.
    Each document is processed and written immediately.
    """
    try:
        result = func(
            llm=llm,
            data=item,
            model_name=model_name,
        )
        result["index"] = idx
        write_jsonl(result, output_path)
        return {"index": idx, "status": "success"}

    except Exception as e:
        failed_entry = {
            "index": idx,
            "description": item.get("description", "")[:300],
            "error": str(e),
        }
        write_jsonl(failed_entry, failed_path)
        logger.warning(f"[{idx}] ❌ Extraction failed: {e}")
        return {"index": idx, "status": "failed", "error": str(e)}


def process_all_documents(
    llm: OpenAI,
    dataset: List[Dict[str, Any]],
    func: Callable,
    model_name: str = "gemini-2.5-flash",
    output_file: str = "data_extraction_results.jsonl",
    max_workers: int = settings.MAX_WORKERS,
):
    """
    Run data_extraction() across multiple threads.
    Each item in `dataset` must have a `description` key.
    Results and failures are written incrementally to disk.
    """
    output_path = Path(output_file).resolve()
    failed_path = output_path.with_name("failed_data_extraction.jsonl")

    print(f"Starting multithreaded extraction for {len(dataset)} records...")
    print(f"Output file: {output_path}")

    results, failed = [], []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for i, item in enumerate(dataset, start=1):
            delay = random.uniform(0.05, 0.075)
            futures.append(
                executor.submit(
                    safe_extract,
                    llm,
                    item,
                    func,
                    model_name,
                    i,
                    output_path,
                    failed_path,
                )
            )
            time.sleep(delay)

        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            if result["status"] == "failed":
                failed.append(result)

    logger.info("\n--- Processing Complete ---")
    logger.info(f"✅ Results written to: {output_path}")
    if failed:
        logger.warning(f"⚠️ {len(failed)} failed → {failed_path}")
    else:
        logger.info("✅ All records processed successfully!")

    return {"failed": failed, "output_file": str(output_path)}
