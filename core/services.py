"""Composition root: builds every service once and wires their dependencies."""
from dataclasses import dataclass

from core.cleaner import StorageCleaner
from core.config import ConfigManager
from core.converter import FileConverter
from core.exclusion import ExclusionPolicy
from core.logger import ActionLogger
from core.organizer import FileOrganizer
from core.paths import user_data_path
from core.stats import StorageAnalyzer
from core.watcher import WatcherManager


@dataclass
class AppServices:
    config: ConfigManager
    logger: ActionLogger
    exclusion: ExclusionPolicy
    cleaner: StorageCleaner
    organizer: FileOrganizer
    converter: FileConverter
    analyzer: StorageAnalyzer
    watcher: WatcherManager

    def set_excluded_folders(self, folders):
        self.config.set("excluded_folders", folders)
        self.exclusion.update(folders)


def build_services(config_path=None, log_txt=None, log_json=None):
    config = ConfigManager(config_path or user_data_path("config.json"))
    logger = ActionLogger(log_txt or user_data_path("action_log.txt"), log_json or user_data_path("action_log.json"))
    exclusion = ExclusionPolicy(config.get("excluded_folders"))
    return AppServices(
        config=config,
        logger=logger,
        exclusion=exclusion,
        cleaner=StorageCleaner(logger, exclusion),
        organizer=FileOrganizer(logger, exclusion=exclusion),
        converter=FileConverter(logger),
        analyzer=StorageAnalyzer(),
        watcher=WatcherManager(logger, exclusion),
    )
