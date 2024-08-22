import os
import mimetypes
from concurrent.futures import ThreadPoolExecutor


def is_text_file(file_path):
    """
    Determine if a file is a text file based on its content and extension.

    Args:
        file_path (str): Path to the file

    Returns:
        bool: True if the file is likely a text file, False otherwise
    """
    # Check common text file extensions
    text_extensions = {
        ".txt",
        ".md",
        ".py",
        ".js",
        ".html",
        ".css",
        ".json",
        ".xml",
        ".csv",
        ".yml",
        ".yaml",
        ".toml",
        ".ini",
        ".cfg",
        ".conf",
        ".sh",
        ".bat",
        ".ps1",
        ".c",
        ".cpp",
        ".h",
        ".hpp",
        ".java",
        ".php",
        ".rb",
        ".pl",
        ".rs",
        ".go",
        ".ts",
        ".jsx",
        ".tsx",
    }

    _, ext = os.path.splitext(file_path.lower())
    if ext in text_extensions:
        return True

    # Check mime type
    mime_type, _ = mimetypes.guess_type(file_path)
    if mime_type and mime_type.startswith("text/"):
        return True

    # Try to read the file as text
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            # Read first 8KB of the file to check if it's text
            sample = f.read(8192)
            # If sample contains null bytes, it's likely binary
            if "\0" in sample:
                return False
            # If more than 30% non-ASCII chars, probably binary
            non_ascii = sum(1 for c in sample if ord(c) > 127)
            if non_ascii > 0.3 * len(sample):
                return False
            return True
    except UnicodeDecodeError:
        # Failed to decode as UTF-8
        return False
    except Exception:
        # Any other error, default to non-text
        return False


def _check_folder_empty(folder_path, text_only, deleted_paths):
    """
    Helper function to check if a folder is empty, suitable for parallel execution.
    """
    try:
        entries = os.listdir(folder_path)
    except Exception:
        return True

    for entry in entries:
        full_path = os.path.join(folder_path, entry)
        if full_path in deleted_paths:
            continue

        if os.path.isfile(full_path):
            if not text_only or is_text_file(full_path):
                return False
        elif os.path.isdir(full_path):
            if not is_folder_empty(full_path, text_only, deleted_paths):
                return False

    return True


def is_folder_empty(folder_path, text_only=False, deleted_paths=None):
    """
    Check if a folder is empty or contains only empty subfolders.

    Args:
        folder_path (str): Path to the folder to check
        text_only (bool): If True, consider a folder empty if it contains no text files
        deleted_paths (set): Set of paths that have been deleted/excluded

    Returns:
        bool: True if the folder is empty (or has only empty subfolders), False otherwise
    """
    if deleted_paths is None:
        deleted_paths = set()

    return _check_folder_empty(folder_path, text_only, deleted_paths)


def _collect_files_worker(args):
    """
    Worker function for collecting files in parallel.
    """
    folder, all_files, deleted_paths, text_only = args
    try:
        entries = os.listdir(folder)
        result = []
        for entry in entries:
            full_path = os.path.join(folder, entry)
            if full_path not in deleted_paths:
                if os.path.isfile(full_path):
                    if not text_only or is_text_file(full_path):
                        result.append(full_path)
                elif os.path.isdir(full_path):
                    subdir_files = _collect_files_worker(
                        (full_path, all_files, deleted_paths, text_only)
                    )
                    result.extend(subdir_files)
        return result
    except Exception as e:
        print(f"Error reading folder {folder}: {e}")
        return []


def get_all_files_recursive(base_paths, deleted_paths, text_only=False):
    """
    Collect all included file paths recursively, excluding deleted ones.
    Uses parallel processing for better performance with large directories.

    Args:
        base_paths (set): Set of base file/folder paths
        deleted_paths (set): Set of paths that have been deleted/excluded
        text_only (bool): If True, only include text files

    Returns:
        list: Sorted list of all file paths
    """
    all_files = set()
    folders_to_process = []

    # Process immediate files and collect folders
    for path in base_paths:
        if path not in deleted_paths:
            if os.path.isfile(path):
                if not text_only or is_text_file(path):
                    all_files.add(path)
            elif os.path.isdir(path):
                folders_to_process.append(path)

    # Process folders in parallel if there are any
    if folders_to_process:
        with ThreadPoolExecutor() as executor:
            args = [
                (folder, all_files, deleted_paths, text_only)
                for folder in folders_to_process
            ]
            results = executor.map(_collect_files_worker, args)
            for result in results:
                all_files.update(result)

    return sorted(all_files)


def merge_file_contents(file_paths):
    """
    Merge contents of multiple files with headers.

    Args:
        file_paths (list): List of file paths to merge

    Returns:
        str: Merged content of all files
    """
    output = []
    for file_path in file_paths:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            header = f"############## {file_path.replace(os.sep, '/')} ##############"
            output.append(header)
            output.append(content)
            output.append("")
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
    return "\n".join(output)
