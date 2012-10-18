'''
This is a basic Minion Plugin for the OWASP Zed Attack Proxy (ZAP)

It all works, but you will have to have ZAP installed.
And the script will need tweaking on Linux, as theres no default directory -
right now you'll need to hard code that - plan to add config file support soon.
'''

from MinionPlugin import MinionPlugin
import threading
import time
import logging
import os
import platform
#import subprocess
from zap import ZAP

class ZapScanThread(threading.Thread):
	
	zap = None
	target = None
		
	def setZapPlugin(self, zapPlugin):
		self.zapPlugin = zapPlugin
		self.status = MinionPlugin.STATUS_PENDING

	def setTarget(self, target):
		self.target = target
				
	def run(self):
		logging.debug("run()")
		self.status = MinionPlugin.STATUS_RUNNING
		try:
			self.zapPlugin.zap.urlopen(self.target)
			
			# Give the sites tree a chance to get updated
			time.sleep(2)
			
			logging.debug('Spidering target %s' % self.target)
			self.zapPlugin.zap.start_spider(self.target)
			# Give the Spider a chance to start
			time.sleep(2)
			while (int(self.zapPlugin.zap.spider_status[0]) < 100):
				logging.debug('Spider progress %s' % self.zapPlugin.zap.spider_status[0])
				time.sleep(5)
			
			logging.debug('Spider completed')
			# Give the passive scanner a chance to finish
			time.sleep(5)
			
			logging.debug('Scanning target %s' % self.target)
			self.zapPlugin.zap.start_scan(self.target)
			time.sleep(5)
			while (int(self.zapPlugin.zap.scan_status[0]) < 100):
				logging.debug('Scan progress %: ' % self.zapPlugin.zap.scan_status[0])
				time.sleep(5)
	
			logging.debug('Scan completed? %s' % self.zapPlugin.zap.scan_status[0])
			self.status = MinionPlugin.STATUS_COMPLETE
			
			# Save the results so the plugin can get them after ZAP is stopped
			self.zapPlugin.results = self.zapPlugin.zap.alerts
			
			logging.debug('Scan completed, shutting down')
			self.zapPlugin.zap.shutdown()
			
		except Exception as e:
			logging.error("run() " + e)
			self.status = MinionPlugin.STATUS_FAILED
		
	def getProgress(self):
		logging.debug("getProgress()")
		progress = int(self.zapPlugin.zap.spider_status[0]) / 2
		if progress == 50:
			progress += (int(self.zapPlugin.zap.scan_status[0]) / 2)
		logging.debug("getProgress() returning %i" %progress)
		return progress 
	
	def getState(self):
		logging.debug("getState() " + self.status)
		return self.status

class ZapPlugin(MinionPlugin):

	default = {
		"template" : {
			"target" : { "type" : "url", "is_list" : True, "required" : True}
		},
		"safechecks" : { "type" : "bool", "value" : True}
	}

	def __init__(self):
		logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
		MinionPlugin.__init__(self, ZapPlugin.default)

		self.zap = ZAP(proxies={'http': 'http://127.0.0.1:8090', 'https': 'http://127.0.0.1:8090'})
		self.state = MinionPlugin.STATUS_PENDING

		self.messages = {
        	"PENDING" : "Plugin is pending execution.",
        	"WAITING" : "Execution is suspending, waiting for RESUME.",
        	"RUNNING" : "Execution is in progress.",
        	"COMPLETE" : "Execution is finished.",
        	"CANCELLED" : "Execution was cancelled.",
        	"FAILED" : "Execution failed."
		}
		self.allow_states = {
        	MinionPlugin.STATUS_PENDING : [MinionPlugin.STATE_START],
        	MinionPlugin.STATUS_WAITING : [MinionPlugin.STATE_RESUME, MinionPlugin.STATE_TERMINATE],
        	MinionPlugin.STATUS_RUNNING : [MinionPlugin.STATE_SUSPEND, MinionPlugin.STATE_TERMINATE],
        	MinionPlugin.STATUS_COMPLETE : [],
        	MinionPlugin.STATUS_CANCELLED : [],
        	MinionPlugin.STATUS_FAILED : []
        }

	def start_zap(self):
		# TODO: Include in the ZAP python API in the future
		# TODO: check if ZAP already running?
		# TODO: loads of override options in the configs ;)
		if platform.system() == 'Windows':
			#zap_script = ['start /b zap.bat']
			zap_script = 'start /b zap.bat'
			zap_path = 'C:\Program Files (x86)\OWASP\Zed Attack Proxy'
			if not os.path.exists(zap_path):
				# Win XP default path
				zap_path = "C:\Program Files\OWASP\Zed Attack Proxy"
		elif platform.system() == 'Darwin':
			#zap_script = ['java', '-jar', 'zap.jar']
			zap_script = 'java -jar zap.jar'
			zap_path = '/Applications/OWASP ZAP.app/Contents/Resources/Java'
		else:
			zap_script = './zap.sh'
			# TODO: no std path on Linux - need option to specify one
			
		# This should be conditional on options
		#zap_script.append(' -daemon')
		zap_script += ' -daemon'

		# Start ZAP
		logging.debug("Starting ZAP in %s using %s" % (zap_path, zap_script))
		os.chdir(zap_path)
		os.system(zap_script)
		'''
		subprocess may be better, but I had problems getting it to work on Windows
		subprocess.Popen(zap_script, cwd=zap_path, stdout=subprocess.PIPE)
		'''

	def stop_zap(self):
		self.zap.shutdown()
		
	def do_validate(self, config):
		return True

	def do_validate_key(self, key, value):
		return True

	def do_status(self):
		logging.debug("ZapPlugin.do_status " + self.state)
		if not hasattr(self, 'zct'):
			return self.create_status(True, self.messages[self.state], self.state)
		progress = self.zct.getProgress()
		
		#if self.state == MinionPlugin.STATUS_COMPLETE and self.zct.getState() == MinionPlugin.STATUS_RUNNING:
		#	self.stop_zap()  
		
		self.state = self.zct.getState()
		
		if progress == 100:
			logging.debug('ZCT state is %s' % self.state)
			#self.state = MinionPlugin.STATUS_COMPLETE
			
		return self.create_status(True, self.messages[self.state] + " " + str(progress), self.state)

	def do_start(self):
		logging.debug("do_start()")
		try:
			self.start_zap()
			time.sleep(30)
			
			self.zct = ZapScanThread()
			self.zct.setZapPlugin(self)
			self.zct.setTarget(self.getValue("target"))
			self.zct.start()
			self.state = MinionPlugin.STATUS_RUNNING
		except Exception as e:
			logging.error("do_start() " + e)
		
		#return self.create_status(True, self.messages[self.state], self.state)
		return self.create_std_status(True, self.state)

	def do_suspend(self):
		self.state = MinionPlugin.STATUS_WAITING
		return self.create_status(True, self.messages[self.state], self.state)

	def do_resume(self):
		self.state = MinionPlugin.STATUS_RUNNING
		return self.create_status(True, self.messages[self.state], self.state)

	def do_terminate(self):
		self.state = MinionPlugin.STATUS_CANCELLED
		return self.create_status(True, self.messages[self.state], self.state)

	def do_get_states(self):
		return self.allow_states[self.state]

	def do_get_results(self):
		logging.debug("do_get_results()")
		issues = [] 
		if not hasattr(self, 'zct'):
			return issues
		# TODO implement properly
		'''
			Not currently using: reference, param, attack
			And should combine alerts listing all of the related urls instead of including them individually 
		'''
		if hasattr(self, 'results'):
			alerts = self.results
		else:
			alerts = self.zap.alerts
	
	
		for alert in alerts:
			found = False
			for issue in issues:
				# TODO should test other values here as well
				if alert.get('alert') == issue['Summary']:
					issue['URLs'].append(alert.get('url'))
					found = True
					break
				if found:
					break
			if not found:
				issues.append({
					"Summary" : alert.get('alert'), 
					"Description" : alert.get('description'), 
					"Further-Info" : alert.get('other'), 
					"Severity" : alert.get('risk'), 
					"Confidence" : alert.get('reliability'), 
					"Solution" : alert.get('solution'), 
					"URLs" : [alert.get('url')]});

		return {"issues" : issues};

	# TODO hacking
	def create_issue(self, summary, description, moreinfo, severity, confidence, urlList):
		return {
			"Summary" : summary, 
			"Description" : description, 
			"Further-Info" : moreinfo, 
			"Severity" : severity, 
			"Confidence" : confidence, 
			"URLs" : urlList}
		
