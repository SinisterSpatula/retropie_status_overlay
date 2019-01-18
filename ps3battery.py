# -*- coding: utf-8 -*-  
import time
import subprocess
import os
import re
import logging
import logging.handlers

fbfile="tvservice -s"

ps3dumper = os.path.dirname(os.path.realpath(__file__)) + "/bluetooth.sh"

pngview_path="/usr/local/bin/pngview"
pngview_call=[pngview_path, "-d", "0", "-b", "0x0000", "-n", "-l", "15000", "-y", "0", "-x"]

logfile = os.path.dirname(os.path.realpath(__file__)) + "/log/ps3battery.log"

dpi=43
overlay_processes = {"ps3":[]}
g_devices = []

def updateDisplay(battery_level_str, handleid):
	global overlay_processes,g_devices

	for i in range(0,len(g_devices)):
		device_current = g_devices[i]
		# only update when value changed
		if device_current['handle'] == handleid and (battery_level_str != device_current['battery'] or i != device_current['last_idx']):
			# save new value
			device_current['battery'] = battery_level_str
			device_current['last_idx'] = i

			x_pos = dpi * 2 * (i/2)
			if i%2:
				x_pos = int(resolution[0]) - dpi * 2 * ((i+2)/2)

			if device_current['battery'] == 'EE':
				process = subprocess.Popen(pngview_call + [str(x_pos), os.path.dirname(os.path.realpath(__file__)) + "/icons/bat_charge.png"])
			else:
				
				process = subprocess.Popen(pngview_call + [str(x_pos), os.path.dirname(os.path.realpath(__file__)) + "/icons/bat"+str((int)(device_current["battery"])-1)+".png"])

			# close old show
			if device_current['process']:
				device_current['process'].kill()
			device_current['process'] = process

			return True
	return False

def getDevice(uid):
	global g_devices
	for tmp in g_devices:
		if tmp['uid'] == uid:
			return tmp

	new_dat = {'uid':uid,'handle':0,'active':True, 'process':None, 'battery':'', 'last_idx':-1}
	g_devices.append(new_dat)
	return new_dat

def ps3controller():
	global overlay_processes,g_devices

	# dump ps3 bluetooth controllers informations 
	os.system(ps3dumper)

	# reset active flag
	for tmp in g_devices:
		tmp['active'] = False

	has_devices = False
	# find current active ps3 controllers
	with open(os.path.dirname(os.path.realpath(__file__))+'/log/hciList.log','r') as f:
		pattern1 = re.compile(r"ACL (.+?:.+?:.+?:.+?:.+?:.+?) handle (\d+?) state")
		for line in f.readlines():
			match = pattern1.findall(line)
			for item in match:
				tmp = getDevice(item[0])
				tmp['handle'] = int(item[1])
				tmp['active'] = True
				has_devices = True

	if has_devices:
		counter = 0
		# find the battery power level
		with open(os.path.dirname(os.path.realpath(__file__))+'/log/hciDump.log','r') as f:
			pattern1 = re.compile(r"ACL data: handle (\d+?) flags")
			line = f.readline()
			while line:
				match = pattern1.findall(line)
				if len(match)>0:
					handleid = int(match[0])
					f.readline()
					f.readline()
					tmp = f.readline()
					#print(tmp)
					# find the level
					tmp_arr = tmp.split()
					if(len(tmp_arr)==20 and updateDisplay(tmp_arr[11], handleid)):
						print(str(handleid) + " " + tmp)
						counter+=1

				# exit loop
				if counter>=len(g_devices):
					break

				line = f.readline()


	# remove unactived devices
	dels = []
	for tmp in g_devices:
		if not tmp['active']:
			dels.append(tmp)
	for tmp in dels:
		if tmp['process']:
			tmp['process'].kill()
		g_devices.remove(tmp)

# Set up logging
my_logger = logging.getLogger('MyLogger')
my_logger.setLevel(logging.INFO)
handler = logging.handlers.RotatingFileHandler(logfile, maxBytes=102400, backupCount=1)
my_logger.addHandler(handler)
console = logging.StreamHandler()
my_logger.addHandler(console)


# Get Framebuffer resolution
resolution=re.search("(\d{3,}x\d{3,})", subprocess.check_output(fbfile.split()).decode().rstrip()).group().split('x')
my_logger.info(resolution)

os.system("pkill pngview")

while True:
	try:
		ps3controller()
	except Exception:
		logger.error("ps3controller error!!!",exc_info = True)
	time.sleep(3)