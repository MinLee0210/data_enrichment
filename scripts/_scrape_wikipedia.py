"""
NOTE: Not scrape well.
Wikipedia Scraper for Famous People

This script scrapes Wikipedia for famous people's names and images.
It saves the data in a structured format for further processing.
"""

import os
import json
import time
import random
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import wikipediaapi
from tqdm import tqdm
from urllib.parse import unquote
from dotenv import load_dotenv

load_dotenv()

# Configure logging
import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Project directories
PROJECT_DIR = Path(__file__).parent.parent
DATA_DIR = PROJECT_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
WIKIPEDIA_DIR = RAW_DATA_DIR / "wikipedia_famous_people"
WIKIPEDIA_DIR.mkdir(parents=True, exist_ok=True)

# Constants
WIKI_USER_AGENT = f"DataEnrichmentBot/1.0 ({os.getenv('EMAIL')})"
WIKIPEDIA_CATEGORIES = [
    "Living_people",
    "Actors",
    "Singers",
    "Scientists",
    "Politicians",
    "Writers",
    "Athletes",
    "Businesspeople",
    "Artists",
    "Musicians",
]
MAX_PEOPLE_PER_CATEGORY = 2000
REQUEST_DELAY = 1  # seconds between requests to be nice to Wikipedia's servers


def setup_wikipedia_api() -> wikipediaapi.Wikipedia:
    """Initialize and return Wikipedia API client."""
    return wikipediaapi.Wikipedia(
        language="en",
        user_agent=WIKI_USER_AGENT,
        extract_format=wikipediaapi.ExtractFormat.WIKI,
    )


def get_category_members(
    category_name: str, wiki: wikipediaapi.Wikipedia
) -> List[Dict]:
    """Get all members of a Wikipedia category."""
    category = wiki.page(f"Category:{category_name}")
    if not category.exists():
        logger.warning(f"Category '{category_name}' does not exist.")
        return []

    members = []
    for member in category.categorymembers.values():
        if member.ns == wikipediaapi.Namespace.CATEGORY:
            # Skip subcategories for now to avoid too many requests
            continue
        members.append(
            {"title": member.title, "url": member.fullurl, "pageid": member.pageid}
        )
        if len(members) >= MAX_PEOPLE_PER_CATEGORY:
            break

    return members


def get_person_info(page_title: str, wiki: wikipediaapi.Wikipedia) -> Optional[Dict]:
    """Extract information about a person from their Wikipedia page."""
    try:
        page = wiki.page(page_title)
        if not page.exists():
            return None

        # Get the first image on the page
        image_url = None
        if hasattr(page, "images"):
            for img in page.images.values():
                if img.url and img.url.lower().endswith((".jpg", ".jpeg", ".png")):
                    image_url = img.url
                    break

        return {
            "name": page.title,
            "url": page.fullurl,
            "summary": page.summary[:500] if page.summary else "",
            "image_url": image_url,
            "categories": [
                cat[9:] for cat in page.categories.keys() if "Category:" in cat
            ],
            "timestamp": datetime.now(datetime.timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"Error processing {page_title}: {str(e)}")
        return None


def download_image(image_url: str, output_dir: Path) -> Optional[str]:
    """Download an image from a URL and save it locally."""
    if not image_url:
        return None

    try:
        # Get the filename from the URL
        filename = unquote(image_url.split("/")[-1])
        # Sanitize filename
        filename = "".join(c if c.isalnum() or c in "._- " else "_" for c in filename)
        filepath = output_dir / filename

        # Skip if file already exists
        if filepath.exists():
            return str(filepath.relative_to(PROJECT_DIR))

        # Download the image
        response = requests.get(image_url, stream=True)
        response.raise_for_status()

        with open(filepath, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        return str(filepath.relative_to(PROJECT_DIR))
    except Exception as e:
        logger.error(f"Error downloading image {image_url}: {str(e)}")
        return None


def scrape_wikipedia(output_file: Path, max_people: int = 20000) -> None:
    """Main function to scrape Wikipedia for famous people data."""
    wiki = setup_wikipedia_api()

    # Create output directories
    images_dir = WIKIPEDIA_DIR / "images"
    images_dir.mkdir(exist_ok=True)

    # Load existing data if it exists
    if output_file.exists():
        with open(output_file, "r", encoding="utf-8") as f:
            existing_data = json.load(f)
        existing_people = {p["name"]: p for p in existing_data}
    else:
        existing_people = {}

    # Scrape people from each category
    all_people = existing_people.copy()

    for category in WIKIPEDIA_CATEGORIES:
        if len(all_people) >= max_people:
            break

        logger.info(f"Processing category: {category}")
        members = get_category_members(category, wiki)

        for member in tqdm(members, desc=f"Processing {category}"):
            if len(all_people) >= max_people:
                break

            if member["title"] in all_people:
                continue

            person_info = get_person_info(member["title"], wiki)
            if not person_info:
                continue

            # Download image if available
            if person_info.get("image_url"):
                image_path = download_image(person_info["image_url"], images_dir)
                person_info["local_image_path"] = image_path

            all_people[person_info["name"]] = person_info

            # Save progress periodically
            if len(all_people) % 100 == 0:
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(
                        list(all_people.values()), f, ensure_ascii=False, indent=2
                    )

            # Be nice to Wikipedia's servers
            time.sleep(REQUEST_DELAY + random.uniform(0, 1))

    # Save final results
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(list(all_people.values()), f, ensure_ascii=False, indent=2)

    logger.info(f"Scraped {len(all_people)} people. Data saved to {output_file}")


def main():
    """Run the Wikipedia scraper."""
    output_file = WIKIPEDIA_DIR / "famous_people.json"

    try:
        scrape_wikipedia(output_file, max_people=20000)
        logger.info("Wikipedia scraping completed successfully!")
    except Exception as e:
        logger.error(f"Error during Wikipedia scraping: {str(e)}", exc_info=True)


if __name__ == "__main__":
    main()
