import time
from pplapp import Pplapp
from dotenv import load_dotenv
import os

load_dotenv()

# Constants
startupDelay = 5
executionDelay = 5

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
            print(f"Error in zeroGridExport execution: {e}")
    
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
            f"control.ports.{batteryPort}.method": "disabled",
            f"control.ports.{batteryPort}.power": str(0)
        }
        self.app.setCommands(converterId, commands)

def main():
    try:
        ipAddress = os.getenv("IP_ADDRESS")
        username = os.getenv("NATS_USERNAME")
        password = os.getenv("NATS_PASSWORD")

        if not username or not password:
            raise ValueError("NATS username or password not set in environment variables")

        app = Pplapp(ipAddress, username, password)

        time.sleep(startupDelay)

        zeroGridExport = ZeroGridExport(app)

        while True:
            zeroGridExport.execute()
            time.sleep(executionDelay)

    except Exception as e:
        print(f"Failed to initialize Zero Grid Export: {e}")

    except KeyboardInterrupt:
        zeroGridExport.disableBatteryPort()

        time.sleep(executionDelay)
        
        app.connectToNats = False

if __name__ == "__main__":
    main()
