import os
import mimetypes
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Set, Optional, List, Any, Tuple

from src.utils.gitignore import load_gitignore_patterns, is_ignored

# Centralized MimeTypes initialization for potential efficiency
mimetypes.init()

# Set of common text file extensions for quick checking
TEXT_EXTENSIONS = {
    ".txt",
    ".md",
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".html",
    ".htm",
    ".css",
    ".json",
    ".xml",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".conf",
    ".sh",
    ".bash",
    ".zsh",
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
    ".sql",
    ".csv",
    ".log",
    ".gitignore",
    ".gitattributes",
    ".dockerfile",
    "Dockerfile",
    ".env",
    ".properties",
    ".lua",
    ".r",
    ".dart",
    ".kt",
    ".swift",
    ".scala",
    ".tex",
    ".vbs",
    ".asp",
    ".aspx",
    ".jsp",
    ".tpl",
    ".erb",
    # Add more as needed
}

# Cache for is_text_file results to avoid redundant checks within a run
_is_text_file_cache: Dict[str, bool] = {}
_is_text_file_lock = threading.Lock()


def is_text_file(file_path: str) -> bool:
    """
    Determine if a file is likely a text file based on extension, mime type,
    and content inspection. Caches results per file path.

    Args:
        file_path (str): Path to the file.

    Returns:
        bool: True if the file is likely a text file, False otherwise.
    """
    # Check cache first
    with _is_text_file_lock:
        if file_path in _is_text_file_cache:
            return _is_text_file_cache[file_path]

    result = False
    try:
        # 1. Check by extension (common cases)
        _, ext = os.path.splitext(file_path.lower())
        if ext in TEXT_EXTENSIONS:
            result = True
        else:
            # 2. Check by mime type
            mime_type, encoding = mimetypes.guess_type(file_path)
            if mime_type and mime_type.startswith("text/"):
                result = True
            elif (
                encoding
            ):  # Sometimes encoding implies text (e.g., gzip text) - debatable
                pass  # Let content check decide

            # 3. Check content if unsure (avoid for known binary mimes if possible)
            if not result and (
                not mime_type
                or not (
                    "binary" in mime_type
                    or "octet-stream" in mime_type
                    or "application" in mime_type
                )
            ):
                # Read a small chunk to detect binary content (like null bytes)
                with open(file_path, "rb") as f:
                    chunk = f.read(8192)  # Read 8KB
                    if (
                        b"\x00" in chunk
                    ):  # Presence of NULL bytes strongly indicates binary
                        result = False
                    else:
                        # Try decoding a small part as UTF-8 as a fallback check
                        try:
                            chunk.decode("utf-8", errors="strict")
                            result = True  # Decoded successfully, likely text
                        except UnicodeDecodeError:
                            result = False  # Failed to decode, likely binary
    except IOError:  # File might not exist or be readable
        result = False
    except Exception as e:  # Catch other unexpected errors
        print(f"Warning: Error checking file type for {file_path}: {e}")
        result = False  # Default to non-text on error

    # Update cache
    with _is_text_file_lock:
        _is_text_file_cache[file_path] = result

    return result


def clear_text_file_cache():
    """Clears the cache used by is_text_file."""
    global _is_text_file_cache
    with _is_text_file_lock:
        _is_text_file_cache = {}


# --- FileTreeBuilder ---


class FileTreeBuilder:
    """
    Builds a nested dictionary representing a file tree structure based on
    base paths, applying filtering (.gitignore, text only, hide empty)
    and respecting a set of deleted paths. Caches .gitignore specs.
    """

    def __init__(
        self,
        base_paths: Set[str],
        text_only: bool = True,
        hide_empty_folders: bool = True,
        deleted_paths: Optional[Set[str]] = None,
    ):
        self.base_paths = {os.path.abspath(p) for p in base_paths}
        self.text_only = text_only
        self.hide_empty_folders = hide_empty_folders
        self.deleted_paths = deleted_paths or set()

        self._lock = threading.Lock()
        self._tree_cache: Optional[Dict[str, Any]] = None
        self._flat_file_list_cache: Optional[List[str]] = None
        self._gitignore_spec_cache: Dict[
            str, Optional[Any]
        ] = {}  # Cache for PathSpec objects per directory
        clear_text_file_cache()

    def build_tree(self):
        self._tree_cache = {"folders": {}, "files": []}
        self._flat_file_list_cache = []
        self._gitignore_spec_cache = {}  # Clear gitignore cache for rebuild

        # Use ThreadPoolExecutor for potentially faster scanning of multiple base paths
        # Adjust workers based on expected number of base paths vs cores
        num_workers = min(len(self.base_paths), (os.cpu_count() or 1) * 2)
        if num_workers <= 1:  # Avoid overhead for single base path
            results = [self._process_base_path(base) for base in self.base_paths]
        else:
            results = []
            with ThreadPoolExecutor(
                max_workers=num_workers, thread_name_prefix="TreeBuilderWorker"
            ) as executor:
                futures = {
                    executor.submit(self._process_base_path, base): base
                    for base in self.base_paths
                }
                for future in as_completed(futures):
                    try:
                        results.append(future.result())
                    except Exception as e:
                        base_path = futures[future]
                        print(f"Error processing base path {base_path}: {e}")

        # Combine results into the main tree structure
        for path, is_dir, subtree, files_found in results:
            if path:  # Ensure path is valid
                if is_dir:
                    if subtree is not None:  # Check if folder wasn't filtered out
                        self._tree_cache["folders"][path] = subtree
                else:
                    self._tree_cache["files"].append(path)
                if files_found:
                    self._flat_file_list_cache.extend(files_found)

        # Sort everything once at the end instead of per-folder
        self._sort_tree_recursively(self._tree_cache)
        self._flat_file_list_cache.sort()

    def _sort_tree_recursively(self, tree_node: Dict[str, Any]):
        """Sort files and folders recursively after tree is built."""
        if "files" in tree_node:
            tree_node["files"].sort()

        if "folders" in tree_node:
            for subfolder in tree_node["folders"].values():
                self._sort_tree_recursively(subfolder)

    def _get_gitignore_spec(self, folder_path: str) -> Optional[Any]:
        """Loads and caches .gitignore spec for a given folder path."""
        abs_folder_path = os.path.abspath(folder_path)
        if abs_folder_path in self._gitignore_spec_cache:
            return self._gitignore_spec_cache[abs_folder_path]

        spec = load_gitignore_patterns(
            abs_folder_path
        )  # load_gitignore handles traversal
        self._gitignore_spec_cache[abs_folder_path] = spec
        return spec

    def _process_base_path(
        self, base_path: str
    ) -> Tuple[Optional[str], bool, Optional[Dict], List[str]]:
        """Processes a single base path (file or directory)."""
        if base_path in self.deleted_paths:
            return None, False, None, []

        flat_files_found = []

        if os.path.isfile(base_path):
            if not self.text_only or is_text_file(base_path):
                flat_files_found.append(base_path)
                return base_path, False, None, flat_files_found
            else:
                return None, False, None, []  # Filtered out
        elif os.path.isdir(base_path):
            spec = self._get_gitignore_spec(base_path)
            # Pass the base path itself to scan_folder so it knows the root for relative paths
            subtree, files_in_subtree = self._scan_folder(base_path, base_path, spec)
            flat_files_found.extend(files_in_subtree)
            if (
                subtree is not None
            ):  # Only return if not filtered (e.g., empty and hide_empty=True)
                return base_path, True, subtree, flat_files_found
            else:
                return None, True, None, flat_files_found  # Filtered out directory
        else:
            # Path doesn't exist or is not a regular file/dir (link?)
            print(
                f"Warning: Base path '{base_path}' is not a file or directory or was deleted."
            )
            return None, False, None, []

    def _scan_folder(
        self, folder_path: str, root_path: str, parent_spec: Optional[Any]
    ) -> Tuple[Optional[Dict], List[str]]:
        """
        Recursively scans a folder, applies filters, and builds the subtree.
        Returns (subtree_dict | None, list_of_files_found_in_subtree).
        Returns None for subtree_dict if the folder should be hidden.
        """
        try:
            # Use os.scandir for potentially better performance than os.listdir
            entries = list(os.scandir(folder_path))
        except OSError as e:
            print(f"Warning: Cannot access folder '{folder_path}': {e}")
            return None, []  # Cannot scan, treat as empty/inaccessible

        folder_dict: Dict[str, Any] = {"folders": {}, "files": []}
        has_visible_content = False
        flat_files_found: List[str] = []

        # Get spec for the current folder (combining/overriding logic could be added here if needed)
        current_spec = self._get_gitignore_spec(folder_path)

        for entry in entries:
            full_path = entry.path
            # Get path relative to the *original* base path for gitignore matching
            # This assumes gitignore patterns are relative to the .gitignore file's location
            # A simpler approach might be needed if complex nested gitignores are involved.
            # Using path relative to current folder for matching seems more standard.
            rel_path_for_match = os.path.relpath(full_path, start=folder_path)

            if full_path in self.deleted_paths:
                continue
            # Check against spec for the current directory
            if is_ignored(rel_path_for_match, current_spec):
                continue

            try:
                if entry.is_file(follow_symlinks=False):
                    if not self.text_only or is_text_file(full_path):
                        folder_dict["files"].append(full_path)
                        flat_files_found.append(full_path)
                        has_visible_content = True
                elif entry.is_dir(follow_symlinks=False):
                    # Recursive call
                    # Pass current spec down? Git combines them. Let's rely on _get_gitignore_spec finding the right one.
                    subtree, files_in_subtree = self._scan_folder(
                        full_path, root_path, current_spec
                    )
                    flat_files_found.extend(files_in_subtree)
                    if subtree is not None:  # If the subdirectory is not hidden
                        folder_dict["folders"][full_path] = subtree
                        has_visible_content = True  # Folder has visible content if it contains a non-empty subfolder
                # Handle symlinks explicitly if needed
                # elif entry.is_symlink():
                #    pass # Decide how to handle symlinks

            except OSError as e:
                print(f"Warning: Cannot access entry '{full_path}': {e}")
                continue  # Skip problematic entries

        # Sorting is done once at the end of build_tree() for efficiency

        # Determine if this folder should be returned based on content and settings
        if not has_visible_content and self.hide_empty_folders:
            return None, flat_files_found  # Hide empty folder

        return folder_dict, flat_files_found

    def get_tree(self) -> Optional[Dict[str, Any]]:
        """Returns the cached file tree structure."""
        with self._lock:
            if self._tree_cache is None:
                self.build_tree()  # Build if not already built
            return self._tree_cache

    def get_flat_file_list(self) -> List[str]:
        """Returns the cached flat list of all included files."""
        with self._lock:
            if self._flat_file_list_cache is None:
                self.build_tree()  # Build if not already built
            # Return a copy to prevent external modification
            return (
                list(self._flat_file_list_cache) if self._flat_file_list_cache else []
            )

    def find_subtree(self, folder_path_to_find: str) -> Optional[Dict[str, Any]]:
        """Finds the subtree dictionary for a given absolute folder path within the cached tree."""
        tree = self.get_tree()
        if not tree:
            return None

        abs_path_to_find = os.path.abspath(folder_path_to_find)

        # Check top-level folders first
        if abs_path_to_find in tree.get("folders", {}):
            return tree["folders"][abs_path_to_find]

        # Recursive search function
        def search_recursive(current_subtree):
            for path, subfolder_data in current_subtree.get("folders", {}).items():
                if os.path.abspath(path) == abs_path_to_find:
                    return subfolder_data
                found = search_recursive(subfolder_data)
                if found:
                    return found
            return None

        return search_recursive(tree)


# --- Other File Operations ---


def merge_file_contents(file_paths: List[str]) -> str:
    """
    Merge contents of multiple text files with markdown-style headers.

    Args:
        file_paths (list): List of file paths to merge.

    Returns:
        str: Merged content of all files in markdown format, or empty string if no files.
    """
    output = []
    for file_path in file_paths:
        if is_text_file(file_path):
            try:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                # Use normalized path for consistency
                normalized_path = file_path.replace(os.sep, "/")

                # Add the markdown-style header
                output.append(f"#### {normalized_path}")
                output.append("")  # Blank line after header
                output.append("```")  # Start code block
                output.append(content.rstrip())  # Remove trailing whitespace
                output.append("```")  # End code block
                output.append("")  # Blank line after code block
            except Exception as e:
                error_msg = f"Error reading file {file_path}: {e}"
                print(error_msg)
        else:
            print(f"Skipping non-text file during merge: {file_path}")

    # Join with newlines and add a final newline
    return "\n".join(output + [""])
