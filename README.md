# WeatherStation

prerequisites:

sudo apt-get -y install python-pigpio python3-pigpio libjpeg-dev python3-picamera git python3 python3-pip

pip3 install Pillow
pip3 install RPi.GPIO
pip3 install boto3
pip3 install AWSIoTPythonSDK
pip3 install spidev

sudo raspi-config // to activate camera

//set boto3 credentials:
aws configure
pip3 install awscli
https://boto3.amazonaws.com/v1/documentation/api/latest/guide/quickstart.html

//set the chron to run pigpiod & the node on startup
@reboot sudo pigpiod
@reboot python3 /home/pi/mel-ws/NodeWs.py &

//set iot certificates
dir iot_cert