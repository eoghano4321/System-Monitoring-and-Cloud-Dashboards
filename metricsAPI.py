import logging
from systemMetrics import DTO_DataSnapshot, DTO_Device, DTO_Aggregator
import requests
from collections import deque

class MetricsApi:
    logger = logging.getLogger()
    def __init__(self):
        self.snapshot_queue = deque()
    
    def aggregateSnapshots(self, name, snapshot: DTO_DataSnapshot):
        device = DTO_Device(
            name,
            data_snapshots=list([snapshot])
        )
        return device
    
    def aggregateDevices(self, platform_id, name, device: DTO_Device):
        self.logger.debug("Collected snapshots for device: %s", device)
        aggregator = DTO_Aggregator(
            platform_uuid=platform_id,
            name=name,
            devices=list([device])
        )
        self.logger.debug("Aggregator: %s", aggregator)
        return aggregator


    def uploadMetrics(self, aggregator: DTO_Aggregator):     
        self.logger.debug("Aggregated devices: %s", aggregator.to_dict())
        self.snapshot_queue.append(aggregator.to_dict())
        self.logger.info("Current upload queue size: %s", len(self.snapshot_queue))
        while self.snapshot_queue: # TODO: Maybe turn this into another function called flush that can be called by a different thread
            snapshot = self.snapshot_queue.popleft()
            try:
                response = requests.post("http://localhost:5656/metrics", json=snapshot)
                if response.status_code == 201:
                    self.logger.info("Snapshot uploaded successfully")
                else:
                    self.logger.error("Failed to upload snapshot, status code: %s, response: %s", response.status_code, response.text)
                    self.snapshot_queue.appendleft(snapshot)
                    return 1
            except Exception as e:
                self.logger.error("Failed to upload snapshot: %s", e)
                self.snapshot_queue.appendleft(snapshot)
                return 1
        self.logger.info("All snapshots in upload queue uploaded successfully")
        return 0
    
    def testServerLive(self):
        try:
            response = requests.get("http://localhost:5656/hello")
            if response.status_code == 200:
                self.logger.info("Server is live")
                return 0
            else:
                self.logger.error("Server failed to respond, status code: %s, response: %s", response.status_code, response.text)
                return 1
        except Exception as e:
                self.logger.error("Failed to connect to server: %s", e)
                return 1
