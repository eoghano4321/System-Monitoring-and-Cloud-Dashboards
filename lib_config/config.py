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
import csv

@dataclass
class WebConfig:
    host: str
    port: int
    debug: bool

@dataclass
class ClientConfig:
    interval: int
    socket_host: str
    socket_port: int

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

@dataclass
class Aggregator:
    agg_id: str

class Config:
    web: WebConfig
    database: DatabaseConfig
    logging_config: LoggingConfig
    aggregator: Aggregator
    mode = ""

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

    def __init__(self, script_path:str =None, run_type:str = None, config_path: str = "config.json"):
        """Loads the config for usage elsewhere and sets up logging according to the configuration"""
        if script_path:
            self.set_working_directory(script_path)
        if run_type:
            self.mode = run_type
        self._config = self._load_config(config_path)
        #Explicitly convert the nested dictionaries to Config objects so they are strongly typed.
        self.web = WebConfig(**self._config.get('web', {}))
        self.client = ClientConfig(**self._config.get('client', {}))
        self.database = DatabaseConfig(**self._config.get('database', {}))
        self.aggregator = Aggregator(**self._config.get('aggregator', {}))
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
        root_level = logging.NOTSET
        enabled_levels = []
        if self.logging_config.console_output.enabled:
            enabled_levels.append(self.logging_config.console_output.level)
        if self.logging_config.file_output.enabled:
            enabled_levels.append(self.logging_config.file_output.level)
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
            console_handler.setLevel(self.logging_config.console_output.level)
            logger.addHandler(console_handler)

        # Add CSV file handler if enabled
        if self.logging_config.file_output.enabled:
            if self.mode:
                file_path = os.path.join(
                    self.logging_config.file_output.log_dir,
                    self.logging_config.file_output.filename + "-" + self.mode + datetime.now().strftime("-%Y%m%d.csv")
                )
            else:
                file_path = os.path.join(
                    self.logging_config.file_output.log_dir,
                    self.logging_config.file_output.filename + datetime.now().strftime("-%Y%m%d.csv")
                )
            
            # Define CSV field names
            fieldnames = ['asctime', 'levelname', 'name', 'message', 'pathname', 'lineno']

            # Add CSV file handler
            csv_handler = CsvFileHandler(file_path, fieldnames, self.logging_config.file_output.date_format)
            csv_handler.setLevel(self.logging_config.file_output.level)
            logger.addHandler(csv_handler)

        return logger


class CsvFileHandler(logging.Handler):
    def __init__(self, file_path, fieldnames, datefmt=None):
        super().__init__()
        self.file_path = file_path
        self.fieldnames = fieldnames
        self.datefmt = datefmt

        # Open the CSV file in append mode
        self.csv_file = open(self.file_path, mode='a', newline='', encoding='utf-8')
        self.csv_writer = csv.DictWriter(self.csv_file, fieldnames=self.fieldnames)

        # Write the header only if the file is empty
        if os.stat(self.file_path).st_size == 0:
            self.csv_writer.writeheader()

    def emit(self, record):
        record.asctime = self.formatTime(record)
        # Convert the log record into a dictionary for CSV
        log_entry = {field: getattr(record, field, '') for field in self.fieldnames}
        self.csv_writer.writerow(log_entry)
        self.csv_file.flush()  # Ensure data is written immediately to the file

    def formatTime(self, record):
        # Format the record creation time
        ct = datetime.fromtimestamp(record.created)
        if self.datefmt:
            return ct.strftime(self.datefmt)
        return ct.isoformat()
    
    def close(self):
        self.acquire()
        try:
            if self.csv_file:
                self.csv_file.close()
            super().close()
        finally:
            self.release()
