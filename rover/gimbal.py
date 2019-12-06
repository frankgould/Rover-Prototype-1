#!/usr/bin/env python3
#Benjamin Hoeller 0925688 TUWIEN 2013-2014
#this is the main controller that moves the PTHead around

import os
import configparser
import MotorDriver
import datetime
import math
from multiprocessing import Process,Pipe

configPath=os.path.dirname(os.path.abspath(__file__))+os.sep+'config.txt'
Config = configparser.ConfigParser()
Config.read(configPath)

        #from https://wiki.python.org/moin/ConfigParserExamples
def ConfigSectionMap(section):
    dict1 = {}
    options = Config.options(section)
    for option in options:
        try:
            dict1[option] = Config.get(section, option)
            if dict1[option] == -1:
                DebugPrint("skip: %s" % option)
        except:
            dict1[option] = None
    return dict1

def getPinArray(section):
    pin1=int(ConfigSectionMap(section)['pin1'])
    pin2=int(ConfigSectionMap(section)['pin2'])
    pin3=int(ConfigSectionMap(section)['pin3'])
    pin4=int(ConfigSectionMap(section)['pin4'])
    return pin1,pin2,pin3,pin4  

def str2bool(v):
    return v.lower() in ("yes", "true", "t", "1")

class PTZ:

    motor1=MotorDriver
    motor2=MotorDriver

    lastDuration=0

    pan=0
    tilt=0

    maxPhotoCounter=1
   
    def initStepper(section):
        name=ConfigSectionMap(section)['name']
        pinArray=getPinArray(section)
        waitTime=float(ConfigSectionMap(section)['waittime'])
        negateSensor=str2bool(ConfigSectionMap(section)['negatesensor'])
        reverseInit=str2bool(ConfigSectionMap(section)['reverseinit'])
        sensorposition=int(ConfigSectionMap(section)['sensorposition'])
        globalMax=int(ConfigSectionMap(section)['globalmax'])
        angle=int(ConfigSectionMap(section)['angle'])
        backSteps=int(ConfigSectionMap(section)['backsteps'])
        return MotorDriver.stepper(name,pinArray,waitTime,negateSensor,reverseInit,sensorposition,globalMax,angle,backSteps)
	
    maxPhotoCount=int(ConfigSectionMap("ptz")["initcounter"])
	
    motor1=initStepper("stepper1")
    motor2=initStepper("stepper2")

    tilt=motor1.step2Deg(motor1.actualPosition)
    pan=motor2.step2Deg(motor2.actualPosition)

    #increases the photoCounter, if it reaches maxPhotoCounter the device will be reinicialised!
    def increasePhotoCounter(self):
        self.photoCounter+=1
        if self.photoCounter>=self.maxPhotoCounter:
            self.photoCounter=0
            self.__init__()

    #returns last reset value of pan stepper
    def getLastPanReset(self):
        return self.motor2.getLastReset()

    #returns last reset value of tilt stepper
    def getLastTiltReset(self):
        return self.motor1.getLastReset()

    #returns the steps of tilt axis
    def getU(self):
        return self.motor1.actualPosition

    #returns the steps of pan axis
    def getV(self):
        return self.motor2.actualPosition

    #returns the angle of tilt axis in degrees
    def getTilt(self):
        return self.tilt

    #returns the angle of pan axis in degrees
    def getPan(self):
        return self.pan

    #returns the duration of the last move
    def getLastDuration(self):
        return self.lastDuration

    #sets the new goal position in degrees
    def goto(self,pan,tilt):
        t=datetime.datetime.now()
        U=self.motor1.deg2Step(tilt)
        V=self.motor2.deg2Step(pan)
	
	#to avoid gearwheel clearance we try to move to a point always from the same side 
        nU=U
        nV=V
        d=150
        doBackStepps=False

        if tilt>self.tilt :
            doBackStepps=True
            maxDiff=self.motor1.maxValue-self.motor1.actualPosition
            nU=min(maxDiff,d)+U
        if pan>self.pan :
            doBackStepps=True
            maxDiff=self.motor2.maxValue-self.motor2.actualPosition
            nV=min(maxDiff,d)+V
        if doBackStepps :
            self.gotoUV(nU,nV)
        self.gotoUV(U,V)
        self.pan=pan
        self.tilt=tilt	
        self.lastDuration=datetime.datetime.now()-t

        #sets the new goal position in steps
    def gotoUV(self,U,V):
        global motor1, motor2
        
        self.motor1.setPosition(U)
        self.motor2.setPosition(V)

    #the move method for one stepper
        def move(motor,conn):
            while motor.isMoving():
                motor.move()
            conn.send([motor.actualPosition])

        p_conn1, c_conn1 = Pipe()
        p_conn2, c_conn2 = Pipe()

#for each stepper the move() method above gets called in a single thread
        p1=Process(target=move,args=(self.motor1,c_conn1,))
        p2=Process(target=move,args=(self.motor2,c_conn2,))

        p1.start()
        p2.start()

    #after finishing the threads the position must be saved	
        self.motor1.actualPosition=p_conn1.recv()[0]	 
        self.motor2.actualPosition=p_conn2.recv()[0]    
#        print('gimbal move: motor1.actualPosition=' + str(motor1.actualPosition) + ' motor2.actualPosition=' + str(motor2.actualPosition))

    #to save power while standing
        self.motor1.off()
        self.motor2.off()
	
