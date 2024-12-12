"""
Library module for the data model for the metrics data. This is a pure
DTO data definition. The implementation of the logic to read and store metrics
is in the metrics_client_datamodel.py module.
"""

from datetime import datetime
from typing import List
from dataclasses import dataclass, field
from dataclasses_json import dataclass_json
import uuid            
import logging

@dataclass_json
@dataclass
class DTO_Metric:
    name: str
    value: float

@dataclass_json
@dataclass
class DTO_DataSnapshot:
    timestamp_utc: datetime = field(
        default_factory=datetime.now, 
        metadata={'dataclasses_json': {'encoder': lambda d: d.isoformat(),
                                       'decoder': datetime.fromisoformat}}  # Custom encoder for datetime
    )
    metrics: List[DTO_Metric] = field(default_factory=list)

    def to_dict(self):
        """Convert DTO_DataSnapshot to a dictionary for JSON serialization."""
        return {
            'timestamp_utc': self.timestamp_utc,  # Convert datetime to ISO format
            'metrics': [metric.to_dict() for metric in self.metrics]
        }

 
@dataclass_json
@dataclass 
class DTO_Device:
    name: str
    data_snapshots: List[DTO_DataSnapshot] = field(default_factory=list)
    def to_dict(self):
        """Convert DTO_Device to a dictionary for JSON serialization."""
        return {
            'name': self.name,
            'data_snapshots': [snapshot.to_dict() for snapshot in self.data_snapshots]
        }
    
@dataclass_json
@dataclass
class DTO_Aggregator:
    logger = logging.getLogger()
    logger.info("Test")
    platform_uuid: uuid.UUID = field(metadata={'dataclasses_json': {'encoder': str}})
    name: str
    devices: List[DTO_Device] = field(default_factory=list)


    def to_dict(self):
        """Convert DTO_Aggregator to a dictionary for JSON serialization."""
        return {
            'platform_uuid': str(self.platform_uuid),  # Convert UUID to string
            'name': self.name,
            'devices': [device.to_dict() for device in self.devices]
        }