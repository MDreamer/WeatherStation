#!/usr/bin/python3
from WindVane import Vane
import WindVane
hw=True #"ifndef C"

#for remote debugging
#import sys
#import pydevd; pydevd.settrace('192.168.1.16', port=5678)

from decimal import Decimal
from datetime import datetime
import logging
import json
import os
from PIL import Image
import time
import threading
import CameraImage
import HandlerS3
import Anemometer
import HandlerAWSIoTMQTT

#if hw:
    #import RPi.GPIO as GPIO
     
    # Set GPIO to output
    #GPIO.setmode(GPIO.BCM)
    #GPIO.setwarnings(False)

logging.basicConfig(filename='log_weather.log', level=logging.ERROR, format='%(asctime)s %(message)s', datefmt='%d/%m/%Y %I:%M:%S %p')

def compressMe(file):
    filepath = os.path.join(os.getcwd(), file)
    picture = Image.open(filepath)
    #set quality= to the preferred quality. 
    #85 has no difference in my 6-10mb files and that 65 is the lowest reasonable number
    picture.save("Compressed_"+file,"JPEG",optimize=True,quality=85) 


if __name__ == '__main__':     
    #Loads the config
    script_path = os.path.abspath(os.path.dirname(__file__))

    config_data = json.load(open(os.path.join(script_path, 'config.json')))
    server = HandlerS3.AWS_S3(config_data["Bucket"], config_data["NodePath"], "Compressed_" + config_data["ImageFilename"])

    cam = CameraImage.ImageGen(config_data["ImageFilename"])
    cam.start()
    anemo = Anemometer.Anemo(config_data["pinAnemometer"], config_data["anemo_dia"], config_data["time_interval"], config_data['HardwareMode'])
    anemo.start()
    vane = WindVane.Vane(config_data["pinVane"], config_data['HardwareMode'])
    vane.start()
    mqtt = HandlerAWSIoTMQTT.AWS_IoTMQTTClient(config_data["StationNumber"], config_data['AWSIoTMQTTClient']['host'], config_data['AWSIoTMQTTClient']['rootCAPath'], config_data['AWSIoTMQTTClient']['privateKeyPath'], script_path, config_data['AWSIoTMQTTClient']['certificatePath'], config_data['AWSIoTMQTTClient']['topic'])
    while True:
        #make sure that the camera is not taking images
        #compress the taken image before sending it to the server
        cam.camLock.acquire()
        try:   
            compressMe(config_data["ImageFilename"])
            cam.camLock.release()
        except Exception as e: #in case image compression failed.. No image, cannot save file?
            logging.critical(str(e)+' failed compressing image')
            cam.camLock.release()
        
        txtDirection = vane.getDirection()
        txtSpeed = round(Decimal(anemo.wind_speed),2) #2 decimal places 
        
        f = open('weatherdata.txt', 'w')
        f.write(str(txtDirection))
        f.write('\n')
        f.write(str(txtSpeed))
        f.write('\n')
        str_time = datetime.now().strftime("%H:%M:%S %d-%m-%Y")
        f.write(str(str_time))
        f.write('\n')
        f.close()
        
        server.uploadImage()
        server.uploadTelemetry() #for ozwassup
        #for weather watcher
        WeatherSummaries = [int(time.time()), round(anemo.wind_speed,1), round(anemo.wind_speed,1), round(anemo.wind_speed,1), round(vane.direction_deg,2)]
        mqtt.publish_data(WeatherSummaries)

        time.sleep(300)