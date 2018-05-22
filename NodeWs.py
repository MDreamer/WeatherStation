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

if hw:
    import RPi.GPIO as GPIO
    # Set GPIO for camera LED
    # Use 5 for Model A/B and 32 for Model B+
    CAMLED = 32 
 
    # Set GPIO to output
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(CAMLED, GPIO.OUT, initial=False) 

logging.basicConfig(filename='log_weather.log', level=logging.INFO, format='%(asctime)s %(message)s', datefmt='%d/%m/%Y %I:%M:%S %p')

def compressMe(file):
    filepath = os.path.join(os.getcwd(), file)
    picture = Image.open(filepath)
    #set quality= to the preferred quality. 
    #85 has no difference in my 6-10mb files and that 65 is the lowest reasonable number
    picture.save("Compressed_"+file,"JPEG",optimize=True,quality=85) 

#creates an indication light that can be visible externally using the 
#onboard LED of the PCB camera
blinkFast = False
def Monitoring():
    global blinkFast, hw
    while (True):
        if blinkFast:
            if hw:
                GPIO.output(CAMLED,True) # On
            time.sleep(0.2)
            if hw:
                GPIO.output(CAMLED,False) # Off
            time.sleep(0.2)
        else:
            if hw:
                GPIO.output(CAMLED,True) # On
            time.sleep(3)
            if hw:
                GPIO.output(CAMLED,False) # Off
            time.sleep(3)

if __name__ == '__main__':
    global blinkFast
    
    print ('Vane testing')
    
    config_data = json.load(open('/home/pi/mel-ws/config.json'))
    server = HandlerS3.AWS_S3(config_data["Bucket"],"Compressed_" + config_data["ImageFilename"])
    tMon = threading.Timer(5.0, Monitoring)
    tMon.start()
    cam = CameraImage.ImageGen(config_data["ImageFilename"])
    cam.start()
    anemo = Anemometer.Anemo(config_data["pinAnemometer"], config_data["anemo_dia"], config_data["time_interval"])
    anemo.start()
    vane = WindVane.Vane(config_data["pinVane"])
    vane.start()
    
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
        
        blinkFast = True
        server.uploadImage()
        server.uploadTelemetry()
        blinkFast = False
        time.sleep(300)