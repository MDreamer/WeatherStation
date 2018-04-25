hw = True

import time
import logging
if hw:
    import picamera
import threading

logging.basicConfig(filename='log_weather.log', level=logging.INFO, format='%(asctime)s %(message)s', datefmt='%d/%m/%Y %I:%M:%S %p')

class ImageGen(threading.Thread):
    def __init__(self, ImageFilename, res_w=1024, res_h=768, vFlip=True, hFlip=True):
        threading.Thread.__init__(self)
        if hw:
            self.camera = picamera.PiCamera() 
            self.camera.resolution = (res_w, res_h)
            self.camera.vflip = vFlip
            self.camera.hflip = hFlip
            self.ImageFilename = ImageFilename
        #to make sure that the image capture is finished
        self.camLock = threading.Lock()
    
    def run(self):
        self.loopTakePic()
    
    #to be used in mocking/without hw
    def captureImage(self):
        self.camera.capture(self.ImageFilename)
        
    def loopTakePic(self):
        while True:
            try:
                #Camera handling
                logging.info('Capturing image...')
                self.camLock.acquire()
                if hw:
                    self.captureImage()
                self.camLock.release()
                time.sleep(240) #sleep for 4 min
            except Exception as e: 
                self.camLock.release()
                logging.critical(str(e)+' failed taking image')
                time.sleep(60)  #sleep for 1 min
