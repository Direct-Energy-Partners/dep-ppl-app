import time
from pplapp import Pplapp
from dotenv import load_dotenv
import os

load_dotenv()

# Constants:
startupDelay = 5
executionDelay = 5

def processMeasurements(app):
    measurements = app.getAllMeasurements()
    
    for deviceId, measurement in measurements.items():
        state = measurement.get("state", "unknown")
        print(f"Device ID: {deviceId} - State: {state}")

    print("-----------------------------")

def main():
    try:
        ipAddress = os.getenv("IP_ADDRESS")
        username = os.getenv("NATS_USERNAME")
        password = os.getenv("NATS_PASSWORD")

        if not username or not password:
            raise ValueError("NATS username or password not set in environment variables")

        app = Pplapp(ipAddress, username, password)

        time.sleep(startupDelay)

        while True:
            processMeasurements(app)
            time.sleep(executionDelay)

    except Exception as e:
        print(f"Failed to initialize PMS: {e}")

    except KeyboardInterrupt:
        print("Exiting program")
        app.connectToNats = False

if __name__ == "__main__":
    main()