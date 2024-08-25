import os
from PyQt6.QtCore import QThread, pyqtSignal
from src.utils.token_counter import count_tokens_in_file, count_tokens_in_folder


class FileSystemWorker(QThread):
    """Worker thread for file system operations."""

    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    progress = pyqtSignal(int)
    token_count_result = pyqtSignal(str, int)  # path, token_count

    def __init__(self, operation, *args):
        super().__init__()
        self.operation = operation
        self.args = args

    def run(self):
        try:
            if self.operation == "list_dir":
                folder = self.args[0]
                try:
                    result = sorted(os.listdir(folder))
                    self.finished.emit(result)
                except Exception as e:
                    self.error.emit(str(e))
                    return
            elif self.operation == "merge_files":
                files = self.args[0]
                total_files = len(files)
                result = []
                for i, file_path in enumerate(files):
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            content = f.read()
                        header = f"############## {file_path.replace(os.sep, '/')} ##############"
                        result.extend([header, content, ""])
                        self.progress.emit(int((i + 1) / total_files * 100))
                    except Exception as e:
                        print(f"Error reading file {file_path}: {e}")
                self.finished.emit("\n".join(result))
            elif self.operation == "count_tokens":
                path = self.args[0]
                text_only = self.args[1] if len(self.args) > 1 else True
                deleted_paths = self.args[2] if len(self.args) > 2 else set()
                
                try:
                    if os.path.isfile(path):
                        token_count = count_tokens_in_file(path)
                    else:  # It's a directory
                        token_count = count_tokens_in_folder(path, text_only, deleted_paths)
                    
                    self.token_count_result.emit(path, token_count)
                    self.finished.emit((path, token_count))
                except Exception as e:
                    self.error.emit(f"Error counting tokens in {path}: {str(e)}")
                    return
        except Exception as e:
            self.error.emit(str(e))
