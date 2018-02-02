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
# Dates   
#   11/10/2017 : fullbucket v2 adds soil data to thingspeak api & adds all data to LCD print
#   11/10/2017 : fullbucket_v1 integrates soil moisture into LCD printout
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
import chirp             # soil sensor library
import bme280            # Temp / Humis Sensor library
import lcd_i2c           # i2C LCD library
#----------------------------------------------
###############i2c params######################
I2C_ADDR  = 0x27 # LCD I2C device address
DEVICE    = 0x76 # DME280  I2C address
SMBUSID   = 1    # 1: Pi 3 B SMBUS
###############################################
#----------------------------------------------
############Soil Moisture Sensor params########
# These values needs to be calibrated for the percentage to work!
# The highest and lowest value with wet and dry soil.
min_moist = 335
max_moist = 700
chirp = chirp.Chirp(address=0x21,               # soil sensor i2c address
                    read_moist=True,
                    read_temp=True,
                    read_light=True,
                    min_moist=min_moist,
                    max_moist=max_moist,
                    temp_scale='farenheit',     # 'farenheit' or 'celcius'
                    temp_offset=0)              # temp offset
###############################################
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

def sendData(url,key,field1,field2,field3,field4,field5,field6,field7,temp,pres,humid,tempf,cMoist,cMoistP,cTemp):
    """
    Send event to Thingspeak internet site
    """
    values = {'api_key' : key,'field1' : temp,'field2' : pres,'field3' : humid,'field4' : tempf,'field5' : cMoist,'field6' : cMoistP,'field7' : cTemp,'timezone' : tz_local}

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

def main():

    #Bring in constants
    global DEVICE
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
    GPIO.setup(18, GPIO.OUT)    #GPIO 18 => Output
    bus = smbus.SMBus(SMBUSID)  
    pwm = GPIO.PWM(18, 25000)   #GPIO 18 PWM @ 25kHz
    pwm.start(0)                #set duty cycle to 0
    lcd_i2c.lcd_init()

    while True:
        try:
            #pull data from BME
            lcd_i2c.lcd_string("      UPDATING      ",LCD_LINE_1)   #display "updtn in top right
            (temperature,pressure,humidity)=bme280.readBME280All(DEVICE)
            temperatureF=temperature*(9)/(5)+32
            chirp_moist = chirp.moist
            chirp_moistPercent = chirp.moist_percent
            chirp_temp  = chirp.temp
            #send to thingspeak server
            sendData(THINGSPEAKURL,THINGSPEAKKEY,'field1','field2','field3','field4','field5','field6','field7',temperature,pressure,humidity,temperatureF,chirp_moist,chirp_moistPercent,chirp_temp)
            sys.stdout.flush()

            # DO THINGS HERE while Waiting for next ThingsSpeak update
            for i in range(0,INTERVAL*6):

                # Trigger the sensors and take measurements.
                chirp.trigger()
                chirp_moist = chirp.moist
                chirp_temp  = chirp.temp
                chirp_moistPercent = chirp.moist_percent
                chirp_light = chirp.light
                output = '{:d} {:4.1f}% | {:3.1f}°F | {:d}'
                output = output.format(chirp_moist, chirp_moistPercent, chirp_temp, chirp_light)   
                (temperature,pressure,humidity)=bme280.readBME280All(DEVICE)
                temperatureF=temperature*(9)/(5)+32
                print(output)

                #Fan  Speed Control Loop
                templog = "Temp = {:.2f} F".format(temperatureF) + " | "
                if temperatureF > 82:
                    pwm.ChangeDutyCycle(100)            # MAX fan speed
                    templog = templog + "PWM = 100"
                    pwm_live = 100
                    print templog
                elif temperatureF > 80:
                    pwm.ChangeDutyCycle(75)
                    templog = templog + "PWM = 75"
                    pwm_live = 75
                    print templog
                elif temperatureF > 76:
                    pwm.ChangeDutyCycle(30)
                    templog = templog + "PWM = 30"
                    pwm_live = 30
                    print templog
                elif temperatureF > 72:
                    pwm.ChangeDutyCycle(15)
                    templog = templog + "PWM = 15"
                    pwm_live = 15
                    print templog  
                else:
                    pwm.ChangeDutyCycle(0)              # MIN fan speed
                    templog = templog + "PWM =0"
                    pwm_live = 0
                    print templog
                #Pirnt all data to LCD screen
                lcd_i2c.lcd_string("PWM  = {:.0f}  [{}]".format(pwm_live, time.strftime("%H:%M")),LCD_LINE_1)  #update the time         
                lcd_i2c.lcd_string("Soil = {:d}   | {:3.1f}%".format(chirp_moist, chirp_moistPercent),LCD_LINE_2)         
                lcd_i2c.lcd_string("Temp = {:.2f} | {:.2f}".format(temperatureF, chirp_temp),LCD_LINE_3)
                lcd_i2c.lcd_string("Hum  = {:.2f}%| {:d}".format(humidity,chirp_light),LCD_LINE_4)
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
