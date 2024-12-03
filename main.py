import argparse
import sys
import logging
from lib_config.config import Config

class ApplicationHandler:
    def __init__(self):
        self.config = Config(__file__)
        self.logger = logging.getLogger()
        self.logger.info("Starting...")
        

    def run_server(self, host=None, port=None) -> int:
        """
        Import and run the server from server.py, optionally setting the port and host address
        """
        from server import Application

        # Create an instance of the Application and override the port if provided
        app = Application(self.logger)
        if port:
            app.config.web.port = port  # Override the port in the configuration
        if host:
            app.config.web.host = host
        
        self.logger.info(f"Server config set to {app.config.web.host or 'default IP'}:{app.config.web.port or 'default port'}")
        return app.run()  # Run the server and exit with its return code

    def run_client(self, host=None, port=None) -> int:
        """
        Import and run the server from server.py, optionally setting the port and host address
        """
        from client import Application

        # Create an instance of the Application and override the port if provided
        app = Application(self.logger)
        if port:
            app.config.web.port = port  # Override the port in the configuration
        if host:
            app.config.web.host = host
        
        return app.run()
    
    def entryPoint(self, args) -> int:
        # Validate port
        if args.port and (args.port < 1 or args.port > 65535):
            self.logger.error("Error: Port must be an integer between 1 and 65535.")
            return 1

        # Validate IP (basic validation, assumes IPv4 for simplicity)
        if args.ip:
            import socket
            try:
                socket.inet_aton(args.ip)
                self.logger.debug("IP is valid")
            except socket.error:
                self.logger.error("Error: Invalid IP address.")
                return 1

        # Check mode
        if args.client and args.server:
            self.logger.error("Error: You can only specify one mode, either --client or --server.")
            return 1
        elif args.client:
            self.logger.info(f"Starting client to point to {args.ip or 'default IP'}:{args.port or 'default port'}")
            return self.run_client(host=args.ip, port=args.port)
        elif args.server:
            self.logger.info(f"Starting server on {args.ip or 'default IP'}:{args.port or 'default port'}")
            return self.run_server(host=args.ip, port=args.port)
        else:
            self.logger.error("Error: You must specify either --client (-c) or --server (-s).")
            return 1

def main() -> int:
    appHandler = ApplicationHandler()
    # Create argument parser
    parser = argparse.ArgumentParser(description="Run TCP server or client.")
    parser.add_argument("-c", "--client", action="store_true", help="Run the client")
    parser.add_argument("-s", "--server", action="store_true", help="Run the server")
    parser.add_argument("-i", "--ip", type=str, help="Specify the IP address for the server")
    parser.add_argument("-p", "--port", type=int, help="Specify the port for the server")

    # Parse arguments
    args = parser.parse_args()
    return appHandler.entryPoint(args)

    

if __name__ == "__main__":
    sys.exit(main())
