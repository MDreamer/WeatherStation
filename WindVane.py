hw = True
import math
import threading
import time
import logging
from collections import deque
import spidev # To communicate with SPI devices
from numpy import interp	# To scale val

if hw:
    import RPi.GPIO as GPIO
    import pigpio # http://abyz.co.uk/rpi/pigpio/python.html

logging.basicConfig(filename='log_weather.log', level=logging.ERROR, format='%(asctime)s %(message)s', datefmt='%d/%m/%Y %I:%M:%S %p')

#Wind vane params
pinWindVane = 17 
GLITCH     = 100
PRE_MS     = 200
POST_MS    = 15
FREQ       = 38.8
SHORT      = 10
GAP_MS     = 100
TOLERANCE  = 15

POST_US    = POST_MS * 1000
PRE_US     = PRE_MS  * 1000
GAP_S      = GAP_MS  / 1000.0
TOLER_MIN =  (100 - TOLERANCE) / 100.0
TOLER_MAX =  (100 + TOLERANCE) / 100.0

class Vane(threading.Thread):
    def __init__(self, pinWindVane, typeVane='Holman', MCP_conf = '3002'):
        threading.Thread.__init__(self)
        self.code = []
        self.fetching_code = False
        self.last_tick = 0
        self.in_code = False
        self.pinWindVane = pinWindVane
        self.txtDirection= "nothing"
        self.direction_deg = 0
        self.typeVane = typeVane
        self.MCP_conf = MCP_conf
        if hw:
            if self.typeVane == 'Davis':
                if self.MCP_conf == '3008':
                    # Start SPI connection
                    self.spi = spidev.SpiDev() # Created an object
                    self.spi.open(0,0)
                elif self.MCP_conf == '3002':                    
                    GPIO.setwarnings(False)
                    GPIO.setmode(GPIO.BOARD)
                    #
                    self.SPICLK = 11
                    self.SPIMOSI = 15
                    self.SPIMISO = 13
                    self.SPICS = 23

                    # set up the SPI interface pins
                    GPIO.setup(self.SPIMOSI, GPIO.OUT)
                    GPIO.setup(self.SPIMISO, GPIO.IN)
                    GPIO.setup(self.SPICLK, GPIO.OUT)
                    GPIO.setup(self.SPICS, GPIO.OUT)

            else: #=Holman
                self.pi = pigpio.pi() # Connect to Pi.
                self.hwHandling()
            
    #for decoupling and mocking
    def hwHandling(self):
        if not self.pi.connected:
            logging.critical('Cannot connect to pigpio-pi')
        self.pi.set_mode(self.pinWindVane, pigpio.INPUT) # wind vane connected to this pinWindVane.
        self.pi.set_glitch_filter(self.pinWindVane, GLITCH) # Ignore glitches.
        self.pi.callback(self.pinWindVane, pigpio.EITHER_EDGE, self.cbf)

    def getDirection(self):
        return self.txtDirection

    def cbf(self, gpio, level, tick):
        
        if level != pigpio.TIMEOUT:    
            edge = pigpio.tickDiff(self.last_tick, tick)
            
            self.last_tick = tick
            
            if self.fetching_code:
                if (edge > PRE_US) and (not self.in_code): # Start of a code.
                    self.in_code = True
                    self.pi.set_watchdog(self.pinWindVane, POST_MS) # Start watchdog.
                    
                elif (edge > POST_US) and self.in_code: # End of a code.
                    self.in_code = False
                    self.pi.set_watchdog(self.pinWindVane, 0) # Cancel watchdog.
                    self.end_of_code()
    
                elif self.in_code:
                    
                    self.code.append(edge)
    
        else:
            self.pi.set_watchdog(self.pinWindVane, 0) # Cancel watchdog.
            if self.in_code:
                #Reached end of code, now check of it is valid
                self.in_code = False
                self.end_of_code()
    
    def end_of_code(self):
        if len(self.code) > SHORT:
            self.fetching_code = False
        else:
            self.code = []
            logging.critical('Error deciphering EOF')
    
    def run(self):
        
        if self.typeVane == 'Davis':
            self.loopWindVaneDavis()
        else:
            self.loopWindVane()

    # read SPI data from MCP3002 chip, 2 possible adc's (0 thru 1)
    def readadc3002(self, adcnum, clockpin, mosipin, misopin, cspin):
        if ((adcnum > 1) or (adcnum < 0)):
            return -1
        GPIO.output(cspin, True)
        
        GPIO.output(clockpin, False)  # start clock low
        GPIO.output(cspin, False)     # bring CS low
        
        commandout = adcnum << 1;
        commandout |= 0x0D  # start bit + single-ended bit + MSBF bit
        commandout <<= 4    # we only need to send 4 bits here
        
        for i in range(4):
            if (commandout & 0x80):
                GPIO.output(mosipin, True)
            else:
                GPIO.output(mosipin, False)
            commandout <<= 1
            GPIO.output(clockpin, True)
            GPIO.output(clockpin, False)
        
        adcout = 0
        
        # read in one null bit and 10 ADC bits
        for i in range(11):
            GPIO.output(clockpin, True)
            GPIO.output(clockpin, False)
            adcout <<= 1
            if (GPIO.input(misopin)):
                adcout |= 0x1
        GPIO.output(cspin, True)
        
        adcout /= 2       # first bit is 'null' so drop it
        return adcout

    def loopWindVaneDavis(self):
        reading_window = deque([])
        while True:

            if self.MCP_conf == '3008':
                output = self.analogInput(0) # Reading from CH0
            elif self.MCP_conf == '3002':             
                # Read ADC channel 0 for wind direction
                output = self.readadc3002(0, self.SPICLK, self.SPIMOSI, self.SPIMISO, self.SPICS)
            
            self.direction_deg = interp(output, [0, 1023], [0, 359])
            
            #offset for Galvin's installation
            self.direction_deg += 270
            self.direction_deg %= 360

            #convert the direciton to a 0-16 number so numbers_to_direction can be used
            direction_16 = int(self.direction_deg / 22.5)
            
            #25 elements tumbling window
            reading_window.append(direction_16)
            if len(reading_window) > 25:
                reading_window.popleft()

            
            sum_dir = self.mostFrequent(list(reading_window), len(reading_window))
            self.direction_deg = sum_dir * 22.5

            #converts numerical direction representation to text
            self.txtDirection = self.numbers_to_direction(sum_dir)
            logging.debug('Finishing reading wind vane, direction: ' + self.txtDirection)
            #print('Finishing reading wind vane, direction: ' + self.txtDirection)
            time.sleep(0.5)

    # Read MCP3008 data
    def analogInput(self, channel):
        self.spi.max_speed_hz = 1350000
        adc = self.spi.xfer2([1,(8+channel)<<4,0])
        data = ((adc[1]&3) << 8) + adc[2]
        return data

    def loopWindVane(self):
        reading_window = deque([])
        while True:
            logging.debug('Starting reading wind vane')
            self.code = []
            self.fetching_code = True
            while self.fetching_code:
                time.sleep(0.1)
            
            time.sleep(0.5)
            read_1 = self.code[:]
            done = False
            tries = 0
            while not done:
                self.code = []
                self.fetching_code = True
                while self.fetching_code:
                    time.sleep(0.1)
                read_2 = self.code[:]
                the_same = self.compare(read_1, read_2)
                if the_same:
                    #OK reading
                    done = True
                    records = read_1[:]
                    time.sleep(0.5)
                else:
                    tries += 1
                    if tries <= 3:
                        logging.debug("No match for wind vane")
                    else:
                        logging.debug("No match for wind vane, giving up after 3 tries")
                        done = True
                    time.sleep(0.5)
    
            #Takes only the last 4 bit readings (out of 8)
            #There are gaps between them so only take even numbers 
            if (len(records)>13):
                compass = []
    
                if (records[8] > 400 and records[8] < 600):
                    compass.append(0)
                else:
                    compass.append(1)
    
                if (records[10] > 400 and records[10] < 600):
                    compass.append(0)
                else:
                    compass.append(1)
    
                if (records[12] > 400 and records[12] < 600):
                    compass.append(0)
                else:
                    compass.append(1)
    
                if (records[14] > 400 and records[14] < 600):
                    compass.append(0)
                else:
                    compass.append(1)
    
                #number representation of the direction
                dir_num = 0
                for bit in compass:
                    dir_num = (dir_num << 1) | bit
            
            #25 elements tumbling window
            reading_window.append(dir_num)
            if len(reading_window) > 25:
                reading_window.popleft()

            sum_dir = self.mostFrequent(list(reading_window), len(reading_window))

            #convers numerical direction representation to text
            self.txtDirection = self.numbers_to_direction(sum_dir)
            logging.debug('Finishing reading wind vane, direction: ' + self.txtDirection)

    def numbers_to_direction(self,argument):
        '''
        0    0    0    0    N
        0    0    0    1    NNE
        0    0    1    0    NE
        0    0    1    1    ENE
        0    1    0    0    E
        0    1    0    1    ESE
        0    1    1    0    SE
        0    1    1    1    SSE
        1    0    0    0    S
        1    0    0    1    SSW
        1    0    1    0    SW
        1    0    1    1    WSW
        1    1    0    0    W
        1    1    0    1    WNW
        1    1    1    0    NW
        1    1    1    1    NNW
        '''
        switcher = {
            0: "N",
            1: "NNE",
            2: "NE",
            3: "ENE",
            4: "E",
            5: "ESE",
            6: "SE",
            7: "SSE",
            8: "S",
            9: "SSW",
            10: "SW",
            11: "WSW",
            12: "W",
            13: "WNW",
            14: "NW",
            15: "NNW"
        }
        return switcher.get(argument, "nothing")
    
    def compare(self, p1, p2):
        """
        Check that both recordings correspond in pulse length to within
        TOLERANCE%.  If they do average the two recordings pulse lengths.
    
        Input
    
            M    S   M   S   M   S   M    S   M    S   M
        1: 9000 4500 600 560 600 560 600 1700 600 1700 600
        2: 9020 4570 590 550 590 550 590 1640 590 1640 590
    
        Output
    
        A: 9010 4535 595 555 595 555 595 1670 595 1670 595
        """
        if len(p1) != len(p2):
            return False
    
    
        for i in range(len(p1)):
            v = float(p2[i]) / float(p2[i])
            if (v < TOLER_MIN) or (v > TOLER_MAX):
                return False
    
        for i in range(len(p1)):
            p1[i] = int(round((p1[i]+p2[i])/2.0))
    
        return True

    # frequent element in an array. 
    def mostFrequent(self, arr, n): 
    
        # Sort the array 
        arr.sort() 
    
        # find the max frequency using 
        # linear traversal 
        max_count = 1; res = arr[0]; curr_count = 1
        
        for i in range(1, n):  
            if (arr[i] == arr[i - 1]): 
                curr_count += 1
                
            else : 
                if (curr_count > max_count):  
                    max_count = curr_count 
                    res = arr[i - 1] 
                
                curr_count = 1
        
        # If last element is most frequent 
        if (curr_count > max_count): 
        
            max_count = curr_count 
            res = arr[n - 1] 
        
        return res 
  