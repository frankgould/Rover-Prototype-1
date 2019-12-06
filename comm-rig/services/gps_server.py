#! /usr/bin/python
# Original Written by Dan Mandle http://dan.mandle.me September 2012
# License: GPL 2.0
# Modifications by Frank Gould April 2019

from gps import *
from time import *
import time, sys
import threading, logging, atexit
from threading import Thread
from datetime import datetime

gpsd = None     #seting the global variable
 
log_file = '/home/comm_logs/gps_server-log-' + datetime.now().strftime("%m-%d-%y") + '.txt'
logging.basicConfig(filename=log_file,level=logging.DEBUG)
logging.info('=============== Rover GPS Communications Server Services Logging Started ' + datetime.now().strftime("%m-%d-%y %H:%M:%S"))

class GpsPoller(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        global gpsd #bring it in scope
        gpsd = gps(mode=WATCH_ENABLE) #starting the stream of info
        self.current_value = None
        self.running = True #setting the thread running to true
 
    def run(self):
        global gpsd
        while gpsp.running:
            gpsd.next()       # this will continue to loop and grab EACH set of gpsd info to clear the buffer

    def shutdown():
        global gpsp
        logging.info('Shutting down gpsd connection.')
        gpsp.running = False
        gpsp.join() # wait for the thread to finish what it's doing
    atexit.register(shutdown)

if __name__ == '__main__':
    gpsp = GpsPoller() # create the thread
    sat_fixed = True
    try:
        gpsp.start() # start it up
################################
#  Main Loop
################################
        while True:
            #  It may take a second or two to get good data
            #  print gpsd.fix.latitude,', ',gpsd.fix.longitude,'  Time: ',gpsd.utc
            NSAT = 0
            if len(gpsd.utc) > 19:
                utc_datetime = gpsd.utc[0:19]
                utc_datetime = utc_datetime.replace('T', ' ')
            if gpsd.satellites == [] or gpsd.satellites == '': pass
            else:
                for SAT in gpsd.satellites:
                    if str(SAT)[42:43] == 'y':
                        NSAT += 1
                if NSAT == 0 and sat_fixed:
                    sat_fixed = False
                    logging.debug('There are no satellites connections at this time: ' + datetime.now().strftime("%m-%d-%y %H:%M:%S") + '. No more log entries until satellites connect.')
                elif NSAT != 0:
                    if sat_fixed == False:
                        sat_fixed = True
                        logging.info('Satellite connections have been reestablished at this time: ' + datetime.now().strftime("%m-%d-%y %H:%M:%S") + '.')
                    stringy = 'UTC Time: ' + utc_datetime + ', #Sat: ' + str(NSAT) + ', Lat: ' + str(gpsd.fix.latitude) + ', Lon: ' + str(gpsd.fix.longitude)
                    logging.debug(stringy)
                    gpsd.satellites = ''
            time.sleep(5)
    except Exception as err:
        logging.error('Encountered an exception: ' + str(err))
        pass
