#!/usr/bin/env python3
"""
Rename files from pattern '[0001-01-01] - [GHD-005] - fanart.jpg'
to 'GHD-005] - fanart.jpg' (remove the date prefix)
"""

import os
import re
from pathlib import Path


def rename_files_in_directory(directory: str = ".", dry_run: bool = True) -> None:
    """
    Rename files by removing the '[YYYY-MM-DD] - ' prefix.
    
    Args:
        directory: Directory to scan for files
        dry_run: If True, only print what would be done without actually renaming
    """
    # Pattern to match: [date] - [code] - rest_of_filename
    pattern = re.compile(r'^\[\d{4}-\d{2}-\d{2}\] - (\[.+)$')
    
    directory_path = Path(directory)
    
    if not directory_path.exists():
        print(f"Error: Directory '{directory}' does not exist")
        return
    
    renamed_count = 0
    
    for file_path in directory_path.iterdir():
        if not file_path.is_file():
            continue
            
        old_name = file_path.name
        match = pattern.match(old_name)
        
        if match:
            new_name = match.group(1)
            new_path = file_path.parent / new_name
            
            # Check if target already exists
            if new_path.exists():
                print(f"Skipping '{old_name}' -> '{new_name}' (target already exists)")
                continue
            
            if dry_run:
                print(f"[DRY RUN] Would rename: '{old_name}' -> '{new_name}'")
            else:
                try:
                    file_path.rename(new_path)
                    print(f"Renamed: '{old_name}' -> '{new_name}'")
                    renamed_count += 1
                except Exception as e:
                    print(f"Error renaming '{old_name}': {e}")
    
    if dry_run:
        print(f"\nDry run complete. Use dry_run=False to actually rename files.")
    else:
        print(f"\nRenamed {renamed_count} file(s)")


if __name__ == "__main__":
    import sys
    
    # Check for --execute flag to actually perform renaming
    dry_run = "--execute" not in sys.argv
    
    # Get directory from command line, default to current directory
    target_dir = "."
    for arg in sys.argv[1:]:
        if not arg.startswith("--"):
            target_dir = arg
            break
    
    print(f"Scanning directory: {Path(target_dir).absolute()}")
    print(f"Mode: {'DRY RUN (preview only)' if dry_run else 'EXECUTE (will rename files)'}")
    print("-" * 60)
    
    rename_files_in_directory(target_dir, dry_run=dry_run)
