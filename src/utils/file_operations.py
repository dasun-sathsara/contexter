import os
import mimetypes


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


def get_all_files_recursive(base_paths, deleted_paths, text_only=False):
    """
    Collect all included file paths recursively, excluding deleted ones.

    Args:
        base_paths (list): List of base file/folder paths
        deleted_paths (set): Set of paths that have been deleted/excluded
        text_only (bool): If True, only include text files

    Returns:
        list: Sorted list of all file paths
    """
    all_files = set()
    for path in base_paths:
        if path not in deleted_paths:
            if os.path.isfile(path):
                if not text_only or is_text_file(path):
                    all_files.add(path)
            elif os.path.isdir(path):
                _collect_files(path, all_files, deleted_paths, text_only)
    return sorted(all_files)


def _collect_files(folder, all_files, deleted_paths, text_only=False):
    """
    Helper method to collect file paths recursively.

    Args:
        folder (str): Folder path to collect files from
        all_files (set): Set to store collected file paths
        deleted_paths (set): Set of paths that have been deleted/excluded
        text_only (bool): If True, only include text files
    """
    try:
        entries = os.listdir(folder)
    except Exception as e:
        print(f"Error reading folder {folder}: {e}")
        return
    for entry in entries:
        full_path = os.path.join(folder, entry)
        if full_path not in deleted_paths:
            if os.path.isfile(full_path):
                if not text_only or is_text_file(full_path):
                    all_files.add(full_path)
            elif os.path.isdir(full_path):
                _collect_files(full_path, all_files, deleted_paths, text_only)


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
