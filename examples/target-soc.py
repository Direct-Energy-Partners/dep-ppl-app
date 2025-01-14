import time
from pplapp import Pplapp
from dotenv import load_dotenv
import os

load_dotenv()

# Constants:
startupDelay = 5
executionDelay = 5

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

    powerSetpoint = limit(powerSetpoint, -batteryChargePowerMax, -batteryDischargePowerMax)

    setPower(app, powerSetpoint)

    print(f"Battery SOC: {soc}% - Target SOC: {targetSoc}%")
    print("Power Setpoint: " + str(powerSetpoint) + "W")

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
        f"control.ports.port{batteryPortNumber}.method": "disabled",
        f"control.ports.port{batteryPortNumber}.power": str(0)
    }
    app.setCommands(converterId, commands)

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
            batteryTargetSOC(app)
            time.sleep(executionDelay)

    except Exception as e:
        print(f"Failed to initialize battery Target SOC: {e}")

    except KeyboardInterrupt:
        disableBatteryPort(app)

        time.sleep(executionDelay)

        app.connectToNats = False

if __name__ == "__main__":
    main()