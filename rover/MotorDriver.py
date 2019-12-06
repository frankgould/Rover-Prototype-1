#!/usr/bin/python3
#Benjamin Hoeller 0925688 TUWIEN 2013-2014
#the controller class for one motor
import RPi.GPIO as GPIO 
import time 
import math
import fileMemory
from multiprocessing import Process

class stepper:
        
	fm=fileMemory.fileMemory()
	goalPosition=0
	actualPosition=0
	globalMax=0
	angle=0
	maxValue=0
	minValue=0
	pins=[0,0,0,0]
	waitTime=0.001
	name="stepper"
	reverseInit=0
	negateSensor=0
	sensorPosition=0
	backSteps=2000
	lastReset=0

	seq =[  [1,0,0,0],
        [1,1,0,0],
        [0,1,0,0],
        [0,1,1,0],
        [0,0,1,0],
        [0,0,1,1],
        [0,0,0,1],
        [1,0,0,1]]

	#WARNING: make sure all the parameters are set right to avoid pysical damage
	#stepperName: String - the name of the stepper motor
	#pins: int[4] - the numbers of the motor GPIO pins 
	#waitTime: Float - time to wait between steps in Seconds
	#negateSensor: boolean - inverts the sensorinput if true 
	#reverseInit: boolean - inverts the initialisation direction
	#sensorPosition: int - the position of the sensor in steps
	#globalMax: int - maximum amount of steps possible
	#angle: int - rotation angle in degres
	#backSteps: int - the amount of steps to go back to free the sensor
	def __init__(self,stepperName,pins,waitTime,negateSensor,reverseInit,sensorPosition,globalMax,angle,backSteps):
		self.name=stepperName
		self.pins=pins
		self.globalMax=globalMax
		self.maxValue=globalMax
		self.angle=angle
		self.waitTime=waitTime
		self.reverseInit=reverseInit
		self.negateSensor=negateSensor
		self.sensorPosition=sensorPosition
		self.backSteps=backSteps
		GPIO.setmode(GPIO.BOARD)
		GPIO.setwarnings(False)
		for pin in self.pins:
			GPIO.setup(pin,GPIO.OUT)
			GPIO.output(pin,0)
		if self.reverseInit :
			direction=-1
		else :
			direction=1
		self.lastReset=self.actualPosition
		self.actualPosition=self.sensorPosition
#		self.goalPosition = self.actualPosition
		
	#converts steps to degrees
	def step2Deg(self,step):
		if step>self.globalMax:
			step=self.globalMax
		if step<0:
			step=0
		return self.angle*(step/float(self.globalMax))
	
	#converts degrees to steps
	def deg2Step(self,deg):
		if deg>self.angle:
			deg=self.angle
		if deg<0:
			deg=0
		return self.globalMax*(deg/float(self.angle))

	#sets aditional boundries (currently not in use)
	def setBoundries(self,min,max):
		if min<0 :
			min=0
		if max>globalMax :
			max=self.globalMax
		self.maxValue=max
		self.minValue=min
    
	#sets goalposition
	def setPosition(self,p):
		if p<self.minValue:
			p=self.minValue
		elif p>self.maxValue:
			p=self.maxValue
		self.goalPosition=int(p)

	#returns last reset
	def getLastReset(self):
		return self.lastReset
      
	#updates actualPosition one step towards goalposition and calls the step() method to move
	def move(self):
		if self.actualPosition<self.goalPosition:
			self.actualPosition+=1
			self.step()
		elif self.actualPosition>self.goalPosition:
			self.actualPosition-=1
			self.step()
        
	#true if goalPosition not yet reached                
	def isMoving(self):
		return self.actualPosition!=self.goalPosition
    
	#sets the GPIO output to the corresponding actualPosition 
	def step(self):
		for pin in range(4):
			GPIO.output(self.pins[pin], self.seq[self.actualPosition%8][pin])
		time.sleep(self.waitTime)
		if self.sensorPosition>0 and math.fabs(self.sensorPosition-self.actualPosition)>2:
			if self.actualPosition<self.sensorPosition :
				self.fm.delete(self.name)
			else :
				self.fm.save(self.name)

	#shuts down the GPIO output to save energy
	def off(self):
		for pin in range(4):
			GPIO.output(self.pins[pin], 0)
        
