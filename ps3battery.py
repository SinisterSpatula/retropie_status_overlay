# -*- coding: utf-8 -*-  
import time
import subprocess
import os
import re
import logging
import logging.handlers
from P3Controllers import *

fbfile="tvservice -s"

ps3dumper = os.path.dirname(os.path.realpath(__file__)) + "/bluetooth.sh"

pngview_path="/usr/local/bin/pngview"
pngview_call=[pngview_path, "-d", "0", "-b", "0x0000", "-n", "-l", "15000", "-y", "0", "-x"]

logfile = os.path.dirname(os.path.realpath(__file__)) + "/log/ps3battery.log"

dpi=43

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
ps3 = P3Controllers(my_logger)
call_proc = []

while True:
	try:
		devices = ps3.GetControllers()
		my_logger.info(devices)
		if len(call_proc) == 0:
			call_proc = [None] * len(devices)

		for i in range(0, len(devices)):
			dev = devices[i]
			if dev == None:continue
			if not dev['changed']:continue

			# close
			if dev['closed']:
				my_logger.info("close###########")
				my_logger.info(dev)
				if call_proc[i]:
					call_proc[i].kill()
					call_proc[i] = None
				ps3.ResetContoller(i)
				continue

			x_pos = dpi * 2 * (i/2)
			if i%2:
				x_pos = int(resolution[0]) - dpi * 2 * ((i+2)/2)

			# update
			if dev['bat'] == 'EE':
				process = subprocess.Popen(pngview_call + [str(x_pos), os.path.dirname(os.path.realpath(__file__)) + "/icons/bat_charge.png"])

				if call_proc[i]:
					call_proc[i].kill()
				call_proc[i] = process
			else:
				
				process = subprocess.Popen(pngview_call + [str(x_pos), os.path.dirname(os.path.realpath(__file__)) + "/icons/bat"+str((int)(dev["bat"])-1)+".png"])

				if call_proc[i]:
					call_proc[i].kill()
				call_proc[i] = process

	except Exception:
		my_logger.error("ps3controller error!!!",exc_info = True)
	time.sleep(3)