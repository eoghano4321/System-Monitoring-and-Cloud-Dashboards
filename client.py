import logging
import sys
import socket
from aggregationManager import *
from lib_config.config import Config
from uuid import UUID
from metricsAPI import *
import time
from localMonitor import *
from remoteMonitor import *

class Application:
    def __init__(self, logger):
        self.config = Config(script_path=__file__, run_type="client")
        self.name = socket.gethostname()
        self.agg_id = UUID(self.config.aggregator.agg_id)
        self.logger = logger
        self.logger.debug("Client application initialised")
        self.localMonitor = localMonitor(self.logger)
        self.remoteMonitor = remoteMonitor(self.logger)


    def run(self) -> int:
        try:
            self.logger.info("Starting client pointing at port %s", self.config.web.port)
            self.logger.info("Application completed successfully")
            metricsSDK = MetricsApi(self.config, self.logger)
            # TODO: Have this run in a thread and monitoring systems run separate so that multiple snapshots can potentially be sent per request
            while True: # Loop until user exits
                aggregator = aggregationManager()
                # espAggregator = aggregationManager()
                localsnapshot = self.localMonitor.monitorSystemUsage()
                if localsnapshot == 1:
                    self.logger.exception("System reading failed")
                    return 1
                aggregator.addSnapshotToAggregator(localsnapshot, self.name)
                localdevice = aggregator.getAggregatedSnapshotsForDevice(self.name)
                aggregator.addDeviceToAggregator(localdevice)
                
                esp32_snapshots = self.remoteMonitor.processEsp32Metrics()
                if esp32_snapshots:
                    for esp32_snapshot in esp32_snapshots:
                        aggregator.addSnapshotToAggregator(esp32_snapshot, esp32_snapshot.device_name)
                        esp32Device = aggregator.getAggregatedSnapshotsForDevice(esp32_snapshot.device_name)
                        aggregator.addDeviceToAggregator(esp32Device)
                
                aggregatedDevices = aggregator.getAggregatedDevices(self.agg_id, self.name)
                self.logger.debug("Aggregated devices: %s", aggregatedDevices)
                request = metricsSDK.uploadMetrics(aggregatedDevices)
                if len(request) > 0:
                    self.logger.info(request)
                    for device in request:
                        if device == self.name:
                            self.logger.critical("Simulating system reboot...")
                        else:
                            self.remoteMonitor.respondCriticalToEsp32(device)
                
                time.sleep(0.5) # Sleep to not overload the server
        except Exception as e:
            self.logger.exception("Application failed with error: %s", str(e))
            return 1

    def debug(self) -> int:
        self.logger.info("Entering client in debug mode")
        snapshot = self.localMonitor.monitorSystemUsage()
        if snapshot == 1:
            self.logger.exception("System reading failed")
            return 1
        self.logger.info("A single reading of system metrics: %s", snapshot)
        self.logger.info("Checking server status")
        metricsSDK = MetricsApi(self.config, self.logger)
        metricsSDK.testServerLive()



if __name__ == "__main__":
    app = Application(logging.getLogger())
    sys.exit(app.debug())