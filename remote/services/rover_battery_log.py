'''Server for multithreaded (asynchronous) chat application.'''
from socket import AF_INET, socket, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR
import logging, subprocess
from datetime import datetime
import time, sys, signal
import atexit

log_file = '/home/remote_logs/rover-battery-log-' + datetime.now().strftime('%m-%d-%y') + '.txt'
logging.basicConfig(filename=log_file,level=logging.DEBUG)
logging.info('==================== Rover Battery Capacity Communications Client Logging Started ' + datetime.now().strftime('%m-%d-%y %H:%M:%S'))

def shutdown(*kwarg):
    logging.info('Shutdown occurred, shutting battery socket down.')
    try:
        battery_socket.send(bytes('{quit}', 'utf8'))
        battery_socket.close
    except: pass
    sys.exit()
atexit.register(shutdown)
#signal.signal(signal.SIGTERM, shutdown)

try:
    infile = open('/home/remote_logs/rover_comm.txt', 'r')
    stored_capacity = str(infile.readline())
    infile.close()
    if stored_capacity == '':
        outfile = open('/home/remote_logs/rover_comm.txt', 'w')
        outfile.write('0000')
        outfile.close()
except:
    outfile = open('/home/remote_logs/rover_comm.txt', 'w')
    outfile.write('0000')
    outfile.close()

try:
    infile = open('/home/remote_logs/batt_cap-rover.txt', 'r')
    stored_capacity = str(infile.readline())
    infile.close()
    if stored_capacity == '':
        outfile = open('/home/remote_logs/batt_cap-rover.txt', 'w')
        outfile.write('10')
        outfile.close()
except:
    outfile = open('/home/remote_logs/batt_cap-rover.txt', 'w')
    outfile.write('10')
    outfile.close()

# Connect to rover comm service - First ping rover static IP so it shows up in arp
#temp = subprocess.Popen(args=['ping -c 1 10.10.10.100'], stdout=subprocess.PIPE, shell=True)
#value, err = temp.communicate()
# Reverse Address the rover for IP address - this can fail if not found, needs exception handling.
#temp = subprocess.Popen(args=['arp -a | grep rover'], stdout=subprocess.PIPE, shell=True)
#value, err = temp.communicate()
#HOST=str(value[7:19])
#HOST=HOST.replace("b","")
#HOST=HOST.replace("'","")
#logging.debug('HOST Address for rover is ' + HOST)
HOST = '10.10.10.100'
battery_PORT = 33002
battery_ADDR = (HOST, battery_PORT)
batt_lost_ping_cnt = 0
try:
    battery_socket = socket(AF_INET, SOCK_STREAM)
    battery_socket.connect(battery_ADDR)
    battery_socket.settimeout(1)
except:
    batt_lost_ping_cnt = 1
    pass

if batt_lost_ping_cnt == 0:
    msg = battery_socket.recv(128).decode('utf8')
    if msg == 'Connected':
        battery_socket.send(bytes('remote', 'utf8'))
        logging.info('Remote Control to Rover Server Battery init: Connected @ ' + datetime.now().strftime('%m-%d-%y %H:%M:%S'))
    time.sleep(.3)
    try:
        msg = ''
        msg = battery_socket.recv(128).decode('utf8')
        logging.debug('Remote Control received: ' + msg)
    except: 
        logging.error('Remote Control init: No Active Completion')
        batt_lost_ping_cnt += 1
        pass
    battery_socket.send(bytes('ping', 'utf8'))
    logging.debug('Remote Control init: Battery ping sent to Rover.')
    time.sleep(.5)

    infile = open('/home/remote_logs/rover_comm.txt','r')
    rover_cmd = str(infile.readline())
    infile.close()
    try:
        msg = ''
        msg = battery_socket.recv(128).decode('utf8')
        if 'ACK' in msg: 
            logging.debug('Remote Control init: Battery ping:ACK with Rover')
            rover_cmd = rover_cmd[0:2] + 'B' + rover_cmd[3]
        else: 
            logging.warning('Remote Control init: Battery NO ping:ACK with Rover, instead: ' + msg)
            batt_lost_ping_cnt += 1
            rover_cmd = rover_cmd[0:2] + '0' + rover_cmd[3]
    except Exception as err:
        logging.warning('Remote Control init Battery Exception: ' + str(err))
        batt_lost_ping_cnt += 1
        rover_cmd = rover_cmd[0:2] + '0' + rover_cmd[3]
        pass
    outfile = open('/home/remote_logs/rover_comm.txt','w')
    outfile.write(rover_cmd)
    outfile.close()

battery_capacity = ''
infile = open('/home/remote_logs/batt_cap-rover.txt', 'r')
stored_capacity = str(infile.readline())
infile.close()

class Rover_batt_poll(object):
    def __init__(self):
        self.poll_rover()

    def poll_rover(self):
        global stored_capacity, battery_capacity, batt_lost_ping_cnt, battery_socket
        #, battery_ADDR
        
        battery_socket.settimeout(1)
        while True:
            try:
                battery_socket.send(bytes('battery', 'utf8'))
                logging.debug("Rover 'battery' command bcast @ " + datetime.now().strftime('%m-%d-%y %H:%M:%S'))
            except Exception as err: 
                logging.error('Rover BATTERY command failed: ' + str(err) + ' @ ' + datetime.now().strftime('%m-%d-%y %H:%M:%S'))
                battery_capacity = '-1'
                pass
    #        if batt_lost_ping_cnt == 0:
            time.sleep(.5)
            try:
                tmp_battery_msg = ''
                tmp_battery_msg = battery_socket.recv(128).decode('utf8')
                logging.debug("Rover 'battery' value response: " + str(tmp_battery_msg) + ', ' + datetime.now().strftime('%m-%d-%y %H:%M:%S'))
                tmp_battery_msg = tmp_battery_msg.replace('remote: battery', '')
                tmp_battery_msg = tmp_battery_msg.replace('rover: ', '')
                logging.debug('Rover battery value filtered: [' + str(tmp_battery_msg) + '], ' + datetime.now().strftime('%m-%d-%y %H:%M:%S'))
                if tmp_battery_msg != '': 
                    try:
                        battery_capacity = str(int(tmp_battery_msg))
                        logging.debug('Received rover battery capacity: ' + battery_capacity + ', ' + datetime.now().strftime('%m-%d-%y %H:%M:%S'))
                    except Exception as err:
                        battery_capacity = '-1'
                        logging.warning('Exception received erroneous rover battery capacity: ' + str(tmp_battery_msg) + ', err: ' + str(err) + ', ' + datetime.now().strftime('%m-%d-%y %H:%M:%S'))
                else: 
                    battery_capacity = '-1'
                    logging.warning("Rover 'battery' NULL response " + datetime.now().strftime('%m-%d-%y %H:%M:%S'))
            except Exception as err:
                battery_capacity = '-1'
                logging.warning("Exception 'battery' value response [" + str(err) + '] ' + datetime.now().strftime('%m-%d-%y %H:%M:%S'))
                pass

            if battery_capacity == '-1':
                batt_lost_ping_cnt += 1
                if batt_lost_ping_cnt > 4:
                    try:
                        logging.debug('Remote Control Battery issuing {quit} and close.')
                        try:
                            battery_socket.send(bytes('{quit}', 'utf8'))              #### Added code here to close socket and restart.
                            battery_socket.close()
                            logging.debug('Remote Control Battery Completed {quit} and closed.')
                        except Exception as err: 
                            logging.debug('Exception {quit} failed err: ' + str(err) + ', ' + datetime.now().strftime('%m-%d-%y %H:%M:%S'))
                            pass
                            
                        logging.critical('Restarting Remote Control to Rover Server Battery @ ' + datetime.now().strftime('%m-%d-%y %H:%M:%S'))
    #                    temp = subprocess.Popen(args=['systemctl stop batt_rover-start'], stdout=subprocess.PIPE, shell=True)
    #                    value, err = temp.communicate()
    #                    temp = subprocess.Popen(args=['systemctl start batt_rover-start'], stdout=subprocess.PIPE, shell=True)
    #                    value, err = temp.communicate()
    #                    sys.exit()
                        
                        battery_socket = socket(AF_INET, SOCK_STREAM)
                        battery_socket.connect(battery_ADDR)
#                        battery_socket.settimeout(.8)
                        tmp_battery_msg = battery_socket.recv(128).decode('utf8')
                        if tmp_battery_msg == 'Connected':
                            battery_socket.send(bytes('remote', 'utf8'))
                            logging.warning('Restarted Remote Control to Rover Server Battery: Connected @ ' + datetime.now().strftime('%m-%d-%y %H:%M:%S'))
                        time.sleep(.2)
                        tmp_battery_msg = battery_socket.recv(128).decode('utf8')
                        logging.debug('Restarted Remote Control to Rover Server Battery: ' + str(tmp_battery_msg))
                        batt_lost_ping_cnt = 0
                        infile = open('/home/remote_logs/rover_comm.txt','r')
                        rover_cmd = str(infile.readline())
                        infile.close()
                        rover_cmd = rover_cmd[0:2] + 'B' + rover_cmd[3]
                        outfile = open('/home/remote_logs/rover_comm.txt','w')
                        outfile.write(rover_cmd)
                        outfile.close()
                    except Exception as err: 
                        logging.error('Restart Remote Control to Rover Server Battery FAILED: ' + str(err))
                        pass
                        infile = open('/home/remote_logs/rover_comm.txt','r')
                        rover_cmd = str(infile.readline())
                        infile.close()
                        rover_cmd = rover_cmd[0:2] + '0' + rover_cmd[3]
                        outfile = open('/home/remote_logs/rover_comm.txt','w')
                        outfile.write(rover_cmd)
                        outfile.close()
            else:
                batt_lost_ping_cnt = 0
                infile = open('/home/remote_logs/rover_comm.txt','r')
                rover_cmd = str(infile.readline())
                infile.close()
                if len(rover_cmd) < 4:
                    logging.error('Remote Control rover_comm.txt file corrupt: ' + str(rover_cmd))
                    rover_cmd = 'RGBW'
                rover_cmd = rover_cmd[0:2] + 'B' + rover_cmd[3]
                outfile = open('/home/remote_logs/rover_comm.txt','w')
                outfile.write(rover_cmd)
                outfile.close()
            
            if battery_capacity != str(stored_capacity) and battery_capacity != '-1' and int(battery_capacity) < 101:
                outfile = open('/home/remote_logs/batt_cap-rover.txt', 'w');
                outfile.write(battery_capacity)
                outfile.close()
                stored_capacity = battery_capacity
            time.sleep(5)
#        self.poll_rover()
Rover_batt_poll()
