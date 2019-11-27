# WeatherStation

prerequisites:

sudo apt-get install python-pigpio python3-pigpio

sudo apt-get install libjpeg-dev

pip3 install Pillow

sudo apt-get install python3-picamera

pip3 install boto3

sudo raspi-config // to activate camera

//set boto3 credentials:
https://boto3.amazonaws.com/v1/documentation/api/latest/guide/quickstart.html

//set the chron to run pigpiod & the node on startup
@reboot sudo pigpiod
@reboot python3 /home/pi/mel-ws/NodeWs.py &

