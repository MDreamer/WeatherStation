# Amazon S3 handling
import boto3
import logging
import time

logging.basicConfig(filename='log_weather.log', level=logging.ERROR, format='%(asctime)s %(message)s', datefmt='%d/%m/%Y %I:%M:%S %p')

class AWS_S3:
    def __init__(self, bucket_name, node_path, image_filename = "image.jpg", telemetry_filename = "weatherdata.txt"):
        # Return an object and sets the bucket name
        self.session_ozwassup = boto3.session.Session(profile_name='ozwassup')
        self.s3 = self.session_ozwassup.resource('s3')
        self.session_weatherwatcher = boto3.session.Session(profile_name='weatherwatcher')
        self.s3weatherwatcher = self.session_weatherwatcher.resource('s3')
        self.bucket_name = bucket_name
        self.node_path = node_path
        self.telemetry_filename =  telemetry_filename
        self.image_filename = image_filename

#upload the telemetry file to the S3 Bucket
    def uploadTelemetry(self):
        try:
            logging.info('Uploading telemetry...')
            self.s3.meta.client.upload_file(self.telemetry_filename, self.bucket_name, self.node_path + 'Telemetry/' + self.telemetry_filename, ExtraArgs={ "ContentType": "text/plain", 'ACL': 'public-read'})
            return True
        except Exception as e:
            logging.critical(str(e) + ' Failed uploading telemetry file to S3')
            return False
    
    #upload the compressed image to the S3 Bucket
    def uploadImage(self):
        try:
            station = 150
            timestamp = str(int(time.time()))
            bucket = 'data.weatherwatcher.com.au'
            photoPath = 'data/photos/'
            key = photoPath + str(station) + '/' + timestamp + '.jpg'
            tempLocation = self.image_filename
            #tempLocation = 'Compressed_' + 'image.jpg'
            data = open(tempLocation, 'rb')

            logging.info('Uploading an image to S3..')
            self.s3.meta.client.upload_file(self.image_filename, self.bucket_name, self.node_path + 'Images/' + self.image_filename, ExtraArgs={ "ContentType": "image/jpg", 'ACL': 'public-read'})
            
            self.s3weatherwatcher.Bucket(bucket).put_object(Key=key, Body=data)
            
            return True
        except Exception as e:
            logging.critical(str(e) + ' Failed uploading an image to S3')
            return False
        