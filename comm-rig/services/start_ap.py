import subprocess

temp = subprocess.Popen(args=['iw dev wlan0 interface add wlan_ap type __ap'], stdout=subprocess.PIPE, shell=True)
value, err = temp.communicate()
temp = subprocess.Popen(args=['ip link set dev wlan_ap address b8:27:eb:25:46:2f'], stdout=subprocess.PIPE, shell=True)
#temp = subprocess.Popen(args=['ip link set dev wlan_ap address b8:27:eb:0d:09:b6'], stdout=subprocess.PIPE, shell=True)
value, err = temp.communicate()
temp = subprocess.Popen(args=['ip link set wlan_ap up'], stdout=subprocess.PIPE, shell=True)
value, err = temp.communicate()
temp = subprocess.Popen(args=['ip address add 10.10.10.1/24 broadcast + dev wlan_ap'], stdout=subprocess.PIPE, shell=True)
value, err = temp.communicate()

