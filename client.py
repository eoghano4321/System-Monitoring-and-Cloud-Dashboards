import logging
import psutil
import sys
import threading
import socket
from lib_config.config import Config
from systemMetrics import DTO_Metric, DTO_DataSnapshot
from uuid import UUID
from metricsAPI import *
import time

class Application:
    def __init__(self, logger):
        self.config = Config(__file__)
        self.name = socket.gethostname()
        self.agg_id = UUID("49ceb0f4-3d61-4e7b-a9e0-066140caf7ca")
        self.logger = logger
        self.logger.debug("Client application initialised")

    def monitorSystemUsage(self):
        try:
            thread_count = threading.active_count()
            self.logger.debug(f"Active threads: {thread_count}")
            
            # Get RAM usage
            ram_usage = psutil.virtual_memory()
            ram_used_percentage = ram_usage.percent
            ram_used_mb = ram_usage.used / (1024 ** 2)  # Convert bytes to MB
            ram_total_mb = ram_usage.total / (1024 ** 2)  # Convert bytes to MB
            self.logger.debug(f"Ram used: {ram_used_mb}MB out of {ram_total_mb}MB ({ram_used_percentage})")

            # Create an instance of SystemMetrics
            thread_count_metric = DTO_Metric(
                name="thread_count",
                value=float(thread_count)
            )
            ram_used_mb_metric = DTO_Metric(
                name="ram_used_mb",
                value=float(ram_used_mb)
            )

            ram_used_perc_metric = DTO_Metric(
                name="ram_used_percentage",
                value=float(ram_used_percentage)
            )

            metrics = list([thread_count_metric, ram_used_mb_metric, ram_used_perc_metric])

            snapshot = DTO_DataSnapshot(
                metrics=metrics
            )

            return snapshot
        except Exception as e:
            self.logger.error(f"An error occurred while monitoring system usage: {e}")
            return 1


    def run(self) -> int:
        try:
            self.logger.info("Starting client pointing at port %s", self.config.web.port)
            self.logger.info("Application completed successfully")
            i = 0
            metricsSDK = MetricsApi()
            while i < 2000:
                snapshot = self.monitorSystemUsage()
                if snapshot == 1:
                    self.logger.exception("System reading failed")
                    return 1
                self.logger.info("Snapshot created successfully: %s", snapshot)
                device = metricsSDK.aggregateSnapshots(self.name, snapshot)
                aggregator = metricsSDK.aggregateDevices(self.agg_id, self.name, device)
                request = metricsSDK.uploadMetrics(aggregator)
                
                self.logger.info("Loop: %s", i)
                time.sleep(0.5)
                i += 1
            return 0
        except Exception as e:
            self.logger.exception("Application failed with error: %s", str(e))
            return 1

    def debug(self) -> int:
        self.logger.info("Entering client in debug mode")
        snapshot = self.monitorSystemUsage()
        if snapshot == 1:
                    self.logger.exception("System reading failed")
                    return 1
        self.logger.info("A single reading of system metrics: %s", snapshot)
        self.logger.info("Checking server status")
        metricsSDK = MetricsApi()
        metricsSDK.testServerLive()



if __name__ == "__main__":
    app = Application(logging.getLogger())
    sys.exit(app.debug())