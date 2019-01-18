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

def ps3controller():
	global overlay_processes

	# dump ps3 bluetooth controllers informations 
	os.system(ps3dumper)

	# clear old display
	if "ps3" in overlay_processes:
		for p in overlay_processes["ps3"]:
			p.kill()
		overlay_processes["ps3"] = []

	try:
		devices = []
		with open(os.path.dirname(os.path.realpath(__file__))+'/log/hciList.log','r') as f:
			pattern1 = re.compile(r"ACL (.+?:.+?:.+?:.+?:.+?:.+?) handle (\d+?) state")
			for line in f.readlines():
				match = pattern1.findall(line)
				for item in match:
					devices.append({"uid":item[0],"handle":int(item[1])})

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
					for k in devices:
						if k["handle"] == handleid and not k.has_key("battery"):
							print(tmp)
							k["battery"] = tmp.split()[11]
							counter+=1

				# find all devices
				if counter>=len(devices):
					break

				line = f.readline()
					
		print(devices)
		# display battery icons
		for i in range(0,len(devices)):
			if not devices[i].has_key("battery"):
				continue

			x_pos = dpi * 2 * (i/2)
			if i%2:
				x_pos = int(resolution[0]) - dpi * 2 * ((i+2)/2)

			if devices[i]["battery"] == 'EE':
				process = subprocess.Popen(pngview_call + [str(x_pos), os.path.dirname(os.path.realpath(__file__)) + "/icons/bat_charge.png"])
			else:
				
				process = subprocess.Popen(pngview_call + [str(x_pos), os.path.dirname(os.path.realpath(__file__)) + "/icons/bat"+str((int)(devices[i]["battery"])-1)+".png"])

			overlay_processes["ps3"].append(process)

	except OSError:
		pass


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
	ps3controller()
	time.sleep(3)