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
log = logging.getLogger("zero-grid-export")
log.setLevel(logging.INFO)
formatter = logging.Formatter(
    fmt="[%(asctime)s] %(levelname)s %(name)s %(message)s",
    datefmt="%d.%m.%Y %H:%M:%S",
)
consoleHandler = logging.StreamHandler()
consoleHandler.setFormatter(formatter)
log.addHandler(consoleHandler)

minSoc = 20
maxSoc = 90
socHysteresis = 2

batteryId = "battery1"
converterId = "converter1"
meterId = "acmeter1"

batteryPort = "port2" # battery port indicates the port on the converter to which the battery is connected

class ZeroGridExport:
    def __init__(self, app):
        self.app = app
        self.powerSetpoint = 0
        self.offset = 0

    def execute(self):
        try:
            gridPower = float(self.app.getMeasurements(meterId, "measure.ports.port1.power"))
            soc = int(float(self.app.getMeasurements(batteryId, "measure.ports.port1.soc")))

            self.powerSetpoint += gridPower

            if self.powerSetpoint >= 0:
                if soc > minSoc + self.offset:
                    self.offset = 0
                else:
                    self.powerSetpoint = 0
                    self.offset = socHysteresis

            elif self.powerSetpoint < 0:
                if soc < maxSoc - self.offset:
                    self.offset = 0
                else:
                    self.powerSetpoint = 0
                    self.offset = socHysteresis

            # Check if power setpoint is within limits of the converter
            converterImportPowerMax = int(self.app.getMeasurements(converterId, f"measure.ports.{batteryPort}.power.import.max"))
            converterExportPowerMax = int(self.app.getMeasurements(converterId, f"measure.ports.{batteryPort}.power.export.max"))

            self.powerSetpoint = self.limit(self.powerSetpoint, converterExportPowerMax, converterImportPowerMax)

            # Check if power setpoint is within limits of the battery
            batteryChargePowerMax = int(self.app.getMeasurements(batteryId, "measure.ports.port1.power.charge.max"))
            batteryDischargePowerMax = int(self.app.getMeasurements(batteryId, "measure.ports.port1.power.discharge.max"))

            self.powerSetpoint = self.limit(self.powerSetpoint, -batteryChargePowerMax, batteryDischargePowerMax)

            self.setPower(self.powerSetpoint)
        
        except Exception as e:
            log.exception("Error in zeroGridExport execution: %s", e)
    
    # Helper functions:
    def limit(self, setpoint, minimum, maximum):
        return max(min(setpoint, maximum), minimum)

    def setPower(self, setpoint):
        commands = {
            f"control.ports.{batteryPort}.method": "constant-power",
            f"control.ports.{batteryPort}.power": str(setpoint)
        }
        self.app.setCommands(converterId, commands)

    def disableBatteryPort(self):
        commands = {
            f"control.ports.{batteryPort}.method": "idle",
            f"control.ports.{batteryPort}.power": str(0)
        }
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

    zeroGridExport = ZeroGridExport(app)

    try:
        while True:
            try:
                zeroGridExport.execute()
            except Exception as e:
                log.exception("Error in control loop: %s", e)
            time.sleep(CONTROL_LOOP_INTERVAL_S)

    except KeyboardInterrupt:
        log.info("Shutdown requested")
        zeroGridExport.disableBatteryPort()
        app.stop()
        log.info("Clean shutdown complete")


if __name__ == "__main__":
    main()
