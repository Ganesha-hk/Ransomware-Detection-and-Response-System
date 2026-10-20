from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from watchdog.observers.polling import PollingObserver


class Handler(FileSystemEventHandler):
    def __init__(self, runtime, root):
        self.runtime, self.root = runtime, root

    def on_any_event(self, event):
        if not event.is_directory and event.event_type in (
            "created",
            "modified",
            "moved",
            "deleted",
        ):
            self.runtime.enqueue(
                self.root,
                event.event_type,
                event.src_path,
                getattr(event, "dest_path", None),
                getattr(event, "is_synthetic", False),
            )


def observer(runtime):
    o = PollingObserver(timeout=0.2) if runtime.config.monitor.observer == "polling" else Observer()
    for root in runtime.config.monitor.watch_paths:
        o.schedule(Handler(runtime, root), root, recursive=runtime.config.monitor.recursive)
    return o
