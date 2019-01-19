# -*- coding: utf-8 -*-  
import os
import re
import logging
import logging.handlers

class P3Controllers(object):
	def __init__(self, my_logger):
		# max connect 6 ps3 controllers
		self.devices = [None,None,None,None]
		self.ps3dump_cmd = os.path.dirname(os.path.realpath(__file__)) + "/bluetooth.sh"
		self.logger = my_logger

	def ResetContoller(self, idx):
		self.devices[idx] = None

	def GetControllers(self):
		tmp_devices = self._getConnectedDevices()

		self.logger.debug("readed devices: ")
		self.logger.debug(tmp_devices)
		self.logger.debug("old devices: ")
		self.logger.debug(self.devices)

		# check changes
		for i in range(0, len(self.devices)):
			if self.devices[i] == None:
				if tmp_devices[i]:
					self.devices[i] = tmp_devices[i]
					self.devices[i]['changed'] = True
			else:
				if tmp_devices[i]:
					if self._checkChanged(self.devices[i], tmp_devices[i]):
						self.devices[i] = tmp_devices[i]
						self.devices[i]['changed'] = True
					else:
						self.devices[i]['changed'] = False
				else:
					self.devices[i]['changed'] = True
					self.devices[i]['closed'] = True


		return self.devices

	def _checkChanged(self, dat1, dat2):
		if dat1['proc'] != dat2['proc']:
			return True
		if dat1['uid'] != dat2['uid']:
			return True
		if dat1['dev'] != dat2['dev']:
			return True
		if dat1['bat'] != dat2['bat']:
			return True
		if dat1['handler'] != dat2['handler']:
			return True

		return False

	def _getConnectedDevices(self):
		tmp_devices = [None] * len(self.devices)
		# check whether have ps3 controllers
		with os.popen('ps aux | grep sixaxis') as cmd:
			for line in cmd.readlines():
				dat_arr = line.split()
				if len(dat_arr)<12:continue

				if dat_arr[10].endswith('sixaxis'):
					# get ps3 controller device link
					with os.popen('sudo ls -l /proc/'+dat_arr[1]+'/fd/') as cmd2:
						device_link = self._parseDeviceLink(cmd2.readlines())
						if device_link:
							new_dev = self._getNewDevice(dat_arr[1], dat_arr[11], device_link)
							tmp_devices.insert(0, new_dev)

		# get bluetooth handler
		self.logger.debug("find devices: ")
		self.logger.debug(tmp_devices)
		if len(tmp_devices)>0:
			# dump ps3 bluetooth controllers informations 
			os.system(self.ps3dump_cmd)
			handlers = self._getUidsAndHandlers()
			self.logger.debug("find bluetooth handlers: ")
			self.logger.debug(handlers)

			ids = [d['handler'] for d in handlers if 'handler' in d]
			batinfos = self._getBatteryLevel(ids)
			self.logger.debug("find battery informations: ")
			self.logger.debug(batinfos)

			merge_info = self._mergeUidAndBatInfo(handlers, batinfos)
			self.logger.debug("find battery and uid merged informations: ")
			self.logger.debug(merge_info)

			# merge battery and handler information
			for dev in tmp_devices:
				for bat in merge_info:
					if dev and  dev['uid'] == bat['uid']:
						dev['bat'] = bat['bat']
						dev['handler'] = bat['handler']

		# sorted base system device name
		# remove duplicate link
		tmp_devices = sorted(tmp_devices, cmp=self._devicesLongSort)
		remove_str = []
		for dev in tmp_devices:
			if not dev:continue

			for t in remove_str:
				dev['dev'] = dev['dev'].replace(t,'')
			if not ',' in dev['dev']:
				remove_str.append(dev['dev'])
		for dev in tmp_devices:
			if not dev:continue
			dev['dev'] = dev['dev'].replace(',','')

		tmp_devices = sorted(tmp_devices, cmp=self._devicesSort)
		if tmp_devices[0]:
			num_idx = (int)(tmp_devices[0]['dev'].replace('/dev/input/js',''))
			for i in range(0, num_idx):
				tmp_devices.insert(0, None)

		if len(tmp_devices)>len(self.devices):
			tmp_devices = tmp_devices[:len(self.devices)]

		return tmp_devices

	def _devicesLongSort(self, x, y):
		if x == None:
			return 1

		if y == None:
			return -1

		return cmp(len(x['dev']), len(y['dev']))

	def _devicesSort(self, x, y):
		if x == None:
			return 1

		if y == None:
			return -1

		return cmp(x['dev'], y['dev'])


	def _mergeUidAndBatInfo(self, uids, bats):
		ret = []
		for uid in uids:
			for bat in bats:
				if bat['handler'] == uid['handler']:
					tmp = {'uid':'', 'handler':'', 'bat':-1}
					tmp['uid'] = uid['uid']
					tmp['handler'] = uid['handler']
					tmp['bat'] = bat['bat']
					ret.append(tmp)
					break;
		return ret

	def _getUidsAndHandlers(self):
		ret = []
		# find current active ps3 controllers
		with open(os.path.dirname(os.path.realpath(__file__))+'/log/hciList.log','r') as f:
			pattern1 = re.compile(r"ACL (.+?:.+?:.+?:.+?:.+?:.+?) handle (\d+?) state")
			for line in f.readlines():
				match = pattern1.findall(line)
				for item in match:
					if item[1].isdigit():
						ret.append({'uid':item[0], 'handler':item[1]})
		return ret

	def _getBatteryLevel(self, handlers):
		ret = []
		# find the battery power level
		with open(os.path.dirname(os.path.realpath(__file__))+'/log/hciDump.log','r') as f:
			pattern1 = re.compile(r"ACL data: handle (\d+?) flags")
			line = f.readline()
			while line:
				match = pattern1.findall(line)
				if len(match)>0:
					handleid = match[0]
					f.readline()
					f.readline()
					tmp = f.readline()
					#print(tmp)
					# find the level
					tmp_arr = tmp.split()
					ids = [d['handler'] for d in ret if 'handler' in d]
					if(len(tmp_arr)==20 and not handleid in ids):
						ret.append({'bat':tmp_arr[11], 'handler':handleid})

				# got all devices information
				if len(ret) == len(handlers):
					break

				line = f.readline()
		return ret

	def _getNewDevice(self, proc, uid, dev):
		ret = {'proc':proc, 'uid':uid, 'dev':dev, 'bat':-1, 'changed':False, 'handler':'', 'closed':False}
		return ret


	def _parseDeviceLink(self, cmd_lines):
		# the sixad driver maybe had a bug, sometime shoud be 2 link suck as:
		# lr-x------ 1 root root 64 Jan 19 10:54 35 -> /dev/input/js0
		# lr-x------ 1 root root 64 Jan 19 10:54 36 -> /dev/input/js1
		# when the real js0 reconnected, it changed:
		# lr-x------ 1 root root 64 Jan 19 10:54 35 -> /dev/input/js0 (deleted)
		# lr-x------ 1 root root 64 Jan 19 10:54 36 -> /dev/input/js1
		ret = None
		for line in cmd_lines:
			if '/dev/input/js' in line:
				if 'deleted' in line:
					ret = line.split()[-2]
					break

				tmp = line.split()[-1]
				if '/dev/input/js' in tmp:
					if ret:
						ret = ret + ',' + tmp
					else:
						ret = tmp

		return ret
