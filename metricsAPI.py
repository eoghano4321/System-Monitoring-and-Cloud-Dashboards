import logging
from systemMetrics import DTO_Aggregator
import requests
from collections import deque

class MetricsApi:
    def __init__(self, config, logger):
        self.snapshot_queue = deque()
        self.config = config
        self.logger = logger

    def uploadMetrics(self, aggregator: DTO_Aggregator):
        criticalDevices = []
        self.logger.debug("Aggregated devices: %s", aggregator.to_dict())
        self.snapshot_queue.append(aggregator.to_dict())
        self.logger.info("Current upload queue size: %s", len(self.snapshot_queue))
        while self.snapshot_queue: # TODO: Maybe turn this into another function called flush that can be called by a different thread
            snapshot = self.snapshot_queue.popleft()
            try:
                endpoint = f"{self.config.web.host}:{self.config.web.port}/metrics"
                response = requests.post(endpoint, json=snapshot) 
                if response.status_code == 201:
                    try:
                        response_data = response.json()  # Parse the response as JSON
                        self.logger.debug(response_data)
                        critical_devices = response_data.get("criticalDevices", [])
                        if critical_devices:
                            criticalDevices.extend(critical_devices)  # Add to the list
                    except ValueError as e:
                        self.logger.error("Failed to parse response JSON: %s", e)
                else:
                    self.logger.error("Failed to upload snapshot, status code: %s, response: %s", response.status_code, response.text)
                    self.snapshot_queue.appendleft(snapshot)
                    return []
            except Exception as e:
                self.logger.error("Failed to upload snapshot: %s", e)
                self.snapshot_queue.appendleft(snapshot)
                return []
        self.logger.info("All snapshots in upload queue uploaded successfully")
        return criticalDevices
    
    def testServerLive(self):
        try:
            endpoint = self.config.web.host + ":" + str(self.config.web.port) + "/hello"
            response = requests.get(endpoint)
            if response.status_code == 200:
                self.logger.info("Server is live")
                return 0
            else:
                self.logger.error("Server failed to respond, status code: %s, response: %s", response.status_code, response.text)
                return 1
        except Exception as e:
                self.logger.error("Failed to connect to server: %s", e)
                return 1
