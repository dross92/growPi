#!/usr/bin/python
"""
* MAX31790 6-Channel PWM-Output Fan RPM Controller Library
* 
* Author : Drew Ross
* 
* Notes:
* _ Use specifc POR settings from hardware
* - If less than 6 fans, use consecutive channels starting at 1
* - 
* - 
* - 
* 
"""

import smbus
import time

bus = smbus.SMBus(1)

#Characteristics
maxAddr = 0x20   # I2C Address (ADD0 & ADD1 = GND)
#maxAddr = 0x40 >> 1   #Datasheet defined 7bit address shifted = 0x20
pulsePerRev = 2  # Number of fan tach pulses  per fan revolution (NP)
tachPeriods = 4  # Chip Default - number of 8192Hz cycles per motor something (SR)


#------------------------Definitions----------------
#FREQS
PWMFREQ_25Hz  = 0b0000
PWMFREQ_30Hz  = 0b0001
PWMFREQ_35Hz  = 0b0010
PWMFREQ_100Hz = 0b0011
PWMFREQ_125Hz = 0b0100
PWMFREQ_5kHz  = 0b1001
PWMFREQ_25kHz = 0b1011

#Spin Up Behavior (2 tach pulses or Max time)
spin_0     = 0b00
spin_500ms = 0b01
spin_1s    = 0b10
spin_2s    = 0b11

#Number of Tach Periods Counted
tachPer_1  = 0b000
tachPer_2  = 0b001
tachPer_4  = 0b010
tachPer_8  = 0b011
tachPer_16 = 0b100
tachPer_32 = 0b101 # or 0b110 or 0b111 will work

#Time between Duty Cycle Increments (ms)
incr_1 = 0b000 # 0
incr_2 = 0b001 # 1.953125
incr_3 = 0b010 # 3.90625
incr_4 = 0b011 # 7.8125 - Default
incr_5 = 0b100 # 15.625
incr_6 = 0b101 # 31.25
incr_7 = 0b110 # 62.5
incr_8 = 0b111 # 125

# Sequential Fan Start Delay
t_0     = 0b000
t_250ms = 0b001
t_500ms = 0b010
t_1s    = 0b011
t_2s    = 0b100
t_4s    = 0b101 # or 0b110 or 0b111 wil work

# Duty Cycle on Failure
duty_0      = 0b00
duty_same   = 0b01
duty_100    = 0b10
duty_ALL100 = 0b11



#--------------------------------------------------------

#---------------------- Register MAP --------------------
#Single Registers
GLOBALCONFIG = 0x00
PWMFREQ = 0x01
SEQ_START = 0x14  #Also Fan Fail Settings

# Fan Config Reg 							02h - 07h
def FAN_CONFIG(channel):
	return 0x02 + (channel - 1)

# Fan Dynamics Reg 							08h - 0Dh
def FAN_DYNAMICS(channel):
	return 0x08 + (channel - 1)

# Read Tach Counter							18h - 23h  - For Fans 1-6
def TACH_COUNT_MSB(channel):
	return 0x18 + ((channel - 1) * 2)
def TACH_COUNT_LSB(channel):
	return 0x19 + ((channel - 1) * 2)

# Read Current PWM Duty Cycle 				30h - 3Bh
def PWM_OUT_DUTYCYCLE_MSB(channel):
	return 0x30 + ((channel - 1) * 2)
def PWM_OUT_DUTYCYCLE_LSB(channel):
	return 0x31 + ((channel - 1) * 2)

# Set Target PWM Duty Cycle 				40h - 4Bh
def PWMOUT_TARGET_MSB(channel):
	return 0x40 + ((channel - 1) * 2)
def PWMOUT_TARGET_LSB(channel):
	return 0x41 + ((channel - 1) * 2)

# Set Target Tach Counter					50h - 5Bh
def TACH_TARGET_COUNT_MSB(channel):
	return 0x50 + ((channel - 1) * 2)
def TACH_TARGET_COUNT_LSB(channel):
	return 0x51 + ((channel - 1) * 2)
#------------------------------------------------------


def writeBit(regAddr, bitNum, data):
	#Write single bit to 8-bit register
	regData = bus.read_byte_data(maxAddr,regAddr)
	writeData = (regData | (1 << bitNum)) if data == 1 else (regData & ~(1 << bitNum))
	bus.write_byte_data(maxAddr, regAddr, writeData)

def writeBits(regAddr, bitStart, length, data):
	#Write multiple bits to 8-bit register
	regData = bus.read_byte_data(maxAddr,regAddr)
	mask = ((1 << length) - 1) << (bitStart - length + 1)
	data = data << (bitStart - length + 1)
	data = data & mask
	writeData = (regData & ~(mask)) | data;
	bus.write_byte_data(maxAddr, regAddr, writeData)


def readReg(regNum):
	#Easier to type in python shell
	return bus.read_byte_data(maxAddr, regNum)

#Settings 
def reset():
	writeBit(GLOBALCONFIG, 6, 1)

def standbyMode():
	writeBit(GLOBALCONFIG, 7, 0)

def runMode():
	writeBit(GLOBALCONFIG, 7, 1)

def spinUp(channel, time):
	writeBits(FAN_CONFIG(channel), 6, 2, time)

def tachEnable(channel, bit):
	writeBit(FAN_CONFIG(channel), 3, bit)
	# 0 = Disable
	# 1 = Enable

def numTachPerCnt(channel, tachPer):
	writeBits(FAN_DYNAMICS(channel), 7, 3, tachPer)

def timeBtwDutyCycleIncr(channel, time):
	writeBits(FAN_DYNAMICS(channel), 4, 3, time)

def rateofChangeSymmetry(channel, bit):
	writeBit(FAN_DYNAMICS(channel), 1, bit)
	# 0 = Same RoC increasing/decreasing
	# 1 = RoC is half when drecreasing

def setSeqStartDelay(time):
	writeBits(SEQSTART, 7, 3, time)

def dutyCycleOnFail(duty):
	writeBits(SEQSTART, 3, 2, duty)

def faultQueue(numFaults):
	writeBits(SEQSTART, 1, 2, numFaults)

def initializeMAX(numberOfFans):
	reset()
	time.sleep(.1)
	for i in range(1,numberOfFans+1):
		#setRPM(i, MaxRPM)   		# Set MAX RPM for faults
		#setPWMTarget(i, 0)	 		# set intial PWM
		tachEnable(i, 1)	 		# Enable Tach input
		rateofChangeSymmetry(i, 1)	#Rate of Change slower when decreaseing
		print "Fan {:d} initialized".format(i)
	#print "MAX31790 Setup Complete"


#--------------------------------------------------

#PWM Functions
def PWMMode(channel):
	#Enable PWM Control Mode
	writeBit(FAN_CONFIG(channel), 7, 1)

def setPWMFreq( freq4_6 , freq1_3):
	#Set the PWM Frequency
	writeData = freq4_6 << 4 | freq1_3
	bus.write_byte_data(maxAddr, PWMFREQ, writeData)

def setPWMTarget(channel, ratePWM):  
	#set target PWM duty cycle in range (0,511)
	MSB = ratePWM >> 1
	LSB = (ratePWM & 0b1) << 7
	bus.write_byte_data(maxAddr, PWMOUT_TARGET_MSB(channel), MSB)
	bus.write_byte_data(maxAddr, PWMOUT_TARGET_LSB(channel), LSB) 

def setPWMTargetDuty(channel, percent):
	#set target PWM duty cycle in range (0,100)
	dutyCycle = (percent * 511) / 100
	MSB = dutyCycle >> 1
	LSB = (dutyCycle & 0b1) << 7
	bus.write_byte_data(maxAddr, PWMOUT_TARGET_MSB(channel), MSB)
	bus.write_byte_data(maxAddr, PWMOUT_TARGET_LSB(channel), LSB) 

def readPWM(channel):
	#read current PWM duty cycle in range (0,500)
	MSB = bus.read_byte_data(maxAddr,PWM_OUT_DUTYCYCLE_MSB(channel))
	LSB = bus.read_byte_data(maxAddr,PWM_OUT_DUTYCYCLE_LSB(channel)) 
	pwmNum = (MSB << 1) | (LSB >> 7)
	return pwmNum

def readPWMDuty(channel):
	#read current PWM duty cycle in range (0,100)
	MSB = bus.read_byte_data(maxAddr,PWM_OUT_DUTYCYCLE_MSB(channel))
	LSB = bus.read_byte_data(maxAddr,PWM_OUT_DUTYCYCLE_LSB(channel)) 
	pwmNum = (MSB << 1) | (LSB >> 7)
	return (pwmNum * 100) / 511	

def	readPWMTarget(channel):
	#Read current PWM target in range (0,511)
	MSB = bus.read_byte_data(maxAddr,PWMOUT_TARGET_MSB(channel))
	LSB = bus.read_byte_data(maxAddr,PWMOUT_TARGET_LSB(channel)) 
	pwmNum = (MSB << 1) | (LSB >> 7)
	return pwmNum	

#RPM Functions
def RPMMode(channel):
	#Enable RPM Control Mode
	writeBit(FAN_CONFIG(channel), 7, 0)

def setRPMTarget(channel, rateRPM):
	#Set the tach target in RPM
	tCount = (60 * (tachPeriods) * (8192)) / (pulsePerRev * rateRPM)
	MSB = (tCount >> 3)
	LSB = (tCount & 0b111) << 5
	bus.write_byte_data(maxAddr, TACH_TARGET_COUNT_MSB(channel), MSB)
	bus.write_byte_data(maxAddr, TACH_TARGET_COUNT_LSB(channel), LSB) 

def readRPM(channel):
	#Read the current tach count in RPM
	MSB = bus.read_byte_data(maxAddr, TACH_COUNT_MSB(channel))
	LSB = bus.read_byte_data(maxAddr, TACH_COUNT_LSB(channel))
	tCount = (MSB << 3) | (LSB >> 5)
	rpm = (60 * (tachPeriods) * (8192)) / (pulsePerRev * tCount)
	# My tach reads 480 when stopped
	if rpm == 480:
		rpm = 0 
	return rpm

def readRPMTarget(channel):
	#Read the current tach target in RPM
	MSB = bus.read_byte_data(maxAddr, TACH_TARGET_COUNT_MSB(channel))
	LSB = bus.read_byte_data(maxAddr, TACH_TARGET_COUNT_MSB(channel))
	tCount = (MSB << 3) | (LSB >> 5)
	return (60 * (tachPeriods) * (8192)) / (pulsePerRev * tCount)


#Usage Functions
def checkFaults():
	#Returns 0 if no faults
	return readReg(0x11) 

def StopAllFans(numberOfFans):
	for i in range (1,numberOfFans):
		setPWMMode(i)
		setPWMTarget(i,0)

def slowStopAllFans(numberOfFans):
	#NOT FUNCTIONAL
	for i in range (1,numberOfFans):
		setPWMTarget(i,20)
	while(readPwm(1) >20):
		pass
	for i in range (1,numberOfFans):
		setPWMTarget(i,0)

def fanTest():
	#Used to Map expected tach values for each duty cycle
	for i in range (0,512):
		setPWMTarget(1, i)
		time.sleep(.5)
		tachCt = readRPM(1)
		print "{:d}".format(i) + " | " + "{:d}".format(tachCt)



'''
def main():
	initialize(1)



if __name__=="__main__":
   main()
'''