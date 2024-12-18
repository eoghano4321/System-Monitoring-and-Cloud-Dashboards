from datetime import datetime
import json
import socket
import threading

from lib_config.config import Config
from systemMetrics import DTO_DataSnapshot, DTO_Metric

class remoteMonitor:
    def __init__(self, logger):
        self.config = Config(__file__, run_type="client")
        self.logger = logger
        self.esp32_metrics = {}
        self.device_connections = {}

        # Start the ESP32 socket server in a separate thread
        threading.Thread(target=self.startEsp32SocketServer, daemon=True).start()

    def startEsp32SocketServer(self):
        """Start a raw socket server to listen for ESP32 metrics."""
        self.logger.info(f"Starting ESP32 socket server on {self.config.client.socket_host}:{self.config.client.socket_port}")
        try:
            server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_sock.bind((self.config.client.socket_host, self.config.client.socket_port))
            server_sock.listen(5)
            while True:
                conn, addr = server_sock.accept()
                threading.Thread(target=self.handleEsp32Connection, args=(conn, addr)).start()
        except Exception as e:
            self.logger.error(f"Error in ESP32 socket server: {e}")
    

    def handleEsp32Connection(self, conn, addr):
        """Handle an incoming connection from ESP32."""
        self.logger.info(f"Connection established with ESP32 at {addr}")
        try:
            while True:  # Keep the connection open
                data = conn.recv(1024)  # Receive raw binary data
                if not data:  # Connection closed by the client
                    self.logger.info(f"Connection closed by ESP32 at {addr}")
                    break

                self.logger.debug(f"Raw data received: {data}")

                # Parse the custom protocol
                metrics, device_name = self.parseCustomProtocol(data)
                with threading.Lock():
                    if device_name not in self.esp32_metrics:
                        self.device_connections[device_name] = conn
                        self.esp32_metrics[device_name] = []
                    self.esp32_metrics[device_name].append(metrics)
                self.logger.info(f"Device name: {device_name}, Metrics: {metrics}")

                conn.sendall(b"Metrics received")  # Acknowledge
        except Exception as e:
            self.logger.error(f"Error handling ESP32 connection: {e}")
        finally:
            self.device_connections.pop(device_name, None)  # Remove the connection
            conn.close()



    def parseCustomProtocol(self, data):
        """
        Parse the custom protocol received from ESP32.

        Protocol structure:
        - 4 bytes: Length of the metrics payload (big-endian integer)
        - Null-terminated string: Device name
        - Remaining bytes: Metrics payload (JSON string)
        """
        try:
            # Extract the length of the metrics payload
            metrics_length = int.from_bytes(data[:4], byteorder='big')
            self.logger.debug(f"Metrics length: {metrics_length}")

            # Find the null-terminated device name
            null_terminator_index = data.find(b'\x00', 4)
            if null_terminator_index == -1:
                raise ValueError("Invalid protocol: Missing null terminator for device name")
            
            # Extract the device name
            device_name = data[4:null_terminator_index].decode()
            self.logger.debug(f"Device name: {device_name}")

            # Extract the metrics payload
            metrics_start_index = null_terminator_index + 1
            metrics_payload = data[metrics_start_index:metrics_start_index + metrics_length].decode()
            metrics = json.loads(metrics_payload)  # Parse the JSON metrics
            return metrics, device_name
        except Exception as e:
            self.logger.error(f"Error parsing custom protocol: {e}")
            raise

    def processEsp32Metrics(self):
        """Convert collected ESP32 metrics into DTO_Metric objects for all connected devices."""
        try:
            snapshots = []  # List to hold snapshots for all devices

            # Iterate over each device in the metrics dictionary
            with threading.Lock():  # Ensure thread-safe access to self.esp32_metrics
                for device_name, metrics_list in self.esp32_metrics.items():
                    device_metrics = []  # Collect metrics for the current device

                    while metrics_list:
                        raw_metric = metrics_list.pop(0)  # Get and remove the oldest metric
                        metric_time = datetime.now().isoformat()
                        for key, value in raw_metric.items():
                            if key == "timestamp":
                                metric_time = datetime.fromisoformat(raw_metric["timestamp"]).isoformat()
                            else:
                                if value.get("threshold"):
                                    device_metrics.append(DTO_Metric(name=key, value=float(value.get("value")), threshold=float(value.get("threshold"))))
                                else:
                                    device_metrics.append(DTO_Metric(name=key, value=float(value.get("value"))))

                        if device_metrics:
                            snapshot = DTO_DataSnapshot(
                                metrics=device_metrics,
                                timestamp_utc=metric_time,
                                device_name=device_name 
                            )
                            self.logger.info(f"Created ESP32 snapshot for device {device_name}: {snapshot}")
                            snapshots.append(snapshot)

            return snapshots if snapshots else None  # Return the list of snapshots or None if empty
        except Exception as e:
            self.logger.error(f"Error processing ESP32 metrics: {e}")
            return None
    
    def respondCriticalToEsp32(self, device_name):
        """Send a reboot message to the specified ESP32 device."""
        try:
            # Check if the device connection exists
            if device_name not in self.device_connections:
                self.logger.error(f"No active connection for device {device_name}")
                return
            
            conn = self.device_connections[device_name]

            # Send the reboot command
            conn.sendall(b"REBOOT")
            self.logger.info(f"Sent reboot command to device {device_name}")
        except Exception as e:
            self.logger.error(f"Failed to send reboot command to {device_name}: {e}")

