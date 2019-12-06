import subprocess
import time
import struct
import smbus

stored_capacity=battery_capacity=''

class Guages(object):
    def __init__(self):
        subprocess.Popen(args=['i2cset -y 1 0x62 0x0A 0x00'], stdout=subprocess.PIPE, shell=True)
        temp = subprocess.Popen(args=['sudo i2cget -y 1 0x62 0x4 bw'], stdout=subprocess.PIPE, shell=True)
        battery_val, err = temp.communicate()
        battery_capacity = str(battery_val)
        battery_capacity = battery_capacity[4] + battery_capacity[5]
        battery_capacity = str(int(battery_capacity, 16))
        try:
            infile = open('/home/remote_logs/batt_cap.txt', 'r')
            stored_capacity = str(infile.readline())
            infile.close()
            if stored_capacity == '' or stored_capacity == '666':
                outfile = open('/home/remote_logs/batt_cap.txt', 'w')
                outfile.write(battery_capacity)
                outfile.close()
        except:
            outfile = open('/home/remote_logs/batt_cap.txt', 'w')
            outfile.write(battery_capacity)
            outfile.close()

        tempFile = open( "/sys/class/thermal/thermal_zone0/temp" )
        cpu_temp = int(tempFile.read())
        tempFile.close()
        temp_C = float(cpu_temp)/1000.0
        temp_F = temp_C * 1.8 + 32
        temp_F = str(round(temp_F,1))
        try:
            infile = open('/home/remote_logs/temp.txt', 'r')
            stored_capacity = str(infile.readline())
            infile.close()
            if stored_capacity == '' or stored_capacity == '666':
                outfile = open('/home/remote_logs/temp.txt', 'w')
                outfile.write(temp_F)
                outfile.close()
        except:
            outfile = open('/home/remote_logs/temp.txt', 'w')
            outfile.write(temp_F)
            outfile.close()

        self.poll_guages()

    def poll_guages(self):
        global stored_capacity, battery_capacity
        infile = open('/home/remote_logs/batt_cap.txt', 'r')
        stored_capacity = str(infile.readline())
        infile.close()
        stored_capacity = str(int(float(stored_capacity)))

        temp = subprocess.Popen(args=['sudo i2cget -y 1 0x62 0x4 bw'], stdout=subprocess.PIPE, shell=True)
        battery_val, err = temp.communicate()
        battery_capacity = str(battery_val)
        battery_capacity = battery_capacity[4] + battery_capacity[5]
        battery_capacity = str(int(battery_capacity, 16))

        if battery_capacity == '0': battery_capacity = '-1'     # send -1 to indicate Power HAT read failure.
        if battery_capacity != str(stored_capacity):
            outfile = open('/home/remote_logs/batt_cap.txt', 'w');
            outfile.write(str(int(float(battery_capacity))))
            outfile.close()
#        infile = open('/home/remote_logs/batt_volt.txt', 'r')
#        stored_volts = str(infile.readline())
#        infile.close()

#        temp = subprocess.Popen(args=['sudo i2cget -y 1 0x62 0x02 w'], stdout=subprocess.PIPE, shell=True)
#        battery_val, err = temp.communicate()
#        battery_volts = str(battery_val)
#        battery_volts_low = battery_volts[4] + battery_volts[5]
#        battery_volts_high = battery_volts[6] + battery_volts[7]
#        battery_volts = str(int(battery_volts_high + battery_volts_low, 16))
#        battery_volts = int(battery_volts) * 305
#        battery_volts = battery_volts / 1000000

#        if str(stored_volts) != str(battery_volts):
#            outfile = open('/home/remote_logs/batt_volt.txt', 'w');
#            outfile.write(str(battery_volts))
#            outfile.close()

# Handle temperature same way
        tempFile = open( "/sys/class/thermal/thermal_zone0/temp" )
        cpu_temp = int(tempFile.read())
        tempFile.close()
        temp_C = float(cpu_temp)/1000.0
        temp_F = temp_C * 1.8 + 32
        temp_F = str(round(temp_F,1))
        infile = open('/home/remote_logs/temp.txt','r')
        stored_temp = str(infile.readline())
        infile.close()
        if temp_F != stored_temp: 
            infile = open('/home/remote_logs/temp.txt','w')
            infile.write(temp_F)
            infile.close()
        time.sleep(10)
        self.poll_guages()
Guages()
