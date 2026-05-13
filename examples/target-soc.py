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
log = logging.getLogger("target-soc")
log.setLevel(logging.INFO)
formatter = logging.Formatter(
    fmt="[%(asctime)s] %(levelname)s %(name)s %(message)s",
    datefmt="%d.%m.%Y %H:%M:%S",
)
consoleHandler = logging.StreamHandler()
consoleHandler.setFormatter(formatter)
log.addHandler(consoleHandler)

# Constants - Change these values to match your system:
POWER = 10000
MINSOC = 20
MAXSOC = 90
TARGETSOC = 75

batteryId = "battery1"
converterId = "converter1"
batteryPortNumber = 2

# Main function:
def batteryTargetSOC(app):
    # Check if target SOC is within limits
    targetSoc = limit(TARGETSOC, MINSOC, MAXSOC)

    # Battery reported State of Charge
    soc = int(float(app.getMeasurements(batteryId, "measure.ports.port1.soc")))

    if soc < targetSoc:
        powerSetpoint = -abs(POWER) # Charge the battery, need to set negative power setpoint to converter port
    elif soc > targetSoc:
        powerSetpoint = abs(POWER) # Discharge the battery, need to set positive power setpoint to converter port
    else:
        powerSetpoint = 0

    # Check if power setpoint is within limits of the converter
    converterImportPowerMax = int(app.getMeasurements(converterId, f"measure.ports.port{batteryPortNumber}.power.import.max"))
    converterExportPowerMax = int(app.getMeasurements(converterId, f"measure.ports.port{batteryPortNumber}.power.export.max"))

    powerSetpoint = limit(powerSetpoint, converterExportPowerMax, converterImportPowerMax)

    # Check if power setpoint is within limits of the battery
    batteryChargePowerMax = int(float(app.getMeasurements(batteryId, "measure.ports.port1.power.charge.max")))
    batteryDischargePowerMax = int(float(app.getMeasurements(batteryId, "measure.ports.port1.power.discharge.max")))

    powerSetpoint = limit(powerSetpoint, -batteryChargePowerMax, batteryDischargePowerMax)

    setPower(app, powerSetpoint)

    log.info("Battery SOC: %d%% - Target SOC: %d%%", soc, targetSoc)
    log.info("Power Setpoint: %dW", powerSetpoint)

# Helper functions:
def limit(setpoint, minimum, maximum):
    return max(min(setpoint, maximum), minimum)

def setPower(app, powerSetpoint):
    commands = {
        f"control.ports.port{batteryPortNumber}.method": "constant-power",
        f"control.ports.port{batteryPortNumber}.power": str(powerSetpoint)
    }
    app.setCommands(converterId, commands)

def disableBatteryPort(app):
    commands = {
        f"control.ports.port{batteryPortNumber}.method": "idle",
        f"control.ports.port{batteryPortNumber}.power": str(0)
    }
    app.setCommands(converterId, commands)

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
        while True:
            try:
                batteryTargetSOC(app)
            except Exception as e:
                log.exception("Error in control loop: %s", e)
            time.sleep(CONTROL_LOOP_INTERVAL_S)

    except KeyboardInterrupt:
        log.info("Shutdown requested")
        disableBatteryPort(app)
        app.stop()
        log.info("Clean shutdown complete")


if __name__ == "__main__":
    main()