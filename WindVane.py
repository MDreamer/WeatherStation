hw = True
import math
import threading
import time
import logging

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
    def __init__(self, pinWindVane):
        threading.Thread.__init__(self)
        self.code = []
        self.fetching_code = False
        self.last_tick = 0
        self.in_code = False
        self.pinWindVane = pinWindVane
        self.txtDirection= "nothing"
        if hw:
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
        self.loopWindVane()

    def loopWindVane(self):
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
    
                #TODO: validate direction 
                #number representation of the direction
                dir_num = 0
                for bit in compass:
                    dir_num = (dir_num << 1) | bit
                    
            self.txtDirection = self.numbers_to_direction(dir_num)
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