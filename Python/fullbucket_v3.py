#!/usr/bin/python
#--------------------------------------
#    ___  ___  _  
#   / _ \/ _ \(_)_____ __ __ __ __     
#  / , _/ ___/ // _  // // // // /     
# /_/|_/_/  /_/ \_, / \___/ \_, /
#              /___/       /___/
#   
#           Envirologger / Fan Controller
#  Read data from a BME280  & Soil Moisture sensor
#  then sends the data to Thingspeak.com account.
#  Also controls fan speed with PWM based on temp data.
#
# Author : Drew Ross
# Updates   
#   02/20/2018 : fullbucket_v3 now using MAX31790 Fan controller with support for up to 6 fans
#   11/10/2017 : fullbucket v2 added soil data to thingspeak api & adds all data to LCD print
#   11/10/2017 : fullbucket_v1 integrated soil moisture into LCD printout
#   11/07/2017 : fullbucket_v0 initiated to consolidate into one script 
#   10/23/2017 : thingspeak data and fan control were seperate scripts to start 
#   10/12/2017 : fixed script crashing from URL post error by implementing try/except error handling  

#
#
#------------------------- References -------------------------------
# *Thingspeak*
#   https://www.raspberrypi-spy.co.uk/2015/06/basic-temperature-logging-to-the-internet-with-raspberry-pi/
#
# *BME280*
#   https://www.raspberrypi-spy.co.uk/2016/07/using-bme280-i2c-temperature-pressure-sensor-in-python/
#
# *Soil Moisture Sensor
#   https://github.com/Miceuz/i2c-moisture-sensor   ->Original
#   https://github.com/Apollon77/I2CSoilMoistureSensor    ->Arduino
#   https://github.com/ageir/chirp-rpi    ->rPi
#
# *PWM*
#   https://sourceforge.net/p/raspberry-gpio-python/wiki/PWM/
#   https://learn.sparkfun.com/tutorials/raspberry-gpio/python-rpigpio-api
#
# *LCD*
#   https://www.raspberrypi-spy.co.uk/2015/05/using-an-i2c-enabled-lcd-screen-with-the-raspberry-pi/
#
# *Interrupts*
#   http://raspi.tv/2013/how-to-use-interrupts-with-python-on-the-raspberry-pi-and-rpi-gpio
#
###############################################
#----------------Libraries---------------------
import smbus
import time
import os
import sys
import urllib            # URL functions
import urllib2           # URL functions
import RPi.GPIO as GPIO  # Raspberry Pi GPIO library
import bme280            # Temp / Humis Sensor library
import lcd_i2c           # i2C LCD library
import MAX31790          # MAX31790
import bmp280
#----------------------------------------------
###############i2c params######################
I2C_ADDR  = 0x27 # LCD I2C device address
BME_ADDR  = 0x76 #BME280  I2C address
BMP_ADDR  = 0x68 #BMP280 I2C Adress

SMBUSID   = 1    # 1: Pi 3 B SMBUS
###############################################
#----------------------------------------------
pushButton = 26   # Button BCM  
PUMP       = 13   # Pump BCM
counter    = 0    # For button press
#----------------------------------------------
###############Thingspeak info#################
INTERVAL      = 1                                     # Delay between each reading (mins)
THINGSPEAKKEY = 'ZEX2JMIAZHUXTG58'                    # API Write Key
THINGSPEAKURL = 'https://api.thingspeak.com/update'   # API URL
tz_local      = 'America/Chicago'                     # Local Timezone
###############################################
#----------------------------------------------
################LCD stuff######################
LCD_WIDTH  = 20     # Maximum characters per line
LCD_LINE_1 = 0x80   # LCD RAM address for the 1st line
LCD_LINE_2 = 0xC0   # LCD RAM address for the 2nd line
LCD_LINE_3 = 0x94   # LCD RAM address for the 3rd line
LCD_LINE_4 = 0xD4   # LCD RAM address for the 4th line
###############################################

def sendData(url,key,field1,field2,field3,field4,temp,pres,humid,tempf):
    """
    Send event to Thingspeak internet site
    """
    values = {'api_key' : key,'field1' : temp,'field2' : pres,'field3' : humid,'field4' : tempf,'timezone' : tz_local}

    postdata = urllib.urlencode(values)     #encode values in url format  ------> (postdata) = api_key=key&field1=temp&field2=pres ....
    req = urllib2.Request(url, postdata)    #attach to URL request  ------> (req) = http://www.thingspeak.com/update?(postdata)

    log = time.strftime("%Y-%m-%d %H:%M:%S") + " | " 
    log = log + "{:.2f} C".format(temp) + " | "
    log = log + "{:.2f} F".format(tempf) + " | "
    log = log + "{:.2f} mBar".format(pres) + " | "
    log = log + "{:.2f} %".format(humid) + " | "
    
    try:
        # Send data to Thingspeak
        response = urllib2.urlopen(req, None, 5)  #open URL (req) to post data to server
        html_string = response.read()             # server returns update number
        response.close()
        log = log + 'Update ' + html_string
    # Error handling so script doesnt break
    except urllib2.HTTPError, e:
        log = log + 'Server could not fulfill the request. Error code: ' + e.code
    except urllib2.URLError, e:
        log = log + 'Failed to reach server. Reason: ' + e.reason
    except:
        log = log + 'Unknown error'

    print log

def BUTTON(channel):
    global counter
    if GPIO.input(26) == 1:
        if counter % 2 == 0:        #check if even
            GPIO.output(PUMP,1)
        else:
            GPIO.output(PUMP,0)
        counter += 1
        if counter == 100:           #keep counter low
            counter =0

def main():

    #Bring in constants
    global BME_ADDR
    global SMBUSID
    global INTERVAL
    global THINGSPEAKKEY
    global THINGSPEAKURL
    global errors
    global I2C_ADDR
    global LCD_WIDTH
    global pwm_live

    #Setup
    errors = 0    #exception counter
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)      #Use BCM numbering for pins
    GPIO.setup(pushButton, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(PUMP, GPIO.OUT, initial=GPIO.LOW)
    GPIO.add_event_detect(pushButton, GPIO.BOTH)
    GPIO.add_event_callback(pushButton, BUTTON)

    bus = smbus.SMBus(SMBUSID)  
    lcd_i2c.lcd_init()
    MAX31790.initializeMAX(1)
    try:
        sensW = bmp280.bmp280Wrapper()
    except:
        print BMP280 init FAIL
    print("Found BMP280 : (%s)" %hex(sensW.chipID))
    sensW.resetSensor()
    # configuration byte contains standby time, filter, and SPI enable.
    bmp280Config = sensW.tSb62t5 | sensW.filt4
    # measurement byte contains temperature + pressure oversampling and mode.
    bmp280Meas = sensW.osP16 | sensW.osT2 | sensW.modeNormal
    # Set sensor mode.
    sensW.setMode(config = bmp280Config, meas = bmp280Meas)

    while True:
        try:
            #pull data from BME
            lcd_i2c.lcd_string("      UPDATING      ",LCD_LINE_1)   #display "updating" during thingspeak update
            (temperature,pressure,humidity)=bme280.readBME280All(BME_ADDR)
            temperatureF=temperature*(9)/(5)+32
            #send to thingspeak server
            sendData(THINGSPEAKURL,THINGSPEAKKEY,'field1','field2','field3','field4',temperature,pressure,humidity,temperatureF)
            sys.stdout.flush()

            # DO THINGS HERE while Waiting for next ThingsSpeak update
            for i in range(0,INTERVAL*6):
  
                (temperature,pressure,humidity)=bme280.readBME280All(BME_ADDR)
                temperatureF=temperature*(9)/(5)+32
                rpm = MAX31790.readRPM(1)
                #BMP280 TEST
                sensW.readSensor()
                print("Pressure   : %s Pa" %sensW.pressure)
                print("Temperature: %s C" %sensW.temperature)

                #Fan  Speed Control Loop
                templog = "Temp = {:.2f} F | RPM = {:d}".format(temperatureF,rpm) + " | "
                if temperatureF > 82:
                    MAX31790.setPWMTargetDuty(1, 30)            # MAX fan speed
                    templog = templog + "PWM = 70"
                    pwm_live = 80
                    print templog
                elif temperatureF > 80:
                    MAX31790.setPWMTargetDuty(1, 40)
                    templog = templog + "PWM = 60"
                    pwm_live = 60
                    print templog
                elif temperatureF > 76:
                    MAX31790.setPWMTargetDuty(1, 50)
                    templog = templog + "PWM = 50"
                    pwm_live = 50
                    print templog
                elif temperatureF > 72:
                    MAX31790.setPWMTargetDuty(1, 60)
                    templog = templog + "PWM = 40"
                    pwm_live = 40
                    print templog  
                else:
                    MAX31790.setPWMTargetDuty(1, 70)              # MIN fan speed
                    templog = templog + "PWM = 30"
                    pwm_live = 30
                    print templog
                # Refresh LCD screen
                lcd_i2c.lcd_string("PWM  = {:.0f} | [{}]".format(pwm_live, time.strftime("%H:%M")),LCD_LINE_1)  #update the time         
                lcd_i2c.lcd_string("Tach = {:d} rpm".format(rpm),LCD_LINE_2)         
                lcd_i2c.lcd_string("Temp = {:.1f} F | {:.0f}C".format(temperatureF,temperature),LCD_LINE_3)
                lcd_i2c.lcd_string("Hum  = {:.2f} %".format(humidity),LCD_LINE_4)
                time.sleep(10)
        #Error Handling
        except :
            errors += 1
            print "err cnt: {:d}  , delay 5s -> try again".format(errors)
            #lcd_i2c.lcd_string("   err = {:d}   ERROR".format(errors),LCD_LINE_1)   #display that an error occured      
            time.sleep(5)
            continue

if __name__=="__main__":
   main()
