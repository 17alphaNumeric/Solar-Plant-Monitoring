"""
Watches the incoming-data folder for new CSV drops from the data logger,
loads them, and archives them once processed -- so the pipeline never
re-processes the same file twice.
"""
import logging
import shutil
import time
from pathlib import Path
from typing import Callable, List

import pandas as pd

import config

logger = logging.getLogger(__name__)


def list_new_files(incoming_dir: Path = config.INCOMING_DIR) -> List[Path]:
    """CSV files currently sitting in the incoming folder, oldest first."""
    files = sorted(incoming_dir.glob("*.csv"), key=lambda p: p.stat().st_mtime)
    return files


def load_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    logger.info("data_ingestion: read %d rows from %s", len(df), path.name)
    return df


def archive_file(path: Path, processed_dir: Path = config.PROCESSED_DIR) -> Path:
    """Move a processed file out of the incoming folder so it isn't re-read."""
    processed_dir.mkdir(parents=True, exist_ok=True)
    dest = processed_dir / path.name
    shutil.move(str(path), str(dest))
    return dest


def watch_folder(callback: Callable[[pd.DataFrame, Path], None],
                  incoming_dir: Path = config.INCOMING_DIR,
                  poll_seconds: int = 10,
                  max_iterations: int = None) -> None:
    """Continuously poll `incoming_dir` for new CSVs and hand each one to
    `callback(df, source_path)` as it arrives, then archive it.

    This is the "CSV arrives -> Python automatically starts" trigger from the
    project spec, implemented as lightweight polling (no extra OS-level
    filesystem-event dependency required).
    """
    iterations = 0
    logger.info("data_ingestion: watching %s every %ds", incoming_dir, poll_seconds)
    while max_iterations is None or iterations < max_iterations:
        for path in list_new_files(incoming_dir):
            try:
                df = load_csv(path)
                callback(df, path)
            except Exception:
                logger.exception("data_ingestion: failed to process %s", path)
            else:
                archive_file(path)
        iterations += 1
        if max_iterations is None or iterations < max_iterations:
            time.sleep(poll_seconds)
