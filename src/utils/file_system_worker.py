import os
from PyQt6.QtCore import QThread, pyqtSignal


class FileSystemWorker(QThread):
    """Worker thread for file system operations."""

    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    progress = pyqtSignal(int)

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
        except Exception as e:
            self.error.emit(str(e))
