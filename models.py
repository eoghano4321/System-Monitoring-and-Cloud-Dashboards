from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Float
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
metadata = Base.metadata

class Aggregator(Base):
    __tablename__ = 'aggregators'

    aggregator_id = Column(Integer, primary_key=True)
    guid = Column(String, nullable=False)
    name = Column(String, nullable=False)

class SystemMetricSnapshot(Base):
    __tablename__ = 'system_metric_snapshots'

    metric_snapshot_id = Column(Integer, primary_key=True)
    device_id = Column(ForeignKey('devices.device_id'), nullable=False)
    client_utc_timestamp_epoch = Column(Integer, nullable=False)
    server_utc_timestamp_epoch =  Column(Integer, nullable=False)

    system_recorded = relationship('Device')

class Device(Base):
    __tablename__ = 'devices'

    aggregator_id = Column(ForeignKey('aggregators.aggregator_id'), nullable=False)
    device_id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)

    aggregator = relationship('Aggregator')

class MetricType(Base):
    __tablename__ = 'metric_types'

    metric_type_id = Column(Integer, primary_key=True)
    device_id = Column(ForeignKey('devices.device_id'), nullable=False)
    metric_type = Column(String, nullable=False)
    metric_threshold = Column(Float, nullable=True)
    
    device = relationship('Device')

class SystemMetricValue(Base):
    __tablename__ = 'metric_values'

    metric_id = Column(Integer, primary_key=True, nullable=False)
    metric_snapshot_id = Column(ForeignKey('system_metric_snapshots.metric_snapshot_id'), nullable=False)
    metric_type_id = Column(ForeignKey('metric_types.metric_type_id'), nullable=False)
    metric_value = Column(Float, nullable=False)

    device_type = relationship('MetricType')
    metric_snapshot = relationship('SystemMetricSnapshot')



