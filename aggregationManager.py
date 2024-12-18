import logging
from systemMetrics import DTO_Aggregator, DTO_DataSnapshot, DTO_Device


class aggregationManager:
    logger = logging.getLogger()
    def __init__(self):
        self.snapshots = list()
        self.devices = list()
    
    def addSnapshotToAggregator(self, snapshot:DTO_DataSnapshot, name):
        if not snapshot.device_name:
            snapshot.device_name = name
        self.snapshots.append(snapshot)

    def addDeviceToAggregator(self, device:DTO_Device):
        self.devices.append(device)
    
    def getAggregatedSnapshotsForDevice(self, name):
        snapshotsForDevice = list()
        for snapshot in self.snapshots:
            if snapshot.device_name == name:
                snapshotsForDevice.append(snapshot)
        device = DTO_Device(
            name,
            data_snapshots=snapshotsForDevice
        )
        return device

    
    def getAggregatedDevices(self, platform_id, name):
        aggregator = DTO_Aggregator(
            platform_uuid=platform_id,
            name=name,
            devices=self.devices
        )
        self.logger.debug("Aggregator: %s", aggregator)
        return aggregator