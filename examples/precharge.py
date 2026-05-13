import logging
import os
import sys
import time
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pplapp import Pplapp

# -- Configuration ------------------------------------------------------------
STARTUP_DELAY_S = 5
CONTROL_LOOP_INTERVAL_S = 5

# -- Logging ------------------------------------------------------------------
log = logging.getLogger("precharge")
log.setLevel(logging.INFO)
formatter = logging.Formatter(
    fmt="[%(asctime)s] %(levelname)s %(name)s %(message)s",
    datefmt="%d.%m.%Y %H:%M:%S",
)
consoleHandler = logging.StreamHandler()
consoleHandler.setFormatter(formatter)
log.addHandler(consoleHandler)

batteryId = "battery1"
converterId = "converter1"

batteryPort = "port2" # battery port indicates the port on the converter to which the battery is connected
voltageThreshold = 3 # voltage threshold indicates the acceptable deviation from the battery voltage during precharge

class Precharge:
    def __init__(self, app):
        self.app = app
        self.state = "initializing"

    # Main function:
    def execute(self):
        '''
        This is a state machine that performs the precharge sequence. The sequence consists of the following steps:
        1. Configure the converter battery port to constant-voltage mode.
        2. Set the voltage of the converter port to the battery voltage.
        3. Close the contactor to connect the battery to the converter.
        4. Disable the battery port.
        Fault handling is also included in the state machine to reset faults and restart the precharge sequence.
        '''
        try:
            if self.state == "initializing":
                self.state = "configuringConverter"

            elif self.state == "configuringConverter":
                # Set the battery port to constant-voltage mode
                method = "constant-voltage"
                self.configureConverter(batteryPort, method)
                
                # Get the current method configured on the battery port
                batteryPortMethod = self.app.getMeasurements(converterId, f"measure.ports.{batteryPort}.method")

                # Check if the battery port method is set correctly
                if batteryPortMethod == method:
                    self.state = "precharging"

            elif self.state == "precharging":
                # Set the voltage of the battery port to the battery voltage
                batteryVoltage = float(self.app.getMeasurements(batteryId, "measure.ports.port1.voltage"))
                self.setVoltage(batteryPort, batteryVoltage)

                # Get the voltage of the battery port
                batteryPortVoltage = float(self.app.getMeasurements(converterId, f"measure.ports.{batteryPort}.voltage"))
                
                # Check if the battery port voltage is within the acceptable deviation from the battery voltage
                if batteryVoltage - voltageThreshold < batteryPortVoltage < batteryVoltage + voltageThreshold:
                    self.state = "closingContactor"

            elif self.state == "closingContactor":
                # Close the contactor to connect the battery to the converter
                self.closeContactor()

                # Get the state of the contactor
                contactorState = self.app.getMeasurements(batteryId, "measure.ports.port1.contactor")

                # Check if the contactor is closed
                if contactorState == "close":
                    self.state = "disablingBatteryPort"

            elif self.state == "disablingBatteryPort":
                # Set the battery port to disabled mode
                method = "idle"
                self.configureConverter(batteryPort, method)

                # Get the current method configured on the battery port
                batteryPortMethod = self.app.getMeasurements(converterId, f"measure.ports.{batteryPort}.method")

                # Check if the battery port method is set correctly
                if batteryPortMethod == method:
                    self.state = "completed"

            elif self.state == "completed":
                log.info("Precharge complete")

            elif self.state == "handlingFault":
                # Reset the active faults on the converter
                self.resetFaults()

                if not self.activeFaults():
                    self.state = "initializing"

            if self.activeFaults():
                self.state = "handlingFault"
        
        except Exception as e:
            log.exception("Error in precharge execution: %s", e)

    # Helper functions:
    def configureConverter(self, port, method):
        commands = {f"control.ports.{port}.method": method}
        self.app.setCommands(converterId, commands)

    def setVoltage(self, port, voltage):
        commands = {f"control.ports.{port}.voltage": str(voltage)}
        self.app.setCommands(converterId, commands)

    def closeContactor(self):
        commands = {"control.ports.port1.contactor": "close"}
        self.app.setCommands(batteryId, commands)

    def activeFaults(self):
        registers = ["fault.active.0", "fault.active.1", "fault.active.2", "fault.active.3"]
        for register in registers:
            if self.app.getMeasurements(converterId, register):
                return True
        return False

    def resetFaults(self):
        commands = {"control.reset": "1"}
        self.app.setCommands(converterId, commands)

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

    precharge = Precharge(app)

    try:
        while True:
            try:
                precharge.execute()
            except Exception as e:
                log.exception("Error in control loop: %s", e)
            time.sleep(CONTROL_LOOP_INTERVAL_S)

    except KeyboardInterrupt:
        log.info("Shutdown requested")
        precharge.configureConverter(batteryPort, "disabled")
        app.stop()
        log.info("Clean shutdown complete")


if __name__ == "__main__":
    main()