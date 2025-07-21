############## C:/Users/dasun/Desktop/Python/src/utils/file_system_worker.py ##############
import os
from PyQt6.QtCore import QThread, pyqtSignal

from src.utils.file_operations import merge_file_contents


class FileSystemWorker(QThread):
    """
    Worker thread primarily for potentially long-running, blocking file system
    operations like merging large numbers of files, to avoid freezing the UI.
    Token counting is now handled by FileManager's ThreadPoolExecutor.
    """

    finished = pyqtSignal(object)  # Emits result data on success
    error = pyqtSignal(str)  # Emits error message on failure
    progress = pyqtSignal(int)  # Emits percentage progress (0-100)

    def __init__(self, operation: str, *args):
        super().__init__()
        self.operation = operation
        self.args = args
        self._is_running = True

    def stop(self):
        """Request the worker to stop."""
        self._is_running = False

    def run(self):
        """Executes the requested file system operation."""
        self._is_running = True
        try:
            if self.operation == "merge_files":
                files_to_merge = self.args[0]
                if not files_to_merge:
                    self.finished.emit("")
                    return

                # Use the refactored merge function
                # Note: merge_file_contents itself might read files sequentially.
                # For massive merges, further optimization (async reading) might be needed.
                # Progress reporting here is simplified as merge_file_contents does it all at once.
                # A more granular progress would require changing merge_file_contents.
                self.progress.emit(50)  # Indicate processing started
                if not self._is_running:
                    return  # Check if stopped

                result = merge_file_contents(files_to_merge)

                if not self._is_running:
                    return  # Check if stopped before emitting

                self.progress.emit(100)
                self.finished.emit(result)

            # Add other long-running, blocking operations here if needed in the future
            # elif self.operation == "some_other_blocking_op":
            #    # ... implementation ...
            #    pass

            else:
                self.error.emit(f"Unknown FileSystemWorker operation: {self.operation}")

        except Exception as e:
            import traceback

            print(f"Error in FileSystemWorker ({self.operation}): {e}")
            traceback.print_exc()
            self.error.emit(str(e))
