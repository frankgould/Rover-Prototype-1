import subprocess, sys
import time, logging
from datetime import datetime

log_file = '/home/rover_logs/wifi_manager-log-' + datetime.now().strftime("%m-%d-%y") + '.txt'
logging.basicConfig(filename=log_file,level=logging.DEBUG)
logging.info('===== Rover Wi-Fi Communications Server Logging Started ' + datetime.now().strftime("%m-%d-%y %H:%M:%S"))

class WiFi_Manager(object):
    def __init__(self):
        self.poll_wifi()

    def poll_wifi(self):
    	temp = subprocess.Popen(args=['ping -c 1 10.10.10.1'], stdout=subprocess.PIPE, shell=True)
    	value, err = temp.communicate()
    	logging.debug('ping response [' + str(value[65:107]) + '] @ ' + datetime.now().strftime("%m-%d-%y %H:%M:%S"))
    	if '1 received' not in str(value):
        	logging.error('No ping response, attempting ping one last time before reboot.')
        	time.sleep(2)
        	temp = subprocess.Popen(args=['ping -c 1 10.10.10.1'], stdout=subprocess.PIPE, shell=True)
        	value, err = temp.communicate()
        	if '1 received' not in str(value):
        		logging.critical('No ping response, rebooting @ ' + datetime.now().strftime("%m-%d-%y %H:%M:%S"))
        		temp = subprocess.Popen(args=['reboot'], stdout=subprocess.PIPE, shell=True)
        		value, err = temp.communicate()
        		sys.exit()

    	temp = subprocess.Popen(args=['systemctl status wpa_supplicant@wlan0 | grep Active:'], stdout=subprocess.PIPE, shell=True)
    	value, err = temp.communicate()
    	if 'active (running)' in str(value):
            logging.debug('wlan0 is operational: ' + str(value) + ' @ ' + datetime.now().strftime("%m-%d-%y %H:%M:%S"))
            temp = subprocess.Popen(args=['systemctl status coffee-start'], stdout=subprocess.PIPE, shell=True)
            value, err = temp.communicate()
            if 'active (running)' not in str(value):
	            logging.error('coffee service is down: ' + str(value) + ', err: ' + str(err))
	            temp = subprocess.Popen(args=['systemctl stop picam-start'], stdout=subprocess.PIPE, shell=True)
	            value, err = temp.communicate()
	            logging.debug('picam stop results: ' + str(value) + ', err: ' + str(err))
	            temp = subprocess.Popen(args=['systemctl restart coffee-start'], stdout=subprocess.PIPE, shell=True)
	            value, err = temp.communicate()
	            logging.debug('coffee restart results: ' + str(value) + ', err: ' + str(err))
	            temp = subprocess.Popen(args=['systemctl restart picam-start'], stdout=subprocess.PIPE, shell=True)
	            value, err = temp.communicate()
	            logging.debug('picam restart results: ' + str(value) + ', err: ' + str(err))
            temp = subprocess.Popen(args=['systemctl status picam-start'], stdout=subprocess.PIPE, shell=True)
            value, err = temp.communicate()
            if 'active (running)' not in str(value) and 'activating (auto-restart)' not in str(value):
	            logging.error('picam service is down (restarting): ' + str(value) + ', err: ' + str(err) + ' @ ' + datetime.now().strftime("%m-%d-%y %H:%M:%S"))
	            temp = subprocess.Popen(args=['systemctl restart picam-start'], stdout=subprocess.PIPE, shell=True)
	            value, err = temp.communicate()
	            logging.info('picam restart results: ' + str(value) + ', err: ' + str(err))
    	else:
            logging.error('wlan0 is down (restarting now): ' + str(value) + ' @ ' + datetime.now().strftime("%m-%d-%y %H:%M:%S"))
            temp = subprocess.Popen(args=['systemctl restart wpa_supplicant@wlan0'], stdout=subprocess.PIPE, shell=True)
            value, err = temp.communicate()
            logging.debug('wlan0 restart results: ' + str(value) + ', err: ' + str(err))
            time.sleep(5)

    	time.sleep(5)
    	self.poll_wifi()
WiFi_Manager()
