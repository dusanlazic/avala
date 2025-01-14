from pathlib import Path
from typing import Callable

from watchdog.events import FileSystemEvent, FileSystemEventHandler


class FileEventHandler(FileSystemEventHandler):
    """
    A custom event handler that processes file modifications and triggers a callback.

    :param callback: A callable function that is triggered when a file is modified. It takes a single argument, a `Path`
                    object representing the modified file.
    :type callback: Callable[[Path], None]
    """

    def __init__(self, callback: Callable[[Path], None]) -> None:
        """
        Initialize the FileEventHandler with a callback function.

        :param callback: The function to be called when a file modification event occurs.
        :type callback: Callable[[Path], None]
        """
        self.callback = callback
        super().__init__()

    def on_modified(self, event: FileSystemEvent) -> None:
        """
        Handle file modification events.

        :param event: The file system event that occurred.
        :type event: FileSystemEvent
        """
        if event.is_directory:
            return
        self.callback(Path(event.src_path).resolve())
