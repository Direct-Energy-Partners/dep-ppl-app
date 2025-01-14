import time
from pplapp import Pplapp
from dotenv import load_dotenv
import os

load_dotenv()

# Constants:
startupDelay = 5
executionDelay = 5

def main():
    try:
        ipAddress = os.getenv("IP_ADDRESS")
        username = os.getenv("NATS_USERNAME")
        password = os.getenv("NATS_PASSWORD")

        if not username or not password:
            raise ValueError("NATS username or password not set in environment variables")

        app = Pplapp(ipAddress, username, password)

        time.sleep(startupDelay)

        app.getLogs()

        time.sleep(executionDelay)

        app.connectToNats = False

    except Exception as e:
        print(f"Failed to download log files: {e}")

    except KeyboardInterrupt:
        print("Exiting program")
        app.connectToNats = False

if __name__ == "__main__":
    main()