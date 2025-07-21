import os
import tiktoken
from typing import Optional, Set


# Cache the encoder to avoid rebuilding it for every file
def get_encoder():
    """Get tiktoken encoder with fallback options."""
    try:
        return tiktoken.get_encoding("cl100k_base")
    except ValueError:
        # Fallback to older encoding if cl100k_base is not available
        try:
            return tiktoken.get_encoding("p50k_base")
        except ValueError:
            # Last resort fallback
            return tiktoken.encoding_for_model("gpt-3.5-turbo")


_enc = None


def count_tokens_in_file(file_path: str) -> int:
    """
    Count the number of tokens in a file using tiktoken.

    Args:
        file_path (str): Path to the file

    Returns:
        int: Number of tokens in the file
    """
    global _enc
    if _enc is None:
        _enc = get_encoder()

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Use cached encoder with disallowed_special=() to allow all special tokens
        tokens = _enc.encode(content, disallowed_special=())
        return len(tokens)
    except Exception as e:
        print(f"Error counting tokens in {file_path}: {e}")
        return 0


def count_tokens_in_folder(
    folder_path: str, text_only: bool = True, deleted_paths: Optional[Set[str]] = None
) -> int:
    """
    Count the total number of tokens in all files in a folder recursively.

    Args:
        folder_path (str): Path to the folder
        text_only (bool): If True, only count tokens in text files
        deleted_paths (set): Set of paths that have been deleted/excluded

    Returns:
        int: Total number of tokens in the folder
    """
    if deleted_paths is None:
        deleted_paths = set()

    if folder_path in deleted_paths:
        return 0

    total_tokens = 0

    try:
        for root, dirs, files in os.walk(folder_path):
            # Skip deleted paths
            dirs[:] = [d for d in dirs if os.path.join(root, d) not in deleted_paths]

            for file in files:
                file_path = os.path.join(root, file)
                if file_path not in deleted_paths:
                    from src.utils.file_operations import is_text_file

                    if not text_only or is_text_file(file_path):
                        total_tokens += count_tokens_in_file(file_path)
    except Exception as e:
        print(f"Error counting tokens in folder {folder_path}: {e}")

    return total_tokens
