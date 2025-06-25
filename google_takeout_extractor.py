"""
Google Takeout Extractor
This script extracts selected files from Google Takeout zip files, allowing users
to filter by file extensions and handle duplicates according to user preferences.
"""

import os
import zipfile
import argparse
from tqdm import tqdm
from pathlib import Path


def should_extract(filename: str, include_exts: set, filter_exts: set) -> bool:
    ext = Path(filename).suffix.lower()
    if include_exts and ext not in include_exts:
        return False
    if ext in filter_exts:
        return False
    return True


def extract_member(zip_ref, member, destination_path):
    file_size = zip_ref.getinfo(member).file_size
    with zip_ref.open(member) as src, open(destination_path, "wb") as dst:
        with tqdm(
            total=file_size,
            desc=f"Extracting {os.path.basename(destination_path)}",
            unit="B",
            unit_scale=True,
            unit_divisor=1024,
            position=2,
            leave=False,
        ) as file_pbar:
            while True:
                buffer = src.read(1024 * 1024)  # Read in 1 MB chunks
                if not buffer:
                    break
                dst.write(buffer)
                file_pbar.update(len(buffer))


# ─── Duplicate Handling Strategies ────────────────────────────────────────────


def handle_skip_duplicate(member, zip_ref, destination_path, log):
    tqdm.write(f"→ Skipped existing file: {destination_path}")
    log.write(f"SKIPPED: {destination_path}\n")


def handle_replace_duplicate(member, zip_ref, destination_path, log):
    tqdm.write(f"→ Replacing: {destination_path}")
    extract_member(zip_ref, member, destination_path)
    log.write(f"REPLACED: {destination_path}\n")


def handle_prompt_duplicate(member, zip_ref, destination_path, log):
    tqdm.write(f"File already exists: {destination_path}")
    while True:
        action = input("Do you want to (s)kip or (r)eplace? [s/r]: ").lower()
        if action == "s":
            handle_skip_duplicate(member, zip_ref, destination_path, log)
            break
        elif action == "r":
            handle_replace_duplicate(member, zip_ref, destination_path, log)
            break
        else:
            tqdm.write("Invalid input. Enter 's' or 'r'.")


# ─── Main Extraction Logic ────────────────────────────────────────────────────


def process_zip_files(
    zip_files, output_folder, include_exts, filter_exts, duplicate_mode, log
):
    if duplicate_mode == "1":
        handle_duplicate = handle_skip_duplicate
    elif duplicate_mode == "2":
        handle_duplicate = handle_replace_duplicate
    else:
        handle_duplicate = handle_prompt_duplicate

    with tqdm(
        total=len(zip_files), desc="ZIP Files", position=0, leave=True
    ) as zip_pbar:
        for zip_path in zip_files:
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                members = [
                    m
                    for m in zip_ref.namelist()
                    if not m.endswith("/")
                    and should_extract(m, include_exts, filter_exts)
                ]

                with tqdm(
                    total=len(members),
                    desc="Extracting Files",
                    position=1,
                    leave=False,
                    unit="file",
                ) as file_pbar:
                    for member in members:
                        destination_path = os.path.join(output_folder, member)
                        os.makedirs(os.path.dirname(destination_path), exist_ok=True)

                        if os.path.exists(destination_path):
                            file_pbar.write(
                                f"Duplicate file exists: {destination_path}"
                            )
                            handle_duplicate(member, zip_ref, destination_path, log)
                        else:
                            extract_member(zip_ref, member, destination_path)
                            log.write(f"ADDED: {destination_path}\n")

                        file_pbar.update(1)

            zip_pbar.update(1)


def main(zip_folder: str, output_folder: str, include_files: list, filter_files: list):
    include_exts = set(f".{ext.lower()}" for ext in include_files)
    filter_exts = set(f".{ext.lower()}" for ext in filter_files)
    log_file = "extraction_log.txt"
    log_path = os.path.join(output_folder, log_file)

    tqdm.write("\nHow should duplicate files be handled?")
    tqdm.write("1. Always skip duplicates")
    tqdm.write("2. Always replace duplicates")
    tqdm.write("3. Ask for each duplicate")

    while True:
        duplicate_mode = input("Enter your choice [1/2/3]: ").strip()
        if duplicate_mode in {"1", "2", "3"}:
            break
        tqdm.write("Invalid input. Please enter 1, 2, or 3.")

    os.makedirs(output_folder, exist_ok=True)
    log = open(log_path, "w", encoding="utf-8")

    process_zip_files(
        [
            os.path.join(zip_folder, zip_name)
            for zip_name in os.listdir(zip_folder)
            if zip_name.endswith(".zip")
        ],
        output_folder,
        include_exts,
        filter_exts,
        duplicate_mode,
        log,
    )
    log.close()
    tqdm.write(f"\n✅ Extraction complete. Log saved to: {log_path}")


# ─── Entry Point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extract selected files from Google Takeout zips."
    )

    parser.add_argument(
        "--zip-folder",
        required=True,
        help="Path to folder containing Google Takeout zip files",
    )
    parser.add_argument(
        "--output-folder",
        default="All_Google_Photos",
        help="Output folder for extracted files",
    )
    parser.add_argument(
        "--filter-files",
        nargs="*",
        default=[],
        help="File extensions to exclude (e.g. json heic)",
    )
    parser.add_argument(
        "--include-files",
        nargs="*",
        default=[],
        help="File extensions to include (e.g. jpg png)",
    )

    args = parser.parse_args()

    main(
        zip_folder=args.zip_folder,
        output_folder=args.output_folder,
        include_files=args.include_files,
        filter_files=args.filter_files,
    )
