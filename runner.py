import os
import json
import re
import requests
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import threading

# -------- CONFIG --------
ROOT_FOLDER = r"C:\Users\Andy\Desktop\Discord"
OUTPUT_FILE = r"C:\Users\Andy\Desktop\Results\results.txt"
DOWNLOAD_FOLDER = r"G:\DiscDown"

MAX_WORKERS = 8   # increase (8–32) for faster downloads

PATTERN = r"https://cdn\.discordapp\.com/attachments/\S+"
regex = re.compile(PATTERN)
# ------------------------

# Lock prevents filename race conditions between threads
filename_lock = threading.Lock()


# ---------- JSON SEARCH ----------
def search_in_data(data, file_path, results, path="root"):
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


# ---------- DOWNLOAD HELPERS ----------
def get_filename_from_url(url):
    parsed = urlparse(url)
    return os.path.basename(parsed.path)


def get_unique_filepath(folder, filename):
    """
    Thread-safe filename collision handling.
    """
    with filename_lock:
        base, ext = os.path.splitext(filename)
        counter = 1
        new_path = os.path.join(folder, filename)

        while os.path.exists(new_path):
            new_filename = f"{base}_{counter}{ext}"
            new_path = os.path.join(folder, new_filename)
            counter += 1

        return new_path


def download_file(url):
    filename = get_filename_from_url(url)
    save_path = get_unique_filepath(DOWNLOAD_FOLDER, filename)

    try:
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()

        with open(save_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        return True

    except Exception:
        return False


# ---------- MAIN ----------
def main():
    os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

    all_results = []
    unique_urls = set()

    print("Scanning JSON files...")

    # Scan folders
    for root, _, files in os.walk(ROOT_FOLDER):
        for file in files:
            if file.lower().endswith(".json"):
                full_path = os.path.join(root, file)
                results = process_json_file(full_path)

                for r in results:
                    all_results.append(r)
                    unique_urls.add(r[2])

    # Save matches
    with open(OUTPUT_FILE, "w", encoding="utf-8") as out:
        for file_path, location, url in all_results:
            out.write(f"File: {file_path}\n")
            out.write(f"Location: {location}\n")
            out.write(f"Match: {url}\n")
            out.write("-" * 60 + "\n")

    print(f"\nSaved {len(all_results)} matches.")
    print(f"Unique files to download: {len(unique_urls)}")

    # ---------- MULTI-THREADED DOWNLOAD ----------
    print("\nDownloading attachments...")

    success = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(download_file, url) for url in unique_urls]

        for future in tqdm(as_completed(futures),
                           total=len(futures),
                           desc="Downloading",
                           unit="file"):
            if future.result():
                success += 1

    print(f"\nDownloaded successfully: {success}/{len(unique_urls)}")
    print("Done!")


if __name__ == "__main__":
    main()

