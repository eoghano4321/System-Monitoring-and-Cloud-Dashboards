import logging
import sys
from lib_config.config import Config

class Application:
    def __init__(self, logger):
        self.config = Config(__file__)
        self.logger = logger
        self.logger.debug("Client application initialised")
    
    def run(self) -> int:
        try:
            self.logger.info("Starting client pointing at port %s", self.config.web.port)
            self.logger.info("Application completed successfully")
            return 0
        except Exception as e:
            self.logger.exception("Application failed with error: %s", str(e))
            return 1
    
    def debug(self) -> int:
        self.logger.info("Entering client in debug mode")


def debug() -> int:
    app = Application(logging.getLogger(__name__))
    return app.debug()

if __name__ == "__main__":
    sys.exit(debug())