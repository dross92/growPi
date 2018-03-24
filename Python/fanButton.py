#
#
# Uses push button to turn a relay on/off
# I couldn't get the event detect to work with 
# GPIO.RSING or GPIO.FALLING so I used GPIO.BOTH
# and a counter + even number check so every press
# alternates on / off
#

import RPi.GPIO as GPIO
import time 

GPIO.setmode(GPIO.BCM) 

PUSH = 26
FAN = 17
counter = 0
GPIO.setwarnings(False)
GPIO.setup(PUSH, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(FAN, GPIO.OUT, initial=GPIO.LOW)
GPIO.add_event_detect(PUSH, GPIO.BOTH)

def PRESSED(channel):
	global counter
	if GPIO.input(26) == 1:
		if counter % 2 == 0:		#check if even
			GPIO.output(FAN,1)
		else:
			GPIO.output(FAN,0)
		counter += 1
		if counter = 100:			#keep counter low
			counter =0

def main():
	GPIO.add_event_callback(PUSH, PRESSED)
	while True:
		time.sleep(5)



if __name__=="__main__":
   main()
