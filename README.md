# Template
## Introduction
- Creating a web server to host cloud dashboards of device metrics
- Creating a client to take snapshots of device metrics and upload them to the cloud server

## Motivation
- Undertaken as part of the context of the code block of CS4447

## Instructions
- To run the server use ```python .\main.py -s``` to run in production mode and ```python .\server.py``` to run in debug mode
- To run the client use ```python .\main.py -c``` to run in production mode and ```python .\client.py``` to run in debug mode
- The port and host are configured in config.json but can be manually set using ```-p | --port``` and ```-i | --ip```
- The ESP32 device can connect to the device IP at port 5665
