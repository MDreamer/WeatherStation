# Amazon S3 handling
import boto3
import logging

logging.basicConfig(filename='log_weather.log', level=logging.INFO, format='%(asctime)s %(message)s', datefmt='%d/%m/%Y %I:%M:%S %p')

class AWS_S3:
    def __init__(self, bucket_name, image_filename = "image.jpg", telemetry_filename = "weatherdata.txt"):
        # Return an object and sets the bucket name
        self.s3 = boto3.resource('s3')
        self.bucket_name = bucket_name
        self.telemetry_filename =  telemetry_filename
        self.image_filename = image_filename

#upload the telemetry file to the S3 Bucket
    def uploadTelemetry(self):
        try:
            logging.info('Uploading telemetry...')
            self.s3.meta.client.upload_file(self.telemetry_filename, self.bucket_name, self.telemetry_filename, ExtraArgs={ "ContentType": "text/plain", 'ACL': 'public-read'})
            return True
        except Exception as e:
            logging.critical(str(e) + ' Failed uploading telemetry file to S3')
            return False
    
    #upload the compressed image to the S3 Bucket
    def uploadImage(self):
        try:
            logging.info('Uploading an image to S3..')
            self.s3.meta.client.upload_file(self.image_filename, self.bucket_name, self.image_filename, ExtraArgs={ "ContentType": "image/jpg", 'ACL': 'public-read'})
            return True
        except Exception as e:
            logging.critical(str(e) + ' Failed uploading an image to S3')
            return False
        