from flask import Flask
import logging
import colorlog
import sys
from lib_config.config import Config
from sqlalchemy import create_engine

class Application:
    def __init__(self, logger):
        self.config = Config(__file__)
        self.logger = logger
        self.webserver = Flask(__name__)
        self.setup_routes()
        self.engine = create_engine(self.config.database.connection_string)
        self.logger.debug("Server application initialised")
    
    def setup_routes(self):
        self.webserver.route("/hello", methods=['GET'])(self.hello_world)

    def hello_world(self):
        self.logger.info("Hello world called")
        return {'message': 'Hello world from data reading web server'}
    
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