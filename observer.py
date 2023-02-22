import os
import time
from PySide6.QtCore import QObject, Signal
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class FileObserver(QObject):

    fileDeleted = Signal(str)
    fileMoved = Signal(str, str)
    fileCreated = Signal(str)
    fileModified = Signal(str)

    def __init__(self):
        super().__init__()
        self.folder_path = os.getcwd()
        self.running = False

    def run(self):
        event_handler = Handler(self)
        self.running = True

        self.observer = Observer()
        self.observer.schedule(event_handler, self.folder_path, recursive=True)
        self.observer.start()
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.observer.stop()
        self.observer.join()
    
    def stop(self):
        self.running = False
        self.observer.stop()
        self.observer.join()


class Handler(FileSystemEventHandler):
    def __init__(self, parent):
        super().__init__()
        self.m = parent.fileMoved
        self.c = parent.fileCreated
        self.d = parent.fileDeleted
        self.mod = parent.fileModified

    def on_moved(self, event):
        if '$' not in event.src_path and '$' not in event.dest_path:
            self.m.emit(event.src_path, event.dest_path)

    def on_created(self, event):
        if '$' not in event.src_path:
            self.c.emit(event.src_path)

    def on_deleted(self, event):
        if '$' not in event.src_path:
            self.d.emit(event.src_path)

    def on_modified(self, event):
        if '$' not in event.src_path:
            self.mod.emit(event.src_path)