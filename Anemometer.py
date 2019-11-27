hw = True
import math
import threading
import time
import logging

if hw:
    import RPi.GPIO as GPIO

logging.basicConfig(filename='log_weather.log', level=logging.ERROR, format='%(asctime)s %(message)s', datefmt='%d/%m/%Y %I:%M:%S %p')

class Anemo(threading.Thread):
    def __init__(self, pinAnemometer, anemo_dia = 9.0, time_interval = 5):
        threading.Thread.__init__(self)
        if hw:
            # Set GPIO
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            GPIO.setup(pinAnemometer, GPIO.IN, GPIO.PUD_UP)
            GPIO.add_event_detect(pinAnemometer, GPIO.FALLING, callback=self.spin)
        self.countAnemometer = 0
        self.anemo_dia = anemo_dia
        self.interval = time_interval
        self.wind_speed = 0
        
    def calculate_speed(self, r_cm = 9.0, time_sec = 5):
        circ_cm = (2 * math.pi) * r_cm
        rot = self.countAnemometer / 2.0
        dist_km = (circ_cm * rot) / 100000.0 # convert to kilometres
        km_per_sec = dist_km / time_sec
        km_per_hour = km_per_sec * 3600 # convert to distance per hour
        return km_per_hour

    #interrupt callback
    def spin(self,channel):
        self.countAnemometer += 1
    
    def run(self):
        self.readAnemometer()
    
    #Anemometer loop thread
    def readAnemometer(self):
        while True:
            try:    
                self.countAnemometer = 0
                time.sleep(self.interval)
                self.wind_speed = self.calculate_speed(self.anemo_dia, self.interval)
                logging.debug(str(self.wind_speed) + ' reading Anemometer')
            except Exception as e:
                logging.critical(str(e)+' error reading Anemometer')
                time.sleep(self.interval)