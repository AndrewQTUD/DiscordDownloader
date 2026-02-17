import os
import json
import re
import requests
from urllib.parse import urlparse

# -------- CONFIG --------
ROOT_FOLDER = r"WHERE TO SAVE YOUR PACKAGE AFTER GDPR REQUESTd"
OUTPUT_FILE = r"WHERE TO SAVE OUTPUT FILE"
DOWNLOAD_FOLDER = r"WHERE TO SAVE FILES DOWNLOADED"

PATTERN = r"https://cdn\.discordapp\.com/attachments/\S+"
regex = re.compile(PATTERN)

# ------------------------


def search_in_data(data, file_path, results, path="root"):
    """Recursively search JSON structure."""
    if isinstance(data, dict):
        for key, value in data.items():
            search_in_data(value, file_path, results, f"{path}.{key}")

    elif isinstance(data, list):
        for i, item in enumerate(data):
            search_in_data(item, file_path, results, f"{path}[{i}]")

    elif isinstance(data, str):
        matches = regex.findall(data)
        for match in matches:
            results.append((file_path, path, match))


def process_json_file(file_path):
    results = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        search_in_data(data, file_path, results)

    except Exception as e:
        print(f"Skipping {file_path}: {e}")

    return results


def get_filename_from_url(url):
    """Extract filename safely from URL."""
    parsed = urlparse(url)
    return os.path.basename(parsed.path)


def download_file(url, download_folder):
    """Download attachment if not already downloaded."""
    filename = get_filename_from_url(url)
    save_path = os.path.join(download_folder, filename)

    if os.path.exists(save_path):
        print(f"Skipping (already exists): {filename}")
        return

    try:
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()

        with open(save_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        print(f"Downloaded: {filename}")

    except Exception as e:
        print(f"Failed download {url}: {e}")


def main():
    os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

    all_results = []
    unique_urls = set()

    # ---- Scan JSON files ----
    for root, _, files in os.walk(ROOT_FOLDER):
        for file in files:
            if file.lower().endswith(".json"):
                full_path = os.path.join(root, file)
                results = process_json_file(full_path)

                for r in results:
                    all_results.append(r)
                    unique_urls.add(r[2])

    # ---- Save matches ----
    with open(OUTPUT_FILE, "w", encoding="utf-8") as out:
        for file_path, location, url in all_results:
            out.write(f"File: {file_path}\n")
            out.write(f"Location: {location}\n")
            out.write(f"Match: {url}\n")
            out.write("-" * 60 + "\n")

    print(f"\nSaved {len(all_results)} matches.")
    print(f"Unique files to download: {len(unique_urls)}")

    # ---- Download attachments ----
    for url in unique_urls:
        download_file(url, DOWNLOAD_FOLDER)

    print("\nDone!")


if __name__ == "__main__":
    main()

