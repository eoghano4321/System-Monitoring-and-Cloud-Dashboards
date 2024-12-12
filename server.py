from flask import Flask, request
import logging
import sys
import sqlite3
from sqlalchemy.orm import Session
from sqlalchemy.inspection import inspect
from models import *
from lib_config.config import Config
from sqlalchemy import create_engine
from dataclasses import dataclass
from systemMetrics import DTO_Aggregator
from datetime import datetime, UTC
from dashboard import Dashboard

@dataclass
class SQLSystemMetric:
    metric_id: int
    system_id: int
    metrics: str

class CursorManager:
    def __init__(self, cursor: sqlite3.Cursor):
        self.cursor = cursor

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.cursor.close()

class Application:
    def __init__(self, logger):
        self.config = Config(__file__)
        self.sqllite_file = self.config.database.connection_string.split('sqlite:///')[1]
        self.logger = logger
        self.webserver = Flask(__name__)
        self.engine = create_engine(self.config.database.connection_string)
        dashboard = Dashboard()
        self.dash_app = dashboard.create_dash_app(self.webserver, self.engine)
        self.setup_routes()
        self.create_tables()
        self.logger.debug("Server application initialised")

    def create_tables(self):
        """Ensure tables exist in the SQLite database."""
        Base.metadata.create_all(self.engine)
        self.logger.info("Tables created (if they didn't already exist)")

    def setup_routes(self):
        self.webserver.route("/hello", methods=['GET'])(self.helloWorld)
        self.webserver.route("/metrics", methods=['POST'])(self.uploadMetrics)
        self.webserver.route("/dashboards", methods=['GET'])(self.displayMetrics)

    def helloWorld(self):
        self.logger.info("Hello world called")
        return {'message': 'Hello world from data reading web server'}

    def uploadMetrics(self):
        session = None
        try:
            data = request.get_json()
            self.logger.info("Upload metrics called")
            dto_aggregator = DTO_Aggregator.from_dict(data)
            self.logger.info("JSON Deserialized. Storing aggregator snapshot: %s", dto_aggregator)
            session = Session(self.engine)

            aggregator = session.query(Aggregator).filter_by(guid=str(dto_aggregator.platform_uuid)).first()
            if not aggregator:
                aggregator = Aggregator(
                    guid=str(dto_aggregator.platform_uuid),
                    name=dto_aggregator.name
                )
                session.add(aggregator)
                session.flush()

            for dto_device in dto_aggregator.devices:
                device = session.query(Device).filter_by(
                    aggregator_id=aggregator.aggregator_id,
                    name=dto_device.name
                ).first()

                if not device:
                    device = Device(
                        aggregator_id=aggregator.aggregator_id,
                        name=dto_device.name
                    )
                    session.add(device)
                    session.flush()

                now_UTC = datetime.now(UTC)

                for dto_snapshot in dto_device.data_snapshots:
                    snapshot = SystemMetricSnapshot(
                        device_id=device.device_id,
                        client_utc_timestamp_epoch=int(dto_snapshot.timestamp_utc.timestamp()),
                        server_utc_timestamp_epoch=int(now_UTC.timestamp())
                    )
                    session.add(snapshot)
                    session.flush()

                    for dto_metric in dto_snapshot.metrics:
                        metric_type = session.query(MetricType).filter_by(
                            device_id=device.device_id,
                            metric_type=dto_metric.name
                        ).first()
                        self.logger.info("TYPE: %s for %s %s", metric_type, device.device_id, device.name)

                        if not metric_type:
                            metric_type = MetricType(
                                device_id=device.device_id,
                                metric_type=dto_metric.name
                            )
                            session.add(metric_type)
                            session.flush()

                        device_metric_value = SystemMetricValue(
                            metric_snapshot_id=snapshot.metric_snapshot_id,
                            metric_type_id=metric_type.metric_type_id,
                            metric_value=float(dto_metric.value)
                        )
                        session.add(device_metric_value)

                        self.logger.info("Uploaded: %s %s", device_metric_value.metric_type_id, device_metric_value.metric_value) 


            session.commit()
            session.close()

            return {
                'status': 'success',
                'message': 'Metric uploaded successfully'
            }, 201
        except Exception as e:
            if session is not None:
                self.logger.error("Rolling back session due to error: %s", str(e))
                try:
                    session.rollback()
                    session.close()
                except Exception as e:
                    self.logger.exception("Error rolling back session: %s", str(e))

            self.logger.exception("Error in upload_snapshot route: %s", str(e))
            return {
                'status': 'error',
                'message': str(e)
            }, 500

    def displayMetrics(self):
        self.logger.info("Redirecting to Dash app")
        return self.dash_app.index()

    def run(self) -> int:
        try:
            self.logger.info("Starting Flask web server on port %s", self.config.web.port)
            self.webserver.run(debug=self.config.web.debug, port=self.config.web.port)
            self.logger.info("Application completed successfully")
            return 0
        except Exception as e:
            self.logger.exception("Application failed with error: %s", str(e))
            return 1

    def debug(self) -> int:
        self.logger.info("Entering server in debug mode")

def debug() -> int:
    app = Application(logging.getLogger(__name__))
    return app.debug()

if __name__ == "__main__":
    sys.exit(debug())