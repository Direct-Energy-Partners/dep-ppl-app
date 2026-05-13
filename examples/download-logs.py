import logging
import os
import sys
import time
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pplapp import Pplapp

# -- Configuration ------------------------------------------------------------
STARTUP_DELAY_S = 5

# -- Logging ------------------------------------------------------------------
log = logging.getLogger("download-logs")
log.setLevel(logging.INFO)
formatter = logging.Formatter(
    fmt="[%(asctime)s] %(levelname)s %(name)s %(message)s",
    datefmt="%d.%m.%Y %H:%M:%S",
)
consoleHandler = logging.StreamHandler()
consoleHandler.setFormatter(formatter)
log.addHandler(consoleHandler)

# -- Main Application Logic ---------------------------------------------------
def main() -> None:
    load_dotenv()

    ipAddress = os.getenv("IP_ADDRESS")
    username = os.getenv("NATS_USERNAME")
    password = os.getenv("NATS_PASSWORD")

    if not ipAddress or not username or not password:
        log.error("IP_ADDRESS, NATS_USERNAME, and NATS_PASSWORD must be set in .env")
        sys.exit(1)

    log.info("Connecting to PPL controller at %s", ipAddress)
    app = Pplapp(ipAddress, username, password)

    time.sleep(STARTUP_DELAY_S)

    try:
        app.getLogs()
    except Exception as e:
        log.exception("Failed to download log files: %s", e)
    finally:
        app.stop()
        log.info("Clean shutdown complete")


if __name__ == "__main__":
    main()