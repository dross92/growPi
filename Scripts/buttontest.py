import RPi.GPIO as GPIO
import time

#GPIO.cleanup()
GPIO.setmode(GPIO.BCM) 

PUSH = 26
PUMP = 13
FAN  = 17

GPIO.setwarnings(False)
GPIO.setup(PUSH, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(PUMP, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(FAN, GPIO.OUT, initial=GPIO.LOW)
GPIO.add_event_detect(PUSH, GPIO.BOTH)
def BUTTON(channel):
    if GPIO.input(26) == 0:
        #GPIO.output(13, 0)
        GPIO.output(17, 0)
    if GPIO.input(26) == 1:
        #GPIO.output(13, 1)
        GPIO.output(17, 1) 
def main():
    GPIO.add_event_callback(PUSH, BUTTON)
    while True:
        time.sleep(1)
        # Fast Clicking
        #GPIO.output(17, GPIO.HIGH)
        #time.sleep(.02)
        #GPIO.output(17, GPIO.LOW)           
    
if __name__=="__main__":
   main()
