# Amazon S3 handling
import boto3
import logging
import time
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient  #requires pip install AWSIoTPythonSDK
import json		#Standard Python Module
import os.path #Standard Python Module
import sys


logging.basicConfig(filename='log_weather.log', level=logging.WARNING, format='%(asctime)s %(message)s', datefmt='%d/%m/%Y %I:%M:%S %p')

class AWS_IoTMQTTClient:
    def iotOnlineCallback(self):
        #print(str(datetime.now()) + ' - AWS IoT Connection - Online')
        logging.info('AWS IoT Connection - Online')

    def iotOfflineCallback(self):
        #print(str(datetime.now()) + ' - AWS IoT Connection - Offline')
        logging.info('AWS IoT Connection - Offline')

    def __init__(self, STN, host, rootCAPath, privateKeyPath, script_path, certificatePath, topic):
        # Return an object and Initialise the AWSIoTMQTTClient
        self.topic = topic
        self.STN = STN
        self.myAWSIoTMQTTClient = AWSIoTMQTTClient(str(STN))
        self.myAWSIoTMQTTClient.configureEndpoint(host, 8883)
        self.myAWSIoTMQTTClient.configureCredentials(os.path.join(script_path, rootCAPath), os.path.join(script_path, privateKeyPath), os.path.join(script_path, certificatePath))
        self.myAWSIoTMQTTClient.configureAutoReconnectBackoffTime(5, 128, 20)
        self.myAWSIoTMQTTClient.configureOfflinePublishQueueing(-1)  # Infinite offline Publish queueing
        self.myAWSIoTMQTTClient.configureDrainingFrequency(1)  # Draining: 1 Hz ie 1 per second
        self.myAWSIoTMQTTClient.configureConnectDisconnectTimeout(10)  # 10 sec
        self.myAWSIoTMQTTClient.configureMQTTOperationTimeout(10)  # 5 sec
        # Register an onOnline callback
        self.myAWSIoTMQTTClient.onOnline = self.iotOnlineCallback
        
        #Register an onOffline callback
        self.myAWSIoTMQTTClient.onOffline = self.iotOfflineCallback
        
        #TODO: re-enable with with random seed backoff timer
        #starttime=time.time()

        #This just pauses until its a clean start on a divisor of 00 seconds. More just for prettiness.
        #If you wanted perfect minutes (on system clock time) would make the divisor 60
        #Probally actuall inefficent as it means all stations will push results to IOT service at the exact same time. But fine while small number of stations.
        #waittime = 1 - (starttime % 1)
        #time.sleep(waittime)
        #starttime=time.time()


        # Connect and subscribe to AWS IoT
        connectStatus = False
        for x in range(5):
            logging.info('Trying to connect to IoT')
            try:
                if connectStatus == False:
                    connectStatus = self.myAWSIoTMQTTClient.connect(120)  # Connect to AWS IoT with keepalive interval set to 120 seconds
            except Exception as e:
                logging.warning("Failed IoT Conneciton Attempt: " + str(e))
                time.sleep(3)

        if connectStatus == True:
            logging.info('AWS IoT connections established')
        else:
            logging.error('AWS IoT connection failed after 5 attempts')

    def publish_data(self, weather_data):
        try:
            #print ('station.readWeatherSummaries()' + str(station.readWeatherSummaries()))
            weatherSummaries = [self.STN]
            weatherSummaries = weatherSummaries + weather_data
            
            msgString = str(weatherSummaries)
            
            #datagram example: 
            #STN, time, windmin, windavg, windmax, direction
            #msgString   [150, 1579567059, 5.9, 6.7, 7.8, 269]
            #print('msgString   '+ msgString)

            self.myAWSIoTMQTTClient.publish(self.topic, msgString, 1)

        except Exception as e:
            logging.warning("Failed to publish IoT data: " + str(e))