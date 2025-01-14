import time
from pplapp import Pplapp
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Constants:
startupDelay = 5
executionDelay = 5

# Main function:
def pms(app):
    pass

# Helper functions:
def function1():
    pass

def function2():
    pass

def function3():
    pass

# Main code that will create a NATS connection and run the PMS loop
def main():
    try:
        # Define the IP address of the controller, and username and password for the NATS connection
        ipAddress = os.getenv("IP_ADDRESS")
        username = os.getenv("NATS_USERNAME")
        password = os.getenv("NATS_PASSWORD")

        if not username or not password:
            raise ValueError("NATS username or password not set in environment variables")

        # Initialize the NATS connection to the controller
        app = Pplapp(ipAddress, username, password)

        time.sleep(startupDelay)

        # Run the PMS loop
        while True:
            pms(app)
            time.sleep(executionDelay)

    except Exception as e:
        print(f"Failed to initialize PMS: {e}")

    except KeyboardInterrupt:
        print("Exiting program")
        app.connectToNats = False

if __name__ == "__main__":
    main()