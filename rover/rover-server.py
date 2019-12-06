#!/usr/bin/python3
#app name: rover-server.py
 
from __future__ import division
from datetime import datetime
import time, curses
import PiMotor
import gimbal
import subprocess
import os, sys
from socket import *
from threading import Thread
import logging
import atexit
import gc

log_file = '/home/rover_logs/rover-log-' + datetime.now().strftime('%m-%d-%y') + '.txt'
logging.basicConfig(filename=log_file,level=logging.DEBUG)
logging.info('=================================== Rover Server App Logging Started ' + datetime.now().strftime('%m-%d-%y %H:%M:%S'))

def shutdown():
    logging.info('Shutdown occurred, shutting down sockets.')
    try:
        gimbal_socket.send(bytes('{quit}', 'utf8'))
        gimbal_socket.close
    except: pass
    try:
        motors_socket.send(bytes('{quit}', 'utf8'))
        motors_socket.close
    except: pass
    try:
        battery_socket.send(bytes('{quit}', 'utf8'))
        battery_socket.close
    except: pass
    try:
        record_socket.send(bytes('{quit}', 'utf8'))
        record_socket.close
    except: pass
atexit.register(shutdown)

pos = gimbal.PTZ() # instantiate Pan/Tilt Gimbal Stepper Motors

#Name of Individual MOTORS - SB Components HAT
wheel_right = PiMotor.Motor("MOTOR1",1)
wheel_left = PiMotor.Motor("MOTOR2",1)
fan_right = PiMotor.Motor("MOTOR3",1)
fan_left = PiMotor.Motor("MOTOR4",1)

#To drive all motors together - SB Components HAT
wheelmotors = PiMotor.LinkedMotors(wheel_right,wheel_left)
fans = PiMotor.LinkedMotors(fan_right,fan_left)

################### DC motors setup - SB Components HAT
base_speed = 50 
max_speed = 100
current_speed = 0
current_direction = 'f'
speed_steps = 5     # the amount of steps to increase/decrease speeds
minimum_turn = 20   # the speed to set wheel for direction left/right
left_degredate = .9

################### Temperature reading setup
TEMP_THRESHOLD = 176    # 176 Farenheit, 80C, RPi recommended temp before core throttle down
TEMP_HYST = 2
fan_on = False
temp_F = 0

# Get battery info
infile = open('/home/rover_logs/batt_cap.txt', 'r') # Code here and below needs to create file if not there.
stored_capacity = str(infile.readline())
infile.close()
infile = open('/home/rover_logs/batt_volt.txt', 'r')
stored_voltage = str(infile.readline())
infile.close()
#print("CPU Voltage: " + stored_voltage[0] + stored_voltage[1] + stored_voltage[2] + "V")
#print("Battery capacity: " + stored_capacity + "%")
#print('Temperature Farenheit Threshold = ' + str(TEMP_THRESHOLD))
#print('Log file location: ' + str(log_file))
################### Setup Gimbal and Stepper Motor Boards
step_amount = 10   # Using degrees

pan_stepper_min = 0
tilt_stepper_min = 0

pan_stepper_max = 350
tilt_stepper_max = 90

pan_home = 180
tilt_home = 0

pan_current = pan_home
tilt_current = tilt_home

# Setup Remote Controller IP address for when available. 

REMOTE_HOST = ''

# Connect to Rover Communications Service - THIS MAY BE UNNECESSARY nulls
# Define separate ports, one for gimbal and one for motors
# This allows this app to wait for ACK per device
rec_comm_conn = 'null'
gbl_comm_conn = 'null'
batt_comm_conn = 'null'
mtrs_comm_conn = 'null'

HOST = '10.10.10.100'
gimbal_PORT = 33000
motors_PORT = 33001
battery_PORT = 33002
record_PORT = 33003
BUFSIZ = 1024
gimbal_ADDR = (HOST, gimbal_PORT)
motors_ADDR = (HOST, motors_PORT)
battery_ADDR = (HOST, battery_PORT)
record_ADDR = (HOST, record_PORT)

gimbal_socket = socket(AF_INET, SOCK_STREAM)
gimbal_socket.connect(gimbal_ADDR)
motors_socket = socket(AF_INET, SOCK_STREAM)
motors_socket.connect(motors_ADDR)
battery_socket = socket(AF_INET, SOCK_STREAM)
battery_socket.connect(battery_ADDR)
record_socket = socket(AF_INET, SOCK_STREAM)
record_socket.connect(record_ADDR)

# These are commands that do not require time to execute and thus no WCK processing:
NoWCK={'31','32','33','67','102','114','115'}

# These are commands that this app supports:
rover_commands={'31','32','33','50','52','54','56','67','72','76','82','102','114','115','258','259','260','261','336','337','393','402',}  
#c = 27          # KEYBOARD ESCape key - kill switch

record_ping_time = datetime.now()
gimbal_ping_time = record_ping_time
battery_ping_time = record_ping_time
motors_ping_time = record_ping_time

previous_rc_batt = '0'
previous_temp = '0'

def log_temp():
    global fan_on, temp_F, stored_capacity, previous_rc_batt, previous_temp

    #Read the temp register
    infile = open('/home/rover_logs/temp.txt','r')
    temp_F = str(infile.readline())
    infile.close()
    old_temp = 0.0  
    try:
        old_temp = float(previous_temp)
    except:
        new_temp = 0.0
        logging.warning('Problem with degree value from file, old_temp = float(previous_temp).')
    try:
        new_temp = float(temp_F)
    except:
        new_temp = 0.0
        logging.warning('Problem with degree value from file, see message below this line.')
    if previous_rc_batt != stored_capacity or (int(old_temp) - int(new_temp)) > 5 or (int(new_temp) - int(old_temp)) > 5 : 
        logging.debug('CPU Battery Capacity: ' + str(stored_capacity) + '%, Temperature: ' + str(new_temp) + 'F, Date/Time= {' + datetime.now().strftime('%m-%d-%y %H:%M:%S') + '}')
        previous_rc_batt = stored_capacity
        previous_temp = temp_F
    if new_temp > TEMP_THRESHOLD:
        fans.forward(100)
        if fan_on == False: 
            logging.debug('Fans ON now')
            fan_on = True

    if new_temp < (TEMP_THRESHOLD - TEMP_HYST):
        fans.stop()
        if fan_on: 
            logging.debug('Fans OFF now')
            fan_on = False
    return new_temp

def set_speed(cmd):
    global current_direction, current_speed, left_degredate
    
    if current_direction == '':current_direction = 'f'
    current_speed = int(cmd)
    if current_direction == 'f':
        wheel_right.forward(current_speed)
        wheel_left.forward(int(current_speed*left_degredate))
    else:
        wheel_right.reverse(current_speed)
        wheel_left.reverse(int(current_speed*left_degredate))
    return 'Slider Speed Set:  right = ' + str(current_speed) + ' left = ' + str(int(current_speed*left_degredate))

def turn_degrees(direction,timer):
    global motor_busy
    motor_busy = True
    if direction == 'left':
        wheel_right.forward(base_speed)
        wheel_left.reverse(base_speed)
    else:
        wheel_right.reverse(base_speed)
        wheel_left.forward(base_speed)
    time.sleep(timer)
    if current_direction == 'f':
        wheel_right.forward(current_speed)
        wheel_left.forward(int(current_speed*left_degredate))
#        logging.debug('current_direction = f, current_speed = ' + str(current_speed) + ', current_speed*left_degredate = ' + str(current_speed*left_degredate))
    elif current_direction == 'r':
        wheel_right.reverse(current_speed)
        wheel_left.reverse(int(current_speed*left_degredate))
#        logging.debug('current_direction = f, current_speed = ' + str(current_speed) + ', current_speed*left_degredate = ' + str(current_speed*left_degredate))
    else:
        wheelmotors.stop()
    motor_busy = False

###########################################
# Wheels and Gimbal Processing Routine
###########################################
def do_work(c):
    global motor_busy, gimbal_busy, current_direction, pos, pan_current, tilt_current, current_speed
    global pan_stepper_min, tilt_stepper_min, pan_stepper_max, tilt_stepper_max, base_speed
    global speed_steps, left_degredate, minimum_turn, step_amount, max_speed
    global pan_home, tilt_home, pan_current, tilt_current

# WHEEL MOTOR Handling Code Below

    
    if c == 115:            # s: STOP
        wheelmotors.stop()
        current_speed = 0
        motor_busy = False
        return 'stopped:  current_speed = ' + str(current_speed)

    elif c == 31:            # MADE UP #: SLOW SPEED FORWARD
        if motor_busy: return ''
        motor_busy = True
        wheel_right.forward(int(base_speed/3))
        wheel_left.forward(int((base_speed/3)*left_degredate))
        current_speed = int(base_speed/3)
        motor_busy = False
        return 'Slow Speed Forward:  current_speed = ' + str(current_speed)

    elif c == 32:            # MADE UP #: MEDIUM SPEED FORWARD
        if motor_busy: return ''
        motor_busy = True
        wheel_right.forward(int(base_speed/2))
        wheel_left.forward(int((base_speed/2)*left_degredate))
        current_speed = int(base_speed/2)
        motor_busy = False
        return 'Medium Speed Forward:  current_speed = ' + str(current_speed)

    elif c == 33:            # !: FULL SPEED FORWARD
        if motor_busy: return ''
        motor_busy = True
        wheel_right.forward(base_speed)
        wheel_left.forward(int(base_speed*left_degredate))
        current_speed = base_speed
        motor_busy = False
        return 'Full Speed Forward:  current_speed = ' + str(current_speed)

    elif c == 102:            # f: FORWARD both wheels
        if motor_busy: return ''
        motor_busy = True
        wheel_right.forward(current_speed)
        wheel_left.forward(int(current_speed*left_degredate))
        current_direction = 'f'
        motor_busy = False
        return 'FORWARD:  right = ' + str(current_speed) + ' left = ' + str(int(current_speed*left_degredate))
        
    elif c == 114:            # r: REVERSE both wheels
        if motor_busy: return ''
        motor_busy = True
        wheel_right.reverse(current_speed)
        wheel_left.reverse(int(current_speed*left_degredate))
        current_direction = 'r'
        motor_busy = False
        return 'REVERSE:  right = ' + str(current_speed) + ' left = ' + str(int(current_speed*left_degredate))

    elif c == 258:                      # DOWN arrow: Slow DOWN
        if motor_busy: return ''
        motor_busy = True
        if current_direction == '':
            motor_busy = False
            return 'You must choose a direction before slowing down.'
        elif current_speed > 0:
            current_speed -= speed_steps
            if current_speed < 0: current_speed = 0

            if current_direction == 'f':
                wheel_right.forward(current_speed)
                wheel_left.forward(int(current_speed*left_degredate))
            else:
                wheel_right.reverse(current_speed)
                wheel_left.reverse(int(current_speed*left_degredate))
            motor_busy = False
            return 'slow down:  right = ' + str(current_speed) + ' left = ' + str(int(current_speed*left_degredate))
        else:
            motor_busy = False
            return 'current_speed = ' + str(current_speed) + ', the rover has stopped.'

    elif c == 259:                      # UP arrow: Speed UP
        if motor_busy: return ''
        motor_busy = True
        if current_direction == '':
            motor_busy = False
            return 'You must choose a direction before speeding up.'
        elif current_speed < 100:
            current_speed += speed_steps
            if current_speed > 100: current_speed = 100
            if current_direction == 'f':
                wheel_right.forward(current_speed)
                wheel_left.forward(int(current_speed*left_degredate))
            else:
                wheel_right.reverse(current_speed)
                wheel_left.reverse(int(current_speed*left_degredate))
            motor_busy = False
            return 'Speed Up:  right = ' + str(current_speed) + ' left = ' + str(int(current_speed*left_degredate))
        else:
            motor_busy = False
            return 'current_speed = ' + str(current_speed) + ', the rover is going as fast as it can.'

    elif c == 260:                      # LEFT arrow: Turn LEFT
        if motor_busy: return ''
        motor_busy = True
        if current_direction == '':
            motor_busy = False
            return 'You must choose a direction before turning left.'
        if current_direction == 'f':
            wheel_left.forward(0)
            time.sleep(.5)
            wheel_left.forward(int(current_speed*left_degredate))
            motor_busy = False
            return 'FORWARD left turn, speed left = ' + str(int(current_speed*left_degredate))
        if current_direction == 'r':
            wheel_left.reverse(0)
            time.sleep(.5)
            wheel_left.reverse(int(current_speed*left_degredate))
            motor_busy = False
            return 'REVERSE left turn, speed left = ' + str(int(current_speed*left_degredate))
        
    elif c == 261:                      # RIGHT arrow: Turn RIGHT
        if motor_busy: return ''
        motor_busy = True
        if current_direction == '':
            motor_busy = False
            return 'You must choose a direction before turning right.'
        if current_direction == 'f':
            wheel_right.forward(0)
            time.sleep(.5)
            wheel_right.forward(current_speed)
            motor_busy = False
            return 'FORWARD right turn, speed right = ' + str(int(current_speed))
        if current_direction == 'r':
            wheel_right.reverse(0)
            time.sleep(.5)
            wheel_right.reverse(current_speed)
            motor_busy = False
            return 'REVERSE right turn, speed right = ' + str(int(current_speed))
        
    elif c == 50:                   # 2 = Spin 180 degrees right
        if motor_busy: return ''
        turn_degrees('right',2)
        return 'Turned 180 degrees left'

    elif c == 52:                   # 4 = Turn 45 degrees to the left
        if motor_busy: return ''
        turn_degrees('left',.5)
        return 'Turned 45 degrees left'

    elif c == 54:                   # 6 = Turn 45 degrees to the right
        if motor_busy: return ''
        turn_degrees('right',.5)
        return 'Turned 45 degrees right'

    elif c == 56:                   # 8 = Turn around in place - NOT on remote UI
        if motor_busy: return ''
        turn_degrees('right',4)
        return 'Turned 360 degrees right'


# CAMERA / GIMBAL I/O Handling Below

    elif c == 393:                      # SHIFT LEFT arrow - Pan Camera Left
        if gimbal_busy: return ''
        pan_current += step_amount
        if pan_current > pan_stepper_max:
            pan_current = pan_stepper_max
            return 'left arrow invalid, pan_current = ' + str(pan_current)
        gimbal_busy = True
        if pan_current < pan_stepper_max:
            pos.goto((360-pan_current), tilt_current)
        gimbal_busy = False
        return 'shift left: Pan Camera Left, pan_current = ' + str(pan_current)
        
    elif c == 402:                      # SHIFT RIGHT arrow - Pan Camera Right
        if gimbal_busy: return ''
        pan_current -= step_amount
        if pan_current < pan_stepper_min:
            pan_current = pan_stepper_min
            return 'right arrow invalid, pan_current = ' + str(pan_current)
        gimbal_busy = True
        if pan_current > pan_stepper_min:
            pos.goto((360-pan_current), tilt_current)
        gimbal_busy = False
        return 'shift right: Pan Camera Right, pan_current = ' + str(pan_current)
        
    elif c == 336:                      # SHIFT DOWN arrow - Tilt Camera Down
        if gimbal_busy: return ''
        tilt_current -= step_amount
        if tilt_current < tilt_stepper_min:
            tilt_current = tilt_stepper_min
            return 'down arrow invalid, tilt_current = ' + str(tilt_current)
        gimbal_busy = True
        if tilt_current > tilt_stepper_min:
            pos.goto(pan_current, tilt_current)
        gimbal_busy = False
        return 'shift down: Tilt Camera Down, pan_current = ' + str(tilt_current)
        
    elif c == 337:                      # SHIFT UP arrow - Tilt Camera Up
        if gimbal_busy: return ''
        tilt_current += step_amount
        if tilt_current > tilt_stepper_max:
            tilt_current = tilt_stepper_max
            return 'up  arrow invalid, tilt_current max = ' + str(tilt_current)
        gimbal_busy = True
        if tilt_current < tilt_stepper_max:
            pos.goto(pan_current, tilt_current)
        gimbal_busy = False
        return 'shift up: Tilt Camera Up, tilt_current = ' + str(tilt_current) + ', pan_current = ' + str(pan_current)

    elif c == 524:                              # SHIFT-Alt DOWN arrow to force head down, ignores tilt_current
        if gimbal_busy: return ''
        gimbal_busy = True
        pan_current = 180
        tilt_current = 0
        pos.goto(pan_current, tilt_current)
        gimbal_busy = False
        return 'Force DOWN tilt = ' + str(tilt_current)

    elif c == 67:                           # C for CALIBRATE
        if gimbal_busy: return ''
        gimbal_busy = True
        pos = gimbal.PTZ() # instantiate Pan/Tilt Gimbal Stepper Motors

        pan_current = 180
        tilt_current = 0
        gimbal_busy = False
        return 'Calibration Complete pan = ' + str(pan_current) + ', tilt = ' + str(tilt_current)

    elif c == 72:                           # H for HOME
        if gimbal_busy: return ''
        gimbal_busy = True
        if pan_current == pan_home and tilt_current == tilt_home:
            time.sleep(.2)  # waste time when nothing is going to happen and comm needs to delay ACK to remote
        pan_current = pan_home
        tilt_current = tilt_home
        pos.goto(pan_current, tilt_current)
        gimbal_busy = False
        return 'HOME pan = ' + str(pan_current) + ', tilt = ' + str(tilt_current)

    elif c == 76:                           # L for LEFT 90 degrees
        if gimbal_busy: return ''
        gimbal_busy = True
        pan_current = 85
        tilt_current = 0
        pos.goto(pan_current, tilt_current)
        gimbal_busy = False
        return '90 degrees LEFT pan = ' + str(pan_current) + ', tilt = ' + str(tilt_current)

    elif c == 82:                           # R for RIGHT 90 degrees
        if gimbal_busy: return ''
        gimbal_busy = True
        pan_current = 270
        tilt_current = 0
        pos.goto(pan_current, tilt_current)
        gimbal_busy = False
        return '90 degrees RIGHT pan = ' + str(pan_current) + ', tilt = ' + str(tilt_current)

    else:
        return str(c)

###########################################
# Initialize RECORD Socket
###########################################
def init_record():
    global record_socket, rec_comm_conn

    error_skip = False
    msg = ''
    record_socket.settimeout(.8)
    try:
        msg = record_socket.recv(1024).decode('utf8')  # Check for remote and server init commands
    except:
        error_skip = True 
        logging.warning('Record socket timed out for Connected.')
        pass
    if not error_skip and msg == "Connected":                        # This msg is from server asking for name
        record_socket.send(bytes('rover', 'utf8'))  # This is the name of this user: rover

    time.sleep(.1)
    error_skip = False
    msg = ''
    try:
        msg = record_socket.recv(1024).decode('utf8')  # Check for remote and server init commands
    except:
        error_skip = True 
        logging.warning('Record socket timed out for Active.')
        pass
    if not error_skip and msg == "Active":  # This is a server init command
        rec_comm_conn = msg

###########################################
#     Initialize GIMBAL Socket
###########################################
def init_gimbal():
    global gimbal_socket, gbl_comm_conn

    error_skip = False
    msg = ''
    gimbal_socket.settimeout(.8)
    try:
        msg = gimbal_socket.recv(1024).decode('utf8')  # Check for remote and server init commands
    except:
        error_skip = True 
        logging.warning('Gimbal socket timed out for Connected.')
        pass
    if not error_skip and msg == "Connected":                        # This msg is from server asking for name
        gimbal_socket.send(bytes('rover', 'utf8'))  # This is the name of this user: rover

    time.sleep(.1)
    error_skip = False
    msg = ''
    try:
        msg = gimbal_socket.recv(1024).decode('utf8')  # Check for remote and server init commands
    except:
        error_skip = True 
        logging.warning('Gimbal socket timed out for Active.')
        pass
    if not error_skip and msg == "Active":  # This is a server init command
        gbl_comm_conn = msg

##################################################
#     Initialize Battery Socket
##################################################
def init_battery():
    global battery_socket, batt_comm_conn

    error_skip = False
    msg = ''
    battery_socket.settimeout(.8)
    try:
        msg = battery_socket.recv(1024).decode('utf8')  # Check for remote and server init commands
    except:
        error_skip = True 
        logging.warning('Battery socket timed out for Connected.')
        pass
    if not error_skip and msg == "Connected":                        # This msg is from server asking for name
        battery_socket.send(bytes('rover', 'utf8'))  # This is the name of this user: rover

    time.sleep(.1)
    error_skip = False
    msg = ''
    try:
        msg = battery_socket.recv(1024).decode('utf8')  # Check for remote and server init commands
    except:
        error_skip = True 
        logging.warning('Battery socket timed out for Active.')
        pass
    if not error_skip and msg == "Active":  # This is a server init command
        batt_comm_conn = msg

###########################################
#     Initialize WHEELS/MOTORS Socket
###########################################
def init_motors():
    global motors_socket, mtrs_comm_conn
    
    error_skip = False
    msg = ''
    motors_socket.settimeout(.8)
    try:
        msg = motors_socket.recv(1024).decode('utf8')  # Check for server init commands
    except:
        error_skip = True 
        logging.warning('Motors socket timed out for Connected.')
        pass

    if msg == "Connected":                        # This msg is from server asking for name
        motors_socket.send(bytes('rover', 'utf8'))  # This is the name of this user: rover

    time.sleep(.1)
    error_skip = False
    msg = ''
    try:
        msg = motors_socket.recv(1024).decode('utf8')  # Check for rover init commands
    except:
        error_skip = True 
        logging.warning('Motors socket timed out for Active.')
        pass
    if not error_skip and msg == "Active":  # This is a server init command
        mtrs_comm_conn = msg

##################################################
# Main Processing Routine - TTY Display and Motors
##################################################
def main():
    global base_speed, current_speed, current_direction, speed_steps, minimum_turn
    global second_timer, left_degredate, gimbal_ping_time, motors_ping_time
    global pan_current, tilt_current, pan_center, tilt_center, step_amount
    global temp_F, pos, motor_busy, gimbal_busy, stored_capacity
    global gimbal_ping_time, motors_ping_time, battery_ping_time, record_ping_time
    global record_socket, gimbal_socket, battery_socket, motors_socket
    global rec_comm_conn, gbl_comm_conn, batt_comm_conn, mtrs_comm_conn
    global gimbal_ADDR, motors_ADDR, battery_ADDR, record_ADDR
    global max_speed, REMOTE_HOST

    motor_busy = False
    gimbal_busy = False

    init_record()
    init_gimbal()
    init_battery()
    init_motors()

    second_timer = int(datetime.now().strftime("%S")) + 1 # set timer to 1 second, so temp logs and screen messages startup
    if second_timer > 59: second_timer -= 59

##############################################
# Main Processing Loop
    while True:
        # get keyboard input, returns -1 if none available

###########################################
# Handle RECORD port communications
###########################################
        msg = ''
        record_socket.settimeout(.01)
        try:
            msg = record_socket.recv(1024).decode('utf8')
        except: pass

        if msg == 'rover: ACK':
            pass  # get rid of repeat from server

        elif msg == 'remote: ping':
            record_socket.send(bytes('ACK', 'utf8'))
            record_ping_time = datetime.now()

        elif msg == 'remote: snapshot':
            os.system('touch /home/build/picam/hooks/start_record')   # Had to shoot video to grab a frame
            time.sleep(.1)
            os.system('touch /home/build/picam/hooks/stop_record')
            snaptime = str(datetime.now().strftime('%y-%m-%d_%H-%M-%S'))
            os.system('ffmpeg -loglevel 0 -y -i /home/build/picam/rec/archive/*.ts -c:v copy -c:a copy -bsf:a aac_adtstoasc /home/apps/rover_video.mp4')
            os.system('ffmpeg -loglevel 0 -y -i /home/apps/rover_video.mp4 -vframes 1 /home/pictures/rover_snapshot' + snaptime + '.jpg')
            record_socket.send(bytes('ACK', 'utf8'))    # Send ACK to complete command handshake
            logging.debug('ACK Sent for filename: /home/pictures/rover_snapshot' + snaptime + '.jpg')
            os.system('rm /home/build/picam/rec/*.ts')
            os.system('rm /home/build/picam/state/*.ts')

        elif msg == 'remote: rec_start':
            os.system('touch /home/build/picam/hooks/start_record')
            record_socket.send(bytes('ACK', 'utf8'))    # Send ACK to complete command handshake
            logging.debug('ACK Sent for Completed Remote Record Command: rec_start')

        elif msg == 'remote: rec_stop':
            os.system('touch /home/build/picam/hooks/stop_record')
            snaptime = str(datetime.now().strftime('%y-%m-%d_%H-%M-%S'))
            os.system('ffmpeg -loglevel 0 -y -i /home/build/picam/rec/archive/*.ts -c:v copy -c:a copy -bsf:a aac_adtstoasc /home/pictures/rover_video' + snaptime + '.mp4')
            record_socket.send(bytes('ACK', 'utf8'))    # Send ACK to complete command handshake
            logging.debug('ACK Sent for filename: rover_video' + snaptime + '.mp4')
            os.system('rm /home/build/picam/rec/archive/*.ts')

###########################################
# Handle GIMBAL port communications
###########################################
        msg = ''
        gimbal_socket.settimeout(.01)
        try:
            msg = gimbal_socket.recv(1024).decode('utf8')
        except: pass

        if msg == 'rover: ACK':
            pass  # get rid of repeat from server

        elif 'remote: ping' in msg:
            gimbal_socket.send(bytes('ACK', 'utf8'))
            gimbal_ping_time = datetime.now()

        elif 'remote:' in msg:
            cmd = msg.replace('remote: ', '')
            if cmd in rover_commands:
                if cmd not in NoWCK:
                    gimbal_socket.send(bytes('WAK', 'utf8'))
                    logging.debug('Gimbal WAK Sent to Remote for: ' + str(msg))
                try:
                    c = int(cmd)
                    tmp_msg = do_work(c)
                    logging.debug('Remote Gimbal Command do_work completed: ' + tmp_msg)
                except: 
                    logging.warning('Received INVALID Remote Gimbal Command (above)')
                    time.sleep(.2)  # Give remote some time to sort things out
                    pass
                gimbal_socket.send(bytes('ACK', 'utf8'))    # Send ACK to complete command handshake
                logging.debug('ACK Sent for Completed Remote Gimbal Command: ' + tmp_msg)

            else: 
                logging.warning('Received INVALID Remote Gimbal Command: [' + msg + ']')

########################################
# Handle BATTERY port communications
########################################
        msg = ''
        battery_socket.settimeout(.1)
        try:
            msg = battery_socket.recv(128).decode('utf8')
        except Exception as err: 
#            logging.warning('Exception Remote Battery Command: [' + str(err) + ']')
            pass

        if msg == 'rover: ACK':
            logging.debug('Remote Battery Command received: [' + str(msg) + '] @ ' + datetime.now().strftime('%m-%d-%y %H:%M:%S'))
            pass  # get rid of repeat from server

        elif 'remote: ping' in msg:
            logging.debug('Remote Battery Command received: [' + str(msg) + '] @ ' + datetime.now().strftime('%m-%d-%y %H:%M:%S'))
            battery_socket.send(bytes('ACK', 'utf8'))
            battery_ping_time = datetime.now()

        elif msg == 'remote: battery':
            logging.debug('Remote Battery Command received: [' + str(msg) + '] @ ' + datetime.now().strftime('%m-%d-%y %H:%M:%S'))
            infile = open('/home/rover_logs/batt_cap.txt', 'r') 
            stored_capacity = str(infile.readline())
            infile.close()
            if stored_capacity == ' ':
                stored_capacity = '-1'
            logging.debug('Rover Battery response sent: [' + stored_capacity + ']')
            battery_socket.send(bytes(stored_capacity, 'utf8'))
            battery_ping_time = datetime.now()

###########################################
# Handle WHEELS/MOTORS port communications
###########################################

        msg = ''
        motors_socket.settimeout(.01)
        try:
            msg = motors_socket.recv(1024).decode('utf8')
        except: pass

        if msg == 'rover: ACK':
            pass  # get rid of repeat from server

        elif 'remote: speed=' in msg:
            cmd = msg.replace('remote: speed=', '')
            try:
                cmd_int = int(float(cmd))
                if cmd_int > max_speed:
                    logging.warning('Remote Motors Command set_speed invalid: ' + str(cmd_int))
                    cmd_int = current_speed
            except:
                logging.warning('Remote Motors Command set_speed exception: ' + msg)
                cmd_int = current_speed
            logging.debug('Remote SPEED cmd received set to: [' + str(cmd_int) + ']')
            tmp_msg = set_speed(cmd_int)
            logging.debug('Remote Motors Command set_speed completed: ' + tmp_msg)

        elif 'remote: ping' in msg:
            motors_socket.send(bytes('ACK', 'utf8'))
            motors_ping_time = datetime.now()

        elif 'remote:' in msg:                          # This is after init/startup and should be valid
            cmd = msg.replace('remote: ', '')
            logging.debug('remote Motors cmd received: [' + str(cmd) + ']')
            if cmd in rover_commands:
                if cmd not in NoWCK:
                    motors_socket.send(bytes('WAK', 'utf8'))
                    logging.debug('Motors WAK Sent to Remote for: ' + str(msg))
                try:
                    c = int(cmd)
                    tmp_msg = do_work(c)
                    logging.debug('Remote Motors Command do_work completed: ' + tmp_msg)
                except: 
                    logging.warning('Received INVALID Remote Motors Command (above)')
                    time.sleep(.2)  # Give remote some time to sort things out
                    pass
                motors_socket.send(bytes('ACK', 'utf8'))    # Send ACK to complete command handshake
                logging.debug('ACK Sent for Completed Remote Motors Command: ' + tmp_msg)
#            else: 
#                logging.warning('Received INVALID Remote Motors Command: [' + msg + ']')

###########################################
#     Handle remote communications
###########################################
        now_timer = int(datetime.now().strftime("%S"))
        if second_timer == now_timer:
            gc.collect()
            if REMOTE_HOST == '':
                REMOTE_HOST='10.10.10.101'
                temp = subprocess.Popen(args=['ping -c 1 ' + REMOTE_HOST], stdout=subprocess.PIPE, shell=True)
                value, err = temp.communicate()
                if '1 received' in str(value):
                    logging.debug('Remote HOST on LAN with IP: ' + REMOTE_HOST + ' @ ' + datetime.now().strftime('%m-%d-%y %H:%M:%S'))
                    remote_offline = False
                else:
                    REMOTE_HOST == ''

            current_temp=log_temp()
            infile = open('/home/rover_logs/batt_cap.txt', 'r')
            stored_capacity = str(infile.readline())
            infile.close()
#            stored_capacity = str(int(stored_capacity)-75)     # This is to test capacity offset by 75% for shutdown
            if int(stored_capacity) < 5:
                logging.critical('Battery capacity is too low to continue app and is shutting down now.')
                shutdown()
                os.system('shutdown -P now')

            if REMOTE_HOST != '':
                try:
                    temp = subprocess.check_output(['ping', '-c', '1', REMOTE_HOST,'-W','1'])
                    logging.debug('ping to Remote Control at ' + REMOTE_HOST + ' connected.')
                    if "b''" in str(temp): REMOTE_HOST = ''
                except: 
                    REMOTE_HOST = ''
                    if not remote_offline:
                        logging.debug('########## Remote is not connected @ ' + datetime.now().strftime('%m-%d-%y %H:%M:%S') + '.')
                        remote_offline = True
                    pass
                if REMOTE_HOST != '':
                    remote_offline = False
                    try:
                        if (datetime.now()-record_ping_time).seconds > 15:
                            rec_comm_conn = 'Timeout'
                            logging.warning('***** record_ping_time timed out: ' + datetime.now() +  ' - ' + battery_ping_time + ' > 15')
                            try:
                                record_socket.send(bytes('{quit}', 'utf8'))
                                record_socket.close
                            except: pass
                            os.system('systemctl restart record-start')
                            logging.warning('record_ping_time exceeded and restarted record-start.service @ ' + datetime.now().strftime('%m-%d-%y %H:%M:%S'))
                            time.sleep(.5)
                            try:
                                record_socket = socket(AF_INET, SOCK_STREAM)
                                record_socket.connect(record_ADDR)
                            except Exception as e: 
                                logging.error('record_socket failed:' + str(e))
                                pass
                            init_record()
                             
                        if (datetime.now()-gimbal_ping_time).seconds > 15:
                            gbl_comm_conn = 'Timeout'
                            logging.warning('***** gimbal_ping_time timed out: ' + datetime.now() +  ' - ' + battery_ping_time + ' > 15')
                            try:
                                gimbal_socket.send(bytes('{quit}', 'utf8'))
                                gimbal_socket.close
                            except: pass
                            os.system('systemctl restart gimbal-start')
                            logging.warning('gimbal_ping_time exceeded and restarted gimbal-start.service @ ' + datetime.now().strftime('%m-%d-%y %H:%M:%S'))
                            time.sleep(.5)
                            try:
                                gimbal_socket = socket(AF_INET, SOCK_STREAM)
                                gimbal_socket.connect(gimbal_ADDR)
                            except Exception as e: 
                                logging.error('gimbal_socket failed:' + str(e))
                                pass
                            init_gimbal()
                             
                        if (datetime.now()-battery_ping_time).seconds > 15:
                            batt_comm_conn = 'Timeout'
                            logging.warning('***** battery_ping_time timed out: ' + datetime.now() +  ' - ' + battery_ping_time + ' > 15')
                            try:
                                battery_socket.send(bytes('{quit}', 'utf8'))
                                battery_socket.close
                            except: 
                                logging.warning('battery {quit} or close failed.')
                                pass
                            temp = subprocess.Popen(args=['systemctl stop battery-start'], stdout=subprocess.PIPE, shell=True)
                            value, err = temp.communicate()
                            temp = subprocess.Popen(args=['systemctl restart battery-start'], stdout=subprocess.PIPE, shell=True)
                            value, err = temp.communicate()
#                            os.system('systemctl restart battery-start')
                            logging.warning('battery_ping_time exceeded and restarted battery-start.service @ ' + datetime.now().strftime('%m-%d-%y %H:%M:%S'))
                            time.sleep(.5)
                            try:
                                battery_socket = socket(AF_INET, SOCK_STREAM)
                                battery_socket.connect(battery_ADDR)
                            except Exception as e: 
                                logging.error('battery_socket failed:' + str(e))
                                pass
                            init_battery()
                            
                        if (datetime.now()-motors_ping_time).seconds > 15:
                            mtrs_comm_conn = 'Timeout'
                            logging.warning('***** motors_ping_time timed out: ' + datetime.now() +  ' - ' + battery_ping_time + ' > 15')
                            try:   # Kill motors
                                wheelmotors.stop()
                            except: pass
                            try:
                                motors_socket.send(bytes('{quit}', 'utf8'))
                                motors_socket.close
                            except: pass
                            os.system('systemctl restart motors-start')
                            logging.warning('motors_ping_time exceeded and restarted motors-start.service @ ' + datetime.now().strftime('%m-%d-%y %H:%M:%S'))
                            time.sleep(.5)
                            try:
                                motors_socket = socket(AF_INET, SOCK_STREAM)
                                motors_socket.connect(motors_ADDR)
                            except Exception as e: 
                                logging.error('motors_socket failed:' + str(e))
                                pass
                            init_motors()
                    except: pass

            second_timer=int(datetime.now().strftime("%S"))+10
            if second_timer >= 60: second_timer -= 60

# start the main program
main()
