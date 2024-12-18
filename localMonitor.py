import threading
import psutil
from systemMetrics import *


class localMonitor:
    def __init__(self, logger):
        self.logger = logger

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
                value=float(thread_count),
                threshold=None
            )
            ram_used_mb_metric = DTO_Metric(
                name="ram_used_mb",
                value=float(ram_used_mb),
                threshold=ram_total_mb*0.8
            )

            ram_used_perc_metric = DTO_Metric(
                name="ram_used_percentage",
                value=float(ram_used_percentage),
                threshold=80.0
            )

            metrics = list([thread_count_metric, ram_used_mb_metric, ram_used_perc_metric])

            snapshot = DTO_DataSnapshot(
                metrics=metrics,
                timestamp_utc=datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
            )

            return snapshot
        except Exception as e:
            self.logger.error(f"An error occurred while monitoring system usage: {e}")
            return 1