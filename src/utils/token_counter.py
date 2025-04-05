import os
import tiktoken
from typing import Dict, Set


def count_tokens_in_file(file_path: str) -> int:
    """
    Count the number of tokens in a file using tiktoken.
    
    Args:
        file_path (str): Path to the file
        
    Returns:
        int: Number of tokens in the file
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Use cl100k_base encoder which is used by GPT-4 and GPT-3.5-turbo
        enc = tiktoken.get_encoding("cl100k_base")
        tokens = enc.encode(content)
        return len(tokens)
    except Exception as e:
        print(f"Error counting tokens in {file_path}: {e}")
        return 0


from typing import Optional, Set

def count_tokens_in_folder(folder_path: str, text_only: bool = True, deleted_paths: Optional[Set[str]] = None) -> int:
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
