from modules import cbpi
from modules.core.hardware import SensorPassive
from modules.core.step import StepBase
from modules.core.props import Property
from modules.core.props import Property, StepProperty

import Adafruit_ADS1x15

# TODO add requitment

@cbpi.sensor
class PressureSensor(SensorPassive):

    GRAVITY = 9.807
    #Gain == 1 mean measuring voltage of +/-4.096.
    #Gain 1 means +-4.096V
    VOLT = 4.096
    GAIN = 1
    PI = 3.1415
    voltLow = Property.Number("Voltage low", configurable=True, default_value=0, description="Pressure sensor minimal voltage. Usually 0")
    voltHigh = Property.Number("Voltage high", configurable=True, default_value=5, description="Pressure sensor minimal voltage. Usually 5")
    pressureLow = Property.Number("Pressure low", configurable=True, default_value=0, description="The pressure value at the minimal voltage. value in kPa")
    pressureHigh = Property.Number("Pressure high", configurable=True, default_value=6, description="The pressure value at the maxmimal voltage. value in kPa")
    sensorHight = Property.Number("Sensor hight", configurable=True, default_value=0, description="The offset of the sensor from the bottom of the kettle")
    kettleDia = Property.Number("Kettle dimammeter", configurable=True, description="The diameter of the sensor in milimiter")
    sensorType = Property.Select("sensor type", options=["Voltage", "Pressure", "Liquid Level", "Volume"], description="Select which type of data to register for this sensor")
    coefficientA = 0
    coefficientB = 0


    def init(self):
            unit = cbpi.get_config_parameter("pressure_sensor_unit", None)
            if not unit:
                    print "Init pressure sensor unit"
                    try:
                            cbpi.add_config_parameter("pressure_sensor_unit", "L", "select", "Pressure sensor liquid level", options=["L", "Gal", "qt"])
                    except:
                            bpi.notify("Pressure Sensor Error", "Unable to update database.", type="danger", timeout=None)

            self.coefficientA = (float(self.pressureHigh - self.pressureLow)) / ((float(self.voltHigh - self.voltLow)))
            self.coefficientB = (float)(self.coefficientA) * self.voltLow - self.pressureLow
            self.adc = Adafruit_ADS1x15.ADS1115()
            self.adc.start_adc(0, gain=self.GAIN)

    def stop(self):
        '''
        Stop the sensor. Is called when the sensor config is updated or the sensor is deleted
        :return:
        '''
        pass

    def convert_volume(self, volume):
            #Convert from Liters into QT/GAL
            unit = cbpi.get_config_parameter("pressure_sensor_unit", None)
            if unit == 'L':
                    return volume
            if unit == 'qt':
                    return float(volume) / 1.057
            if unit == 'Gal':
                    return float(volume) / 3.785

    def convert_hight(self, hight):
            unit = cbpi.get_config_parameter("pressure_sensor_unit", None)
            if unit == 'L':
                    return hight
            else:
                    return float(hight) / 2.54


    def get_unit(self):
        '''
        :return: Unit of the sensor as string. Should not be longer than 3 characters
        '''
        unit =  cbpi.get_config_parameter("pressure_sensor_unit", None)
        if self.sensorType == "Voltage":
            return "V"
        if self.sensorType == "Pressure":
            return "kPa"
        # TODO add option for inches
        if self.sensorType == "Liquid Level":
                if unit == 'L':
                        return "cm"
                else:
                        return "in"
        if self.sensorType == "Volume":
                return unit
        return "N/A"

    def read(self):
        value = self.adc.get_last_result()
	volt = value * self.VOLT / 32767
	pressure = self.coefficientA * volt + self.coefficientB

	#water level is calculated by H = P / (SG * G). Assume the SG of water is 1.000
        #This is true for water at 4deg (Cel)
	water_level = pressure / self.GRAVITY

	# Convert to cm and add the hight of the sensor
	water_level = water_level * 100 + self.sensorHight

	radious = float(self.kettleDia) / 20
	volume = (water_level * self.PI * radious * radious) / 1000
        output = 0
	if self.sensorType == "Voltage":
                output = volt
        if self.sensorType == "Pressure":
                output = pressure
        if self.sensorType == "Liquid Level":
                output = self.convert_hight(water_level)
        if self.sensorType == "Volume":
                output = self.convert_volume(volume)
        self.data_received("{0:.2f}".format(output))

@cbpi.step
class PressureSensor(StepBase):
    volume = Property.Number("volume", configurable=True)
    sensor = StepProperty.Sensor("Sensor")
    actor = StepProperty.Actor("Actor")

    def init(self):
        if self.actor is not None:
            self.actor_on(int(self.actor))

    @cbpi.action("Turn Actor OFF")
    def start(self):
            if self.actor is not None:
                    self.actor_off(int(self.actor))

    def reset(self):
            if self.actor is not None:
                    self.actor_off(int(self.actor))

    def finish(self):
            if self.actor is not None:
                    self.actor_off(int(self.actor))

    def execute(self):
            for key, value in cbpi.cache.get("sensors").iteritems():
                    if key == int(self.sensor):
                            sensorValue = value.instance.last_value
            if float(sensorValue) >= float(self.volume):
                    self.next()


