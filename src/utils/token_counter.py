import os
import threading
from typing import Optional, Set, Tuple

import tiktoken

# Encoder cache
_enc = None
_enc_lock = threading.Lock()

# Token cache: path -> (token_count, mtime, size)
_token_cache_lock = threading.Lock()
_token_cache: dict[str, Tuple[int, float, int]] = {}


def get_encoder():
    """Get tiktoken encoder with fallback options (cached)."""
    global _enc
    if _enc is not None:
        return _enc
    with _enc_lock:
        if _enc is not None:
            return _enc
        try:
            _enc = tiktoken.get_encoding("cl100k_base")
        except ValueError:
            try:
                _enc = tiktoken.get_encoding("p50k_base")
            except ValueError:
                _enc = tiktoken.encoding_for_model("gpt-3.5-turbo")
        return _enc


def _stat_path(path: str) -> Optional[Tuple[float, int]]:
    """Return (mtime, size) for a path or None if not accessible."""
    try:
        st = os.stat(path)
        return st.st_mtime, st.st_size
    except Exception:
        return None


def get_cached_token_count(file_path: str) -> Optional[int]:
    """
    Return cached token count for file_path if cache is fresh (mtime/size match),
    else None.
    """
    stat = _stat_path(file_path)
    if stat is None:
        # File no longer exists; treat as 0 tokens and cache it
        with _token_cache_lock:
            _token_cache[file_path] = (0, -1.0, 0)
        return 0

    mtime, size = stat
    with _token_cache_lock:
        entry = _token_cache.get(file_path)
        if entry and entry[1] == mtime and entry[2] == size:
            return entry[0]
    return None


def count_tokens_in_file(file_path: str) -> int:
    """
    Count the number of tokens in a file using tiktoken, with caching based on
    (mtime, size).
    """
    enc = get_encoder()

    stat = _stat_path(file_path)
    if stat is None:
        with _token_cache_lock:
            _token_cache[file_path] = (0, -1.0, 0)
        return 0

    mtime, size = stat
    with _token_cache_lock:
        entry = _token_cache.get(file_path)
        if entry and entry[1] == mtime and entry[2] == size:
            return entry[0]

    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        tokens = enc.encode(content, disallowed_special=())
        count = len(tokens)
    except Exception as e:
        print(f"Error counting tokens in {file_path}: {e}")
        count = 0

    with _token_cache_lock:
        _token_cache[file_path] = (count, mtime, size)

    return count


def count_tokens_in_folder(
    folder_path: str, text_only: bool = True, deleted_paths: Optional[Set[str]] = None
) -> int:
    """
    Count the total number of tokens in all files in a folder recursively.
    Uses cached per-file counts when available.
    Note: This function does not apply .gitignore filtering. Prefer using the
    FileTreeBuilder with aggregation in the UI for exact consistency.
    """
    if deleted_paths is None:
        deleted_paths = set()
    if folder_path in deleted_paths:
        return 0

    total_tokens = 0
    try:
        for root, dirs, files in os.walk(folder_path):
            dirs[:] = [d for d in dirs if os.path.join(root, d) not in deleted_paths]
            for file in files:
                file_path = os.path.join(root, file)
                if file_path in deleted_paths:
                    continue
                from src.utils.file_operations import is_text_file

                if not text_only or is_text_file(file_path):
                    cached = get_cached_token_count(file_path)
                    if cached is not None:
                        total_tokens += cached
                    else:
                        total_tokens += count_tokens_in_file(file_path)
    except Exception as e:
        print(f"Error counting tokens in folder {folder_path}: {e}")

    return total_tokens
