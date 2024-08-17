import os


def get_all_files_recursive(base_paths, deleted_paths):
    """
    Collect all included file paths recursively, excluding deleted ones.

    Args:
        base_paths (list): List of base file/folder paths
        deleted_paths (set): Set of paths that have been deleted/excluded

    Returns:
        list: Sorted list of all file paths
    """
    all_files = set()
    for path in base_paths:
        if path not in deleted_paths:
            if os.path.isfile(path):
                all_files.add(path)
            elif os.path.isdir(path):
                _collect_files(path, all_files, deleted_paths)
    return sorted(all_files)


def _collect_files(folder, all_files, deleted_paths):
    """
    Helper method to collect file paths recursively.

    Args:
        folder (str): Folder path to collect files from
        all_files (set): Set to store collected file paths
        deleted_paths (set): Set of paths that have been deleted/excluded
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
                all_files.add(full_path)
            elif os.path.isdir(full_path):
                _collect_files(full_path, all_files, deleted_paths)


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
