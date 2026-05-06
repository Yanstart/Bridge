"""FileWatcherAdapter : surveille un repertoire et emet a chaque depot.

Utilise `watchdog` en thread d'observation. A chaque creation de fichier
matchant le pattern (`profile.channel.file_pattern`, ex. `*.json`), le
contenu est lu et pousse dans la queue. Le fichier source n'est pas
supprime ni renomme : la responsabilite de nettoyage revient au
producteur ou a une tache externe.

Ce design suppose que le producteur ecrit le fichier de maniere atomique
(write-then-rename). En demonstration, le simulateur respecte ce pattern.
"""

from __future__ import annotations

import asyncio
import fnmatch
import threading
from pathlib import Path

import structlog
from watchdog.events import FileSystemEvent, FileSystemEventHandler
# PollingObserver fonctionne meme sur les volumes Docker Desktop / SMB ou
# inotify peut etre defaillant. Il scrute le repertoire toutes les 2 s.
from watchdog.observers.polling import PollingObserver as Observer

from bridge_core.adapter.base import BaseAdapter, RawFrame, adapter_registry

logger = structlog.get_logger(__name__)


@adapter_registry.register("file_watcher")
class FileWatcherAdapter(BaseAdapter):
    """Surveille un repertoire et pousse le contenu de chaque nouveau fichier."""

    async def _run(self, queue: asyncio.Queue[RawFrame]) -> None:
        directory = Path(self.profile.channel.directory or "/app/drop")
        pattern = self.profile.channel.file_pattern or "*"
        loop = asyncio.get_running_loop()

        directory.mkdir(parents=True, exist_ok=True)

        class Handler(FileSystemEventHandler):
            def __init__(self_, adapter: FileWatcherAdapter) -> None:  # noqa: N805
                self.adapter = adapter

            def on_created(self_, event: FileSystemEvent) -> None:  # noqa: N805
                if event.is_directory:
                    return
                file_path = Path(event.src_path)
                if not fnmatch.fnmatch(file_path.name, pattern):
                    return
                try:
                    payload = file_path.read_bytes()
                except OSError as exc:
                    logger.warning(
                        "file_watcher.read_error",
                        device_id=self.profile.id,
                        path=str(file_path),
                        error=str(exc),
                    )
                    return
                frame = self._make_frame(
                    payload,
                    metadata={"source_path": str(file_path)},
                )
                asyncio.run_coroutine_threadsafe(queue.put(frame), loop)
                logger.info(
                    "file_watcher.captured",
                    device_id=self.profile.id,
                    file=file_path.name,
                    size=len(payload),
                )

        observer = Observer()
        observer.schedule(Handler(self), str(directory), recursive=False)
        observer.start()

        logger.info(
            "file_watcher.listening",
            device_id=self.profile.id,
            directory=str(directory),
            pattern=pattern,
        )

        try:
            await self._stop_event.wait()
        finally:
            observer.stop()
            await asyncio.to_thread(observer.join, timeout=5.0)
