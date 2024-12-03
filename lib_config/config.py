"""
Library module for configuration and logging setup for the application.
Defines types for the configuration and provides a method to load and setup logging.
Optionally, the working directory can be set to the directory of the calling script
to enable files to be loaded relative to the script without resorting to absolute paths.
"""

import json
import os
from dataclasses import dataclass
from typing import Optional
from typing import Any
import logging
import logging.handlers
import colorlog
from datetime import datetime

@dataclass
class WebConfig:
    host: str
    port: int
    debug: bool

@dataclass
class ClientConfig:
    interval: int

@dataclass
class DatabaseConfig:
    connection_string: str

@dataclass
class ConsoleLoggingConfig:
    enabled: bool
    level: str
    format: str
    date_format: str
    def get_level(self) -> int:
        return getattr(logging, self.level.upper())

@dataclass
class FileLoggingConfig(ConsoleLoggingConfig):
    log_dir: str
    filename: str
    max_bytes: int
    backup_count: int

@dataclass
class LoggingConfig:
    console_output: ConsoleLoggingConfig
    file_output: FileLoggingConfig

class Config:
    web: WebConfig
    database: DatabaseConfig
    logging_config: LoggingConfig

    @staticmethod
    def set_working_directory(script_path: str) -> str:
        """
        Sets working directory to the location of the calling script's path as supplied by __file__.
        Can be used to set the working directory to the location in which the config file is found
        without resorting to absolute paths.
        Args:
            script_path: The __file__ value from the calling script.
        Returns:
            The new working directory path
        """
        script_dir = os.path.dirname(os.path.abspath(script_path))
        os.chdir(script_dir)
        return script_dir

    def __init__(self, script_path:str =None, config_path: str = "config.json"):
        """Loads the config for usage elsewhere and sets up logging according to the configuration"""
        if script_path:
            self.set_working_directory(script_path)
        self._config = self._load_config(config_path)
        #Explicitly convert the nested dictionaries to Config objects so they are strongly typed.
        self.web = WebConfig(**self._config.get('web', {}))
        self.client = ClientConfig(**self._config.get('client', {}))
        self.database = DatabaseConfig(**self._config.get('database', {}))
        raw_logging_config = self._config.get('logging_config', {})
        self.logging_config = LoggingConfig(
            console_output=ConsoleLoggingConfig(**raw_logging_config.get('console_output', {})),
            file_output=FileLoggingConfig(**raw_logging_config.get('file_output', {}))
        )
        self.setup_logging()

        
        
    def _load_config(self, config_path: str) -> dict:
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Config file not found: {config_path}")
        with open(config_path, 'r') as f:
            return json.load(f)
    
    def setup_logging(self) -> logging.Logger:
        # Create logs directory if needed and file output is enabled
        if self.logging_config.file_output.enabled:
            os.makedirs(self.logging_config.file_output.log_dir, exist_ok=True)
                
        # Get root logger
        logger = logging.getLogger()

        # Set base filtering to be the lowest of all enabled handlers.
        root_level = logging.NOTSET  # Default if no handlers are enabled (essentially suppresses all messages)
        enabled_levels = []
        if self.logging_config.console_output.enabled:
            enabled_levels.append(self.logging_config.console_output.get_level())
        if self.logging_config.file_output.enabled:
            enabled_levels.append(self.logging_config.file_output.get_level())
        if enabled_levels:
            root_level = min(enabled_levels)        
        logger.setLevel(root_level)

        # Clear any existing handlers
        logger.handlers.clear()
        
        # Add console handler if enabled
        if self.logging_config.console_output.enabled:
            console_handler = logging.StreamHandler()
            console_formatter = colorlog.ColoredFormatter(
            fmt='%(log_color)s' + self.logging_config.console_output.format,
            datefmt=self.logging_config.console_output.date_format,
            reset=True,
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red,bg_white'
            }
            )
            console_handler.setFormatter(console_formatter)
            console_handler.setLevel(self.logging_config.console_output.get_level())
            logger.addHandler(console_handler)
        
        # Add file handler if enabled
        if self.logging_config.file_output.enabled:
            file_path = os.path.join(self.logging_config.file_output.log_dir, self.logging_config.file_output.filename + datetime.now().strftime("-%Y%m%d.log"))
            file_handler = logging.handlers.RotatingFileHandler(
                file_path,
                maxBytes=self.logging_config.file_output.max_bytes,
                backupCount=self.logging_config.file_output.backup_count
            )
            file_formatter = logging.Formatter(
                fmt=self.logging_config.file_output.format,
                datefmt=self.logging_config.file_output.date_format
            )
            file_handler.setFormatter(file_formatter)
            file_handler.setLevel(self.logging_config.file_output.get_level())
            logger.addHandler(file_handler)
        
        return logger