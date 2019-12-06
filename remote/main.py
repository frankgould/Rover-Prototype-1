#! /usr/bin/python3
import os
os.environ['KIVY_GL_BACKEND']='gl'
import subprocess
from datetime import datetime
import time
from socket import AF_INET, socket, SOCK_STREAM
from threading import Thread 
import configparser
import kivy
from kivy.lang import Builder
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
import atexit
import logging, sys
from PIL import Image
import gc

# setup logging
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
parent=logger.__dict__['parent']
logger.info('=============== Remote Control Main App Logging Started ' + datetime.now().strftime('%m-%d-%y %H:%M:%S'))

def shutdown():
  logger.info('Shutdown occurred, shutting down gimbal, wheels, and record sockets.')
  try:
    gimbal_socket.send(bytes('{quit}', 'utf8'))
    gimbal_socket.close
  except: pass
  try:
    motors_socket.send(bytes('{quit}', 'utf8'))
    motors_socket.close
  except: pass
  try:
    record_socket.send(bytes('{quit}', 'utf8'))
    record_socket.close
  except: pass
atexit.register(shutdown)

# Need to determine if these two lines need to execute here or shutdown above (There has been some issues with restarting batt_rover-start):
#  os.system('systemctl stop batt_rover-start')
#os.system('systemctl restart batt_rover-start')

# Connect to rover comm service
HOST = '10.10.10.100'
gimbal_PORT = 33000
motors_PORT = 33001
record_PORT = 33003
gimbal_ADDR = (HOST, gimbal_PORT)
motors_ADDR = (HOST, motors_PORT)
record_ADDR = (HOST, record_PORT)

gimbal_socket = socket(AF_INET, SOCK_STREAM)
try:
  gimbal_socket.connect(gimbal_ADDR)
except Exception as err:
  logger.error('Remote Control Gimbal Channel Failed Socket init with Communications Server err: ' + str(err) + ' - rebooting.)
  temp = subprocess.Popen(args=['reboot'], stdout=subprocess.PIPE, shell=True)

motors_socket = socket(AF_INET, SOCK_STREAM)
try:
  motors_socket.connect(motors_ADDR)
except Exception as err:
  logger.error('Remote Control Wheels/Motors Channel Failed Socket init with Communications Server err: ' + str(err) + ' - rebooting.)
  temp = subprocess.Popen(args=['reboot'], stdout=subprocess.PIPE, shell=True)

record_socket = socket(AF_INET, SOCK_STREAM)
try:
  record_socket.connect(record_ADDR)
except Exception as err:
  logger.error('Remote Control Record Channel Failed Socket init with Communications Server err: ' + str(err) + ' - rebooting.)
  temp = subprocess.Popen(args=['reboot'], stdout=subprocess.PIPE, shell=True)

msg = gimbal_socket.recv(1024).decode('utf8')
if msg == 'Connected':
  gimbal_socket.send(bytes('remote', 'utf8'))
msg = gimbal_socket.recv(1024).decode('utf8')
if msg == 'Active':
  logger.info('Remote Control Gimbal Channel Connected and Active with Communications Server @ ' + str(datetime.now())[0:19])

msg = motors_socket.recv(1024).decode('utf8')
if msg == 'Connected':
  motors_socket.send(bytes('remote', 'utf8'))
msg = motors_socket.recv(1024).decode('utf8')
if msg == 'Active':
  logger.info('Remote Control Motors Channel Connected and Active with Communications Server @ ' + str(datetime.now())[0:19])

msg = record_socket.recv(1024).decode('utf8')
if msg == 'Connected':
  record_socket.send(bytes('remote', 'utf8'))
msg = record_socket.recv(1024).decode('utf8')
if msg == 'Active':
  logger.info('Remote Control Record Channel Connected and Active with Communications Server @ ' + str(datetime.now())[0:19])

# Make sure rover_comm.txt exists or create it if not.
try:
	infile = open('/home/remote_logs/rover_comm.txt','r')
	rover_cmd = str(infile.readline())
	infile.close()
except:
	pass
	outfile = open('/home/remote_logs/rover_comm.txt','w')
	rover_cmd = 'RGBW'
	outfile.write(rover_cmd)
	outfile.close

# Now ping to confirm rover is there and responding, setup rover_cm first for the Rover icon display
# NOTE: Battery is handled by the rover_battery_log.py script since it has a different function, to
#       just query the rover battery capacity, not command motors and recordings.
gimbal_socket.send(bytes('ping', 'utf8'))
gimbal_socket.settimeout(1)
try:
  msg = gimbal_socket.recv(1024).decode('utf8')
  if msg == 'remote: ping':   # if echo back bcast ping...try again
    msg = gimbal_socket.recv(1024).decode('utf8')
  if 'ACK' in msg: 
    logger.debug('Remote Control init: Gimbal ping:ACK with Rover @ ' + str(datetime.now())[0:19])
    rover_cmd = rover_cmd[0:1] + 'G' + rover_cmd[2:4]
    gbl_lost_ping_cnt = 0
  else: 
    logger.error('Remote Control init: Gimbal NO ping:ACK with Rover, instead: ' + msg)
    rover_cmd = rover_cmd[0:1] + '0' + rover_cmd[2:4]
    gbl_lost_ping_cnt = 1
except:
  logger.error('Remote Control init: Gimbal Timeout no ping response')
  rover_cmd = rover_cmd[0:1] + '0' + rover_cmd[2:4]
  gbl_lost_ping_cnt = 1
  pass

motors_socket.send(bytes('ping', 'utf8'))
motors_socket.settimeout(1)
try:
  msg = motors_socket.recv(1024).decode('utf8')
  if msg == 'remote: ping':   # if echo back bcast ping...try again
    msg = motors_socket.recv(1024).decode('utf8')
  if 'ACK' in msg: 
    logger.debug('Remote Control init: Motors ping:ACK with Rover @ ' + str(datetime.now())[0:19])
    rover_cmd = rover_cmd[0:3] + 'W'
    mtr_lost_ping_cnt = 0
  else: 
    logger.debug('Remote Control init: Motors NO ping:ACK with Rover, instead: ' + msg)
    rover_cmd = rover_cmd[0:3] + '0'    # this is to handle boot delay today, might need to change in field tests.
    mtr_lost_ping_cnt = 1
except:
  logger.debug('Remote Control init: Motors no ping response')
  rover_cmd = rover_cmd[0:3] + '0'
  mtr_lost_ping_cnt = 1
  pass
  
record_socket.send(bytes('ping', 'utf8'))
record_socket.settimeout(1)
try:
  msg = record_socket.recv(1024).decode('utf8')
  if msg == 'remote: ping':   # if echo back bcast ping...try again
    msg = record_socket.recv(1024).decode('utf8')
  if 'ACK' in msg: 
    logger.debug('Remote Control init: Record ping:ACK with Rover @ ' + str(datetime.now())[0:19])
    rover_cmd = 'R' + rover_cmd[1:4]
    rec_lost_ping_cnt = 0
  else: 
    logger.debug('Remote Control init: Record NO ping:ACK with Rover, instead: ' + msg)
    rover_cmd = '0' + rover_cmd[1:4]
    rec_lost_ping_cnt = 1
except:
  logger.debug('Remote Control init: Record no ping response')
  rover_cmd = '0' + rover_cmd[1:4]
  rec_lost_ping_cnt = 1
  pass
outfile = open('/home/remote_logs/rover_comm.txt','w')
outfile.write(rover_cmd)
outfile.close()

# Confirm data files are in remote_logs folder or create ones with '666'

dir='/home/remote_logs/batt_cap-rover.txt'
if not os.path.exists(dir):
    text_file = open(dir,"w")
    text_file.write('666\n')
    text_file.close()

dir='/home/remote_logs/batt_cap.txt'
if not os.path.exists(dir):
	temp = subprocess.Popen(args=['sudo i2cget -y 1 0x62 0x4 bw'], stdout=subprocess.PIPE, shell=True)
	battery_val, err = temp.communicate()
	battery_capacity = str(battery_val)
	text_file = open(dir,"w")
	text_file.write(battery_capacity)
	text_file.close()

dir='/home/remote_logs/temp.txt'
if not os.path.exists(dir):
    tempFile = open( "/sys/class/thermal/thermal_zone0/temp" )
    cpu_temp = int(tempFile.read())
    tempFile.close()
    temp_C = float(cpu_temp)/1000.0
    temp_F = temp_C * 1.8 + 32
    temp_F = str(round(temp_F,1))
    text_file = open(dir,"w")
    text_file.write(temp_F)
    text_file.close()

config = configparser.ConfigParser()
config.read('/root/.kivy/config.ini')
control_side = config.get('input', 'control_side')
kivy_file = 'RemoteControl-' + control_side + '.kv'

prior_strength = 0  # wlan0 to initialize
previous_rover_batt = '0'
previous_rc_batt = '0'
previous_temp = '0'
# --------------------
class Remote_Control(App):	# the main application
# --------------------
	global motor_busy, gimbal_busy
	
	motor_busy = False
	gimbal_busy = False
	main_widget = Builder.load_file(kivy_file)

# ----------------------------------------------
	def build(self):
# ----------------------------------------------
		Clock.schedule_once(Remote_Control.read_files, 1)
		return self.main_widget

	def app_shutdown(self):
		logger.debug('Remote Control App Shutdown Commencing - User Interface button.')
		shutdown()
		sys.exit()

	def app_restart(self):
		logger.debug('Remote Control App Restart Commencing - User Interface button.')
		shutdown()
		sys.exit(1)
	
	def app_reboot(self):
		logger.debug('Remote Control App Shutdown Commencing - User Interface button.')
		shutdown()
		os.system('sudo reboot')

	def remote_shutdown(self):
		logger.debug('Remote Control CPU Shutdown Commencing - User Interface button.')
		shutdown()
		os.system('sudo shutdown -h now')
# ----------------------------------------------
	def restart_rec_socket(self):
# ----------------------------------------------
		global record_socket
		
		socket_success = False
		record_socket.settimeout(.5)
		try:
			record_socket.send(bytes('{quit}', 'utf8'))
			record_socket.close()
			logger.debug('Remote Control: Record {quit} and closed.')
		except Exception as err:
			logger.error('Exception Remote Control: Record {quit} and close failed. err: ' + str(err) + ' and rebooting.')
			temp = subprocess.Popen(args=['reboot'], stdout=subprocess.PIPE, shell=True)
			pass
		record_socket = socket(AF_INET, SOCK_STREAM)
		try:
			record_socket.connect(record_ADDR)
			tmp_record_msg = record_socket.recv(128).decode('utf8')
		except Exception as err:
			logger.error('Exception Remote Control: Record receive Connected failed. err: ' + str(err))
			pass
			return False              # Give up if the channel fails to respond

		if tmp_record_msg == 'Connected':
			record_socket.send(bytes('remote', 'utf8'))
			tmp_record_msg = record_socket.recv(128).decode('utf8')
		if tmp_record_msg == 'Active':
			logger.debug('Remote Control Record Capture Reconnected and Active with Communications Server @ ' + str(datetime.now())[0:19])
		else:
			logger.error('Remote Control Record NOT Active with Communications Server @ ' + str(datetime.now())[0:19])
		record_socket.send(bytes('ping', 'utf8'))
		tmp_record_msg = ''
		try:
			tmp_record_msg = record_socket.recv(128).decode('utf8')
		except Exception as err:
			logger.error('Exception Remote Control: Record {quit} and close failed. err: ' + str(err))
			pass
		if tmp_record_msg == 'remote: ping':   # echo back from bcast, try again
			logger.debug('Remote Control Restart: Record ping in receive buffer. Receiving again.' + str(datetime.now())[0:19])
			try:
				tmp_record_msg = record_socket.recv(128).decode('utf8')
			except Exception as err:
				logger.error('Exception Remote Control: Record receive failed. err: ' + str(err))
				pass
		if 'ACK' in msg: 
			logger.debug('Remote Control Restart: Record Capture ping:ACK with Rover @ ' + str(datetime.now())[0:19])
			socket_success = True
		else:
			logger.debug('Remote Control Restart: Record Capture NO ping:ACK with Rover')
		return socket_success
			
# ----------------------------------------------
	def ping_record(self):
# ----------------------------------------------
	# ping to confirm Rover Video Capture is there and responding
		global record_socket, rec_lost_ping_cnt
    
		tmp_record_msg = ''
		record_socket.settimeout(.5)
		try:
			record_socket.send(bytes('ping', 'utf8'))
			time.sleep(.1)
			tmp_record_msg = record_socket.recv(128).decode('utf8')
			if tmp_record_msg == 'remote: ping':   # echo back from bcast, try again
#				logger.debug('Remote Control: Record bcast ping back')
				tmp_gimbal_msg = ''
				tmp_record_msg = record_socket.recv(128).decode('utf8')
			if 'ACK' in tmp_record_msg: 
				logger.debug('Remote Control: Record ping:ACK with Rover. ' + str(datetime.now())[0:19])
				infile = open('/home/remote_logs/rover_comm.txt','r')
				rover_cmd = str(infile.readline())
				infile.close()
				rover_cmd = 'R' + rover_cmd[1:4]
				outfile = open('/home/remote_logs/rover_comm.txt','w')
				outfile.write(rover_cmd)
				outfile.close()
				rec_lost_ping_cnt = 0
			elif tmp_record_msg != '': 
				logger.debug('Remote Control: Record NO ping:ACK with Rover, instead: ' + tmp_record_msg)
				rec_lost_ping_cnt += 1
				if rec_lost_ping_cnt > 4:
					logger.warning('Remote Control: Record invalid ping response - restarting socket')
					infile = open('/home/remote_logs/rover_comm.txt','r')
					rover_cmd = str(infile.readline())
					infile.close()
					if Remote_Control.restart_rec_socket(self): 
						rover_cmd = 'R' + rover_cmd[1:4]
						rec_lost_ping_cnt = 0
					else:
						rover_cmd = '0' + rover_cmd[1:4]
					outfile = open('/home/remote_logs/rover_comm.txt','w')
					outfile.write(rover_cmd)
					outfile.close()
          
		except Exception as err:
			logger.debug('Exception Rover Record ping/ACK err: ' + str(err))  
			rec_lost_ping_cnt += 1
			if rec_lost_ping_cnt > 4:
				logger.warning('Remote Control: Record NO ping response - restarting socket')
				infile = open('/home/remote_logs/rover_comm.txt','r')
				rover_cmd = str(infile.readline())
				infile.close()
				if Remote_Control.restart_rec_socket(self): 
				  logger.debug('Remote Control: Record restarted socket.')
				  rover_cmd = 'R' + rover_cmd[1:4]
				  rec_lost_ping_cnt = 0
				else:
				  logger.debug('Remote Control: Record failed to restart socket.')
				  rover_cmd = '0' + rover_cmd[1:4]
				outfile = open('/home/remote_logs/rover_comm.txt','w')
				outfile.write(rover_cmd)
				outfile.close()
			pass

# ----------------------------------------------
	def restart_gbl_socket(self):
# ----------------------------------------------
		global gimbal_socket
		
		socket_success = False
		gimbal_socket.settimeout(.5)
		try:
			gimbal_socket.send(bytes('{quit}', 'utf8'))
			gimbal_socket.close()
			logger.debug('Remote Control: Gimbal {quit} and closed.')
		except Exception as err:
			logger.error('Exception Remote Control: Gimbal {quit} and close failed. err: ' + str(err) + ' and rebooting')
			temp = subprocess.Popen(args=['reboot'], stdout=subprocess.PIPE, shell=True)
			pass
		gimbal_socket = socket(AF_INET, SOCK_STREAM)
		try:
			gimbal_socket.connect(gimbal_ADDR)
			tmp_gimbal_msg = gimbal_socket.recv(128).decode('utf8')
		except Exception as err:
			logger.error('Exception Remote Control: Gimbal receive Connected failed. err: ' + str(err))
			pass
			return False              # Give up if the channel fails to respond

		if tmp_gimbal_msg == 'Connected':
			gimbal_socket.send(bytes('remote', 'utf8'))
			tmp_gimbal_msg = gimbal_socket.recv(128).decode('utf8')
		if tmp_gimbal_msg == 'Active':
			logger.debug('Remote Control Gimbal Reconnected and Active with Communications Server @ ' + str(datetime.now())[0:19])
		else:
			logger.error('Remote Control Gimbal NOT Active with Communications Server @ ' + str(datetime.now())[0:19])
		gimbal_socket.send(bytes('ping', 'utf8'))
		tmp_gimbal_msg = ''
		try:
			tmp_gimbal_msg = gimbal_socket.recv(128).decode('utf8')
		except Exception as err:
			logger.error('Exception Remote Control: Gimbal {quit} and close failed. err: ' + str(err))
			pass
		if tmp_gimbal_msg == 'remote: ping':   # echo back from bcast, try again
			logger.debug('Remote Control Restart: Gimbal ping in receive buffer. Receiving again.' + str(datetime.now())[0:19])
			try:
				tmp_gimbal_msg = gimbal_socket.recv(128).decode('utf8')
			except Exception as err:
				logger.error('Exception Remote Control: Gimbal receive failed. err: ' + str(err))
				pass
		if 'ACK' in tmp_gimbal_msg: 
			logger.debug('Remote Control Restart: Gimbal ping:ACK with Rover @ ' + str(datetime.now())[0:19])
			socket_success = True
		else:
			logger.error('Remote Control Restart: Gimbal NO ping:ACK with Rover')
		return socket_success

# ----------------------------------------------
	def ping_gimbal(self):
# ----------------------------------------------
	# ping to confirm Rover Gimbal is there and responding
		global gimbal_socket, gbl_lost_ping_cnt, gimbal_busy
    
		if gimbal_busy: 
			logger.debug('ping_gimbal:gimbal_busy')	
			return
		gimbal_busy = True
		tmp_gimbal_msg = ''
		gimbal_socket.settimeout(.5)
		try:
			gimbal_socket.send(bytes('ping', 'utf8'))
			time.sleep(.1)
			tmp_gimbal_msg = gimbal_socket.recv(128).decode('utf8')
			if tmp_gimbal_msg == 'remote: ping':   # echo back from bcast, try again 
#				logger.debug('Remote Control: Gimbal bcast ping back')
				tmp_gimbal_msg = ''
				tmp_gimbal_msg = gimbal_socket.recv(128).decode('utf8')
			if 'ACK' in tmp_gimbal_msg: 
				logger.debug('Remote Control: Gimbal ping:ACK with Rover. ' + str(datetime.now())[0:19])
				infile = open('/home/remote_logs/rover_comm.txt','r')
				rover_cmd = str(infile.readline())
				infile.close()
				rover_cmd = rover_cmd[0:1] + 'G' + rover_cmd[2:4]
				outfile = open('/home/remote_logs/rover_comm.txt','w')
				outfile.write(rover_cmd)
				outfile.close()
				gbl_lost_ping_cnt = 0
			elif tmp_gimbal_msg != '': 
				  logger.debug('Remote Control: Gimbal NO ping:ACK with Rover, instead: ' + tmp_gimbal_msg)
				  gbl_lost_ping_cnt += 1
				  if gbl_lost_ping_cnt > 4:
				    logger.warning('Remote Control: Gimbal invalid ping response - restarting socket.' + str(datetime.now())[0:19])
				    infile = open('/home/remote_logs/rover_comm.txt','r')
				    rover_cmd = str(infile.readline())
				    infile.close()
				    if Remote_Control.restart_gbl_socket(self): 
				      rover_cmd = rover_cmd[0:1] + 'G' + rover_cmd[2:4]
				      gbl_lost_ping_cnt = 0
				    else:
				      rover_cmd = rover_cmd[0:1] + '0' + rover_cmd[2:4]
				    outfile = open('/home/remote_logs/rover_comm.txt','w')
				    outfile.write(rover_cmd)
				    outfile.close()
				
		except Exception as err:
			logger.debug('Exception Rover Gimbal ping/ACK err: ' + str(err))  
			gbl_lost_ping_cnt += 1
			if gbl_lost_ping_cnt > 4:   # If no response from server after 4 pings, restart socket services
				logger.warning('Remote Control: Gimbal NO ping response - restarting socket')
				infile = open('/home/remote_logs/rover_comm.txt','r')
				rover_cmd = str(infile.readline())
				infile.close()
				if Remote_Control.restart_gbl_socket(self): 
				  logger.debug('Remote Control: Gimbal restarted socket.')
				  rover_cmd = rover_cmd[0:1] + 'G' + rover_cmd[2:4]
				  gbl_lost_ping_cnt = 0
				else:
				  logger.debug('Remote Control: Gimbal failed to restart socket.')
				  rover_cmd = rover_cmd[0:1] + '0' + rover_cmd[2:4]
				outfile = open('/home/remote_logs/rover_comm.txt','w')
				outfile.write(rover_cmd)
				outfile.close()
			pass
		gimbal_busy = False

# ----------------------------------------------
	def restart_mtr_socket(self):
# ----------------------------------------------
		global motors_socket
		
		socket_success = False
		motors_socket.settimeout(.5)
		try:
			motors_socket.send(bytes('{quit}', 'utf8'))
			motors_socket.close()
			logger.debug('Remote Control: Motors {quit} and closed.')
		except Exception as err:
			logger.error('Exception Remote Control: Motors {quit} and close failed. err: ' + str(err)) + ' and rebooting.')
			temp = subprocess.Popen(args=['reboot'], stdout=subprocess.PIPE, shell=True)
			pass
		motors_socket = socket(AF_INET, SOCK_STREAM)
		try:
			motors_socket.connect(motors_ADDR)
			tmp_motors_msg = motors_socket.recv(128).decode('utf8')
		except Exception as err:
			logger.error('Exception Remote Control: Gimbal receive Connected failed. err: ' + str(err))
			pass
			return False              # Give up if the channel fails to respond

		if tmp_motors_msg == 'Connected':
			motors_socket.send(bytes('remote', 'utf8'))
			tmp_motors_msg = motors_socket.recv(128).decode('utf8')
		if tmp_motors_msg == 'Active':
			logger.debug('Remote Control Motors Reconnected and Active with Communications Server @ ' + str(datetime.now())[0:19])
		else:
			logger.error('Remote Control Motors NOT Active with Communications Server @ ' + str(datetime.now())[0:19])
		motors_socket.send(bytes('ping', 'utf8'))
		tmp_motors_msg = ''
		try:
			tmp_motors_msg = motors_socket.recv(128).decode('utf8')
		except Exception as err:
			logger.error('Exception Remote Control: Motors {quit} and close failed. err: ' + str(err))
			pass
		if tmp_motors_msg == 'remote: ping':   # echo back from bcast, try again
			logger.debug('Remote Control Restart: Motors ping in receive buffer. Receiving again.' + str(datetime.now())[0:19])
			try:
				tmp_motors_msg = motors_socket.recv(128).decode('utf8')
			except Exception as err:
				logger.error('Exception Remote Control: Motors receive failed. err: ' + str(err))
				pass
		if 'ACK' in tmp_motors_msg: 
			logger.debug('Remote Control Restart: Motors ping:ACK with Rover @ ' + str(datetime.now())[0:19])
			socket_success = True
		else:
			logger.debug('Remote Control Restart: Motors NO ping:ACK with Rover')
		return socket_success

# ----------------------------------------------
	def ping_motors(self):
# ----------------------------------------------
  # ping to confirm Rover Motors/Wheels are there and responding
		global motors_socket, mtr_lost_ping_cnt, motor_busy
    
		if motor_busy: 
			logger.debug('ping_motors:motor_busy')	
			return
		motor_busy = True
		tmp_motors_msg = ''
		motors_socket.settimeout(.5)
		try:
			motors_socket.send(bytes('ping', 'utf8'))
			time.sleep(.1)
			tmp_motors_msg = motors_socket.recv(128).decode('utf8')
			if tmp_motors_msg == 'remote: ping':   # echo back from bcast, try again 
#				logger.debug('Remote Control: Motors bcast ping back')
				tmp_motors_msg = ''
				tmp_motors_msg = motors_socket.recv(128).decode('utf8')
			if 'ACK' in tmp_motors_msg: 
				logger.debug('Remote Control: Motors ping:ACK with Rover. ' + str(datetime.now())[0:19])
				infile = open('/home/remote_logs/rover_comm.txt','r')
				rover_cmd = str(infile.readline())
				infile.close()
				rover_cmd = rover_cmd[0:3] + 'W'
				outfile = open('/home/remote_logs/rover_comm.txt','w')
				outfile.write(rover_cmd)
				outfile.close()
				mtr_lost_ping_cnt = 0
			elif tmp_motors_msg != '': 
				logger.debug('Remote Control: Motors NO ping:ACK with Rover, instead: ' + tmp_motors_msg)
				mtr_lost_ping_cnt += 1
				if mtr_lost_ping_cnt > 4:
					logger.warning('Remote Control: Motors invalid ping response - restarting socket.')
					infile = open('/home/remote_logs/rover_comm.txt','r')
					rover_cmd = str(infile.readline())
					infile.close()
					if Remote_Control.restart_mtr_socket(self): 
						rover_cmd = rover_cmd[0:3] + 'W'
						mtr_lost_ping_cnt = 0
					else:
						rover_cmd = rover_cmd[0:3] + '0'
					outfile = open('/home/remote_logs/rover_comm.txt','w')
					outfile.write(rover_cmd)
					outfile.close()

		except Exception as err:
			logger.debug('Exception Rover Motors ping/ACK err: ' + str(err))  
			mtr_lost_ping_cnt += 1
			if mtr_lost_ping_cnt > 4:   # If no response from server after 4 pings, restart socket services
				logger.warning('Remote Control: Motors NO ping response - restarting socket')
				infile = open('/home/remote_logs/rover_comm.txt','r')
				rover_cmd = str(infile.readline())
				infile.close()
				if Remote_Control.restart_mtr_socket(self): 
				  logger.debug('Remote Control: Motors restarted socket.')
				  rover_cmd = rover_cmd[0:3] + 'W'
				  mtr_lost_ping_cnt = 0
				else:
				  logger.debug('Remote Control: Motors failed to restart socket.')
				  rover_cmd = rover_cmd[0:3] + '0'
				outfile = open('/home/remote_logs/rover_comm.txt','w')
				outfile.write(rover_cmd)
				outfile.close()
			pass
		motor_busy = False

# ----------------------------------------------
	def update_wifi(self):
# ----------------------------------------------
		global prior_strength
    
		gc.collect()
		temp = subprocess.Popen(args=['iwconfig wlan0 | grep -i quality'], stdout=subprocess.PIPE, shell=True)
		wlan0_val, err = temp.communicate()
		wlan0_strength = str(wlan0_val)
		cmp=wlan0_strength[25:33]
		i=1
		while cmp[i]!='/':
			i += 1
		cmp_num = cmp[:i]
		i += 1
		j = i
		while cmp[i]!=' ':
			i += 1
		cmp_den = cmp[j:i]
		try:
			num = int(cmp_num)
			den = int(cmp_den)
		except:
			num, den = 0
    
		if num > 10 and den > 10:
			try:
				wlan0_strength = num/den
			except:
				Remote_Control.main_widget.ids['wifi_icon'].background_normal = '/home/app/icons/Wi-FiIcon-off.PNG'
				logger.debug('ERROR: set wifi indicator off')
				prior_strength = 0
			if wlan0_strength != prior_strength:
				if wlan0_strength < .2:
					Remote_Control.main_widget.ids['wifi_icon'].background_normal = '/home/app/icons/Wi-FiIcon-low.PNG'
					logger.debug(str(num) + '/' + str(den) + ' set wifi indicator low')
				elif wlan0_strength < .5:
					Remote_Control.main_widget.ids['wifi_icon'].background_normal = '/home/app/icons/Wi-FiIcon-half.PNG'
					logger.debug(str(num) + '/' + str(den) + ' set wifi indicator half')
				else:
					Remote_Control.main_widget.ids['wifi_icon'].background_normal = '/home/app/icons/Wi-FiIcon-full.PNG'
#					logger.debug(str(num) + '/' + str(den) + ' set wifi indicator high')
				prior_strength = wlan0_strength
		else:
			Remote_Control.main_widget.ids['wifi_icon'].background_normal = '/home/app/icons/Wi-FiIcon-off.PNG'
			logger.info(str(num) + '/' + str(den) + ' set wifi indicator off')
			prior_strength = 0
		return

#######################################################
# CAMERA
#######################################################
	def camera_180_pan(self):
# ----------------------------------------------
		#client_socket.send(bytes('', 'utf8'))
		# Wait for WAK/ACK
		logger.info('camera_180_pan needs to be implemented')
		return

# ----------------------------------------------
	def camera_90_pan_left(self):
# ----------------------------------------------
		global gimbal_busy
		if gimbal_busy:
			logger.info('camera_90_pan_left BUSY')	
			return
		gimbal_busy = True
		gimbal_socket.send(bytes('76', 'utf8'))
		logger.debug('camera_90_pan_left sent gimbal_msg')
		# Wait for WAK/ACK
		gimbal_socket.settimeout(1)
		try:
			gimbal_msg = gimbal_socket.recv(1024).decode('utf8')
		except: 
			logger.debug('camera_90_pan_left - No WAK received')
			pass
		if 'WAK' in gimbal_msg:
			logger.debug('camera_90_pan_left - WAK received')
		else: logger.debug('camera_90_pan_left - No WAK received')
		gimbal_socket.settimeout(7)
		try:
			gimbal_msg = gimbal_socket.recv(1024).decode('utf8')
		except: 
			logger.debug('camera_90_pan_left - No ACK received')
			pass
		if 'ACK' in gimbal_msg:
			logger.debug('camera_90_pan_left - ACK completed')
		gimbal_busy = False
		return

# ----------------------------------------------
	def camera_90_pan_right(self):
# ----------------------------------------------
		global gimbal_busy
		if gimbal_busy: 
			logger.debug('camera_90_pan_right BUSY')	
			return
		gimbal_busy = True
		gimbal_socket.send(bytes('82', 'utf8'))
		logger.debug('camera_90_pan_right sent gimbal_msg')
		# Wait for WAK/ACK
		gimbal_msg = gimbal_socket.recv(1024).decode('utf8')
		if 'WAK' in gimbal_msg:
			logger.debug('camera_90_pan_right - WAK received')
		gimbal_msg = gimbal_socket.recv(1024).decode('utf8')
		if 'ACK' in gimbal_msg:
			logger.debug('camera_90_pan_right - ACK completed')
		gimbal_busy = False
		return

# ----------------------------------------------
	def camera_tilt_up(self):
# ----------------------------------------------
		global gimbal_busy
		if gimbal_busy: 
			logger.debug('camera_tilt_up BUSY')	
			return
		gimbal_busy = True
		gimbal_socket.send(bytes('337', 'utf8'))
		logger.debug('camera_tilt_up sent gimbal_msg')
		gimbal_msg = ''
		try:
      gimbal_msg = gimbal_socket.recv(1024).decode('utf8')
		except:
      pass
		if 'WAK' in gimbal_msg:
			logger.debug('camera_tilt_up - WAK received')
		try:
      gimbal_msg = gimbal_socket.recv(1024).decode('utf8')
		except:
      pass
		if 'ACK' in gimbal_msg:
			logger.debug('camera_tilt_up - ACK completed')
		gimbal_busy = False
		return
		
# ----------------------------------------------
	def camera_tilt_down(self):
# ----------------------------------------------
		global gimbal_busy
		if gimbal_busy:
			logger.debug('camera_tilt_down BUSY')	
			return
		gimbal_busy = True
		gimbal_socket.send(bytes('336', 'utf8'))
		logger.debug('camera_tilt_down sent gimbal_msg')
		# Wait for WAK/ACK
		gimbal_msg = ''
		try:
      gimbal_msg = gimbal_socket.recv(1024).decode('utf8')
		except:
      pass
		if 'WAK' in gimbal_msg:
			logger.debug('camera_tilt_down - WAK received')
		try:
      gimbal_msg = gimbal_socket.recv(1024).decode('utf8')
		except:
      pass
		if 'ACK' in gimbal_msg:
			logger.debug('camera_tilt_down - ACK completed')
		gimbal_busy = False
		return

# ----------------------------------------------
	def camera_pan_left(self):
# ----------------------------------------------
		global gimbal_busy
		if gimbal_busy:
			logger.debug('camera_pan_left BUSY')	
			return
		gimbal_busy = True
		gimbal_socket.send(bytes('393', 'utf8'))
		logger.debug('camera_pan_left sent gimbal_msg')
		# Wait for WAK/ACK
		gimbal_msg = ''
		try:
      gimbal_msg = gimbal_socket.recv(1024).decode('utf8')
		except:
      pass
		if 'WAK' in gimbal_msg:
			logger.debug('camera_pan_left - WAK received')
		try:
      gimbal_msg = gimbal_socket.recv(1024).decode('utf8')
		except:
      pass
		if 'ACK' in gimbal_msg:
			logger.debug('camera_pan_left - ACK completed')
		gimbal_busy = False
		return

# ----------------------------------------------
	def camera_pan_right(self):
# ----------------------------------------------
		global gimbal_busy
		if gimbal_busy:
			logger.debug('camera_pan_right BUSY')
			return
		gimbal_busy = True
		gimbal_socket.send(bytes('402', 'utf8'))
		logger.debug('camera_pan_right sent gimbal_msg')
		# Wait for WAK/ACK
		gimbal_msg = ''
		try:
      gimbal_msg = gimbal_socket.recv(1024).decode('utf8')
		except:
      pass
		if 'WAK' in gimbal_msg:
			logger.debug('camera_pan_right - WAK received')
		try:
      gimbal_msg = gimbal_socket.recv(1024).decode('utf8')
		except:
      pass
		if 'ACK' in gimbal_msg:
			logger.debug('camera_pan_right - ACK completed')
		gimbal_busy = False
		return

# ----------------------------------------------
	def camera_home(self):
# ----------------------------------------------
		global gimbal_busy
		if gimbal_busy:
			logger.debug('camera_home BUSY')	
			return
		gimbal_busy = True
		gimbal_socket.send(bytes('72', 'utf8'))
		logger.debug('camera_home sent gimbal_msg')
		# Wait for WAK/ACK
		gimbal_msg = ''
		try:
      gimbal_msg = gimbal_socket.recv(1024).decode('utf8')
		except:
      pass
		if 'WAK' in gimbal_msg:
			logger.debug('camera_home - WAK received')
		try:
      gimbal_msg = gimbal_socket.recv(1024).decode('utf8')
		except:
      pass
		if 'ACK' in gimbal_msg:
			logger.debug('camera_home - ACK completed')
		gimbal_busy = False
		return

# ----------------------------------------------
	def calibrate_camera(self):
# ----------------------------------------------
		global gimbal_busy
		if gimbal_busy: 
			logger.debug('calibrate_camera BUSY')	
			return
		gimbal_busy = True
		gimbal_socket.send(bytes('67', 'utf8'))
		logger.debug('calibrate_camera sent gimbal_msg')
		# Wait for ACK
		gimbal_msg = ''
		try:
      gimbal_msg = gimbal_socket.recv(1024).decode('utf8')
		except:
      pass
		if 'ACK' in gimbal_msg:
			logger.debug('calibrate_camera - ACK completed')
		gimbal_busy = False
		return

#######################################################
# WHEELS
#######################################################
	def wheel_180_turn(self):
# ----------------------------------------------
		global motor_busy
		if motor_busy: return
		motor_busy = True
		motors_socket.send(bytes('50', 'utf8'))
		logger.debug('wheel_180_turn sent motors_msg')
		# Wait for WAK/ACK
		motors_msg = ''
		try:
			motors_msg = motors_socket.recv(1024).decode('utf8')
		except: pass
		if 'WAK' in motors_msg:
			logger.debug('wheel_180_turn - WAK received')
		try:
			motors_msg = motors_socket.recv(1024).decode('utf8')
		except: pass
		if 'ACK' in motors_msg:
			logger.debug('wheel_180_turn - ACK completed')
		motor_busy = False
		return 

# ----------------------------------------------
	def wheel_90_turn_left(self):
# ----------------------------------------------
		global motor_busy
		if motor_busy: return
		motor_busy = True
		motors_socket.send(bytes('52', 'utf8'))
		logger.debug('wheel_90_turn_left sent motors_msg')
		# Wait for WAK/ACK
		motors_msg = ''
		try:
			motors_msg = motors_socket.recv(1024).decode('utf8')
		except: pass
		if 'WAK' in motors_msg:
			logger.debug('wheel_90_turn_left - WAK received')
		try:
			motors_msg = motors_socket.recv(1024).decode('utf8')
		except: pass
		if 'ACK' in motors_msg:
			logger.debug('wheel_90_turn_left - ACK completed')
		motor_busy = False
		return

# ----------------------------------------------
	def wheel_90_turn_right(self):
# ----------------------------------------------
		global motor_busy
		if motor_busy: return
		motor_busy = True
		motors_socket.send(bytes('54', 'utf8'))
		logger.debug('wheel_90_turn_right sent motors_msg')
		# Wait for WAK/ACK
		motors_msg = ''
		try:
			motors_msg = motors_socket.recv(1024).decode('utf8')
		except: pass
		if 'WAK' in motors_msg:
			logger.debug('wheel_90_turn_right - WAK received')
		try:
			motors_msg = motors_socket.recv(1024).decode('utf8')
		except: pass
		if 'ACK' in motors_msg:
			logger.debug('wheel_90_turn_right - ACK completed')
		motor_busy = False
		return

# ----------------------------------------------
	def wheels_right(self):
# ----------------------------------------------
		global motor_busy
		if motor_busy: return
		motor_busy = True
		motors_socket.send(bytes('261', 'utf8'))
		logger.debug('wheels_right sent motors_msg')
		# Wait for WAK/ACK
		motors_msg = ''
		try:
			motors_msg = motors_socket.recv(1024).decode('utf8')
		except: pass
		if 'WAK' in motors_msg:
			logger.debug('wheels_right - WAK received')
		try:
			motors_msg = motors_socket.recv(1024).decode('utf8')
		except: pass
		if 'ACK' in motors_msg:
			logger.debug('wheels_right - ACK completed')
		motor_busy = False
		return

# ----------------------------------------------
	def wheels_left(self):
# ----------------------------------------------
		global motor_busy
		if motor_busy: return
		motor_busy = True
		motors_socket.send(bytes('260', 'utf8'))
		logger.debug('wheels_turn_left sent motors_msg')
		# Wait for WAK/ACK
		motors_msg = ''
		try:
			motors_msg = motors_socket.recv(1024).decode('utf8')
		except: pass
		if 'WAK' in motors_msg:
			logger.debug('wheels_left - WAK received')
		try:
			motors_msg = motors_socket.recv(1024).decode('utf8')
		except: pass
		if 'ACK' in motors_msg:
			logger.debug('wheels_left - ACK completed')
		motor_busy = False
		return

# ----------------------------------------------
	def wheels_home(self):
# ---------------------------------------------- This is a misnomer to test WAK/ACK for timed 360 turn around.
		global motor_busy
		if motor_busy: return
		motor_busy = True
		motors_socket.send(bytes('50', 'utf8'))
		logger.debug('wheels_home sent motors_msg')
		# Wait for WAK/ACK
		motors_msg = ''
		try:
			motors_msg = motors_socket.recv(1024).decode('utf8')
		except: pass
		if 'WAK' in motors_msg:
			logger.debug('wheels_home - WAK received')
		try:
			motors_msg = motors_socket.recv(1024).decode('utf8')
		except: pass
		if 'ACK' in motors_msg:
			logger.debug('wheels_home - ACK completed')
		motor_busy = False
		return

# ----------------------------------------------
	def wheels_forward(self):	# Note this command does not care about motor_busy
# ----------------------------------------------
		motors_socket.send(bytes('102', 'utf8'))
		logger.debug('wheels_forward sent motors_msg')
		# Wait for ACK
		motors_msg = ''
		try:
			motors_msg = motors_socket.recv(1024).decode('utf8')
		except: pass
		if 'ACK' in motors_msg:
			logger.debug('wheels_forward - ACK completed')
		return

# ----------------------------------------------
	def wheels_reverse(self):	# Note this command does not care about motor_busy
# ----------------------------------------------
		motors_socket.send(bytes('114', 'utf8'))
		logger.info('wheels_reverse sent motors_msg')
		# Wait for ACK
		motors_msg = ''
		try:
			motors_msg = motors_socket.recv(1024).decode('utf8')
		except: pass
		if 'ACK' in motors_msg:
			logger.debug('wheels_reverse - ACK completed')
		return

# ----------------------------------------------
	def slider_speed(self):   # This routine is executed whenever the speed value changes
# ---------------------------------------------- includes speed buttons, slider, and stop button.
		global motor_busy
		
		if motor_busy: 
			logger.debug('slider_speed:motor_busy')	
			return
		motor_busy = True
		speed_int = int(self.main_widget.ids.slider_speed.value)
		speed = 'speed=' + str(speed_int)
		motors_socket.send(bytes(speed, 'utf8'))
		logger.debug('slider_speed sent msg as ' + speed)
		motor_busy = False

#######################################################
# VIDEO BUTTONS
#######################################################
# ----------------------------------------------
	def video_record(self):
# ----------------------------------------------
#		logger.info('Remote_Control.main_widget.ids[video_record].state = ' + str(Remote_Control.main_widget.ids['video_record'].state))
		if Remote_Control.main_widget.ids['video_record'].state == 'down':
			record_socket.send(bytes('rec_start', 'utf8'))
			logger.info('Video Recording Started at ' + datetime.now().strftime('%m-%d-%y_%H-%M-%S'))
			record_socket.settimeout(.5)
			try:
				record_msg = record_socket.recv(1024).decode('utf8')
				if 'ACK' in record_msg: logger.info('Video Recording Started - ACK received')
				else: logger.info('Video Recording Started - No ACK received')
			except:
				logger.info('Video Recording Started - ACK timed out')
			Clock.schedule_once(Remote_Control.video_rec_stop, 60)
		else:
			record_socket.send(bytes('rec_stop', 'utf8'))
			try:
				record_msg = record_socket.recv(1024).decode('utf8')
				if 'ACK' in record_msg: logger.info('Video Recording Started - ACK received')
				else: logger.info('Video Recording Started - No ACK received')
			except:
				logger.info('Video Recording Started - ACK timed out')
			logger.info('Video Recording User Stopped at ' + datetime.now().strftime('%m-%d-%y_%H-%M-%S'))

# ----------------------------------------------
	def video_rec_stop(self):
# ----------------------------------------------
		record_socket.send(bytes('rec_stop', 'utf8'))
		logger.info('Video Recording Timed Stop at ' + datetime.now().strftime('%m-%d-%y_%H-%M-%S'))
		Remote_Control.main_widget.ids['video_record'].state = 'normal'
		record_socket.settimeout(1)
		try:
			record_msg = record_socket.recv(1024).decode('utf8')
			if 'ACK' in record_msg: logger.info('Video Recording Timed Stopped - ACK received')
			else: logger.info('Video Recording Timed Stopped - No ACK received')
		except:
			logger.info('Video Recording Timed Stopped - ACK timed out')

# ----------------------------------------------
	def video_snapshot(self):
# ----------------------------------------------
		record_socket.send(bytes('snapshot', 'utf8'))
		logger.info('Command: snapshot sent to rover')
		# Wait for ACK
		record_socket.settimeout(1)
		try:
			snapshot_msg = record_socket.recv(1024).decode('utf8')
			if 'ACK' in snapshot_msg: logger.info('snapshot - ACK completed')
			else: logger.info('snapshot - No ACK received')
		except:
			logger.info('snapshot - ACK timed out')

# ----------------------------------------------
	def screen_snapshot(self):
# ----------------------------------------------
		background = Image.open('/home/app/black.png')
		foreground = Image.open('/home/app/screen_snapshot.png')
		Image.alpha_composite(background, foreground).save('/home/pictures/ScrSnap' + datetime.now().strftime('%m-%d-%y_%H-%M-%S') + '.png')
		logger.info('Screen Snapshot saved.')

# ----------------------------------------------
	def read_files(self):
# ----------------------------------------------
		global previous_rc_batt, previous_rover_batt, previous_temp
    
		infile = open('/home/remote_logs/batt_cap.txt','r')
		stored_batt = str(infile.readline())
		infile.close()
		if int(stored_batt) == -1: stored_batt = '666'
		if int(stored_batt) < 5:
			logger.critical('Remote Control Battery Capacity is less than 5%, shutting down now. Date/Time= {' + str(datetime.now())[0:19] + '}')
			time.sleep(.5)
			os.system('shutdown -P now')
		infile = open('/home/remote_logs/batt_cap-rover.txt','r')
		rover_batt = str(infile.readline())
		infile.close()
		if previous_rover_batt != str(rover_batt):
			logger.info('Rover Processor: Battery Capacity: ' + rover_batt + '%, Date/Time= {' + str(datetime.now())[0:19] + '}')
			previous_rover_batt = str(rover_batt)

		if int(stored_batt) < 10:
			RC_batt = 'alert'
		elif int(stored_batt) < 20:
			RC_batt = '20'
		elif int(stored_batt) < 50:
			RC_batt = '50'
		elif int(stored_batt) < 80:
			RC_batt = '80'
		else:
			RC_batt = 'full'

		if int(rover_batt) < 10:
			R_batt = 'alert'
		elif int(rover_batt) < 20:
			R_batt = '20'
		elif int(rover_batt) < 50:
			R_batt = '50'
		elif int(rover_batt) < 80:
			R_batt = '80'
		else:
			R_batt = 'full'
		Remote_Control.main_widget.ids['batteries_icon'].background_normal = '/home/app/icons/R'+ R_batt + '_RC' + RC_batt + '.PNG'
		Remote_Control.main_widget.ids['battery_capacity'].text = 'Battery: ' + stored_batt + '%'
		Remote_Control.main_widget.ids['battery_capacity'].color = (1,1,1,1)
		Remote_Control.main_widget.ids['direction'].color = (1,1,1,1)
		Remote_Control.main_widget.ids['speed_display'].color = (1,1,1,1)

		infile = open('/home/remote_logs/temp.txt','r')
		try:
			stored_temp = str(infile.readline())
			infile.close()
			Remote_Control.main_widget.ids['temperature'].text = 'Temp: {}°F'.format(stored_temp)
			Remote_Control.main_widget.ids['temperature'].color = (0,1,1,1)
			new_temp = float(stored_temp)
			old_temp = float(previous_temp)
			if previous_rc_batt != str(stored_batt) or (int(old_temp) - int(new_temp)) > 5 or (int(new_temp) - int(old_temp)) > 5 :
				logger.info('Remote Control: Battery Capacity: ' + stored_batt + '%' + ', Temperature: ' + str(stored_temp) + ', Date/Time= {' + str(datetime.now())[0:19] + '}')
				previous_rc_batt = str(stored_batt)
				previous_temp = str(stored_temp)
		except: 
			logger.error('Remote Control: Battery value error, Date/Time= {' + str(datetime.now())[0:19] + '}')
			infile.close()
			pass
		Remote_Control.ping_gimbal(self)
		Remote_Control.ping_motors(self)
		Remote_Control.ping_record(self)
		infile = open('/home/remote_logs/rover_comm.txt','r')
		rover_cmd = str(infile.readline())
		Remote_Control.main_widget.ids['rover_icon'].background_normal = '/home/app/icons/rover_icons/RoverIcon-' + rover_cmd + '.png'

		Remote_Control.update_wifi(self)
		Clock.schedule_once(Remote_Control.read_files, 5)

# start the main program
if __name__ == '__main__':
	Remote_Control().run()
