# A simple Template plugin

from MinionPlugin import MinionPlugin
import threading
import time
import logging
from zap import ZAP

# TODO: This is work in progress!

class ZapScanThread(threading.Thread):
	
	zap = None
	target = None
		
	def setZap(self, zap):
		self.zap = zap
		self.status = MinionPlugin.STATUS_PENDING

	def setTarget(self, target):
		self.target = target
				
	def run(self):
		logging.debug("run()")
		self.status = MinionPlugin.STATUS_RUNNING
		try:
			self.zap.urlopen(self.target)
			
			# Give the sites tree a chance to get updated
			time.sleep(2)
			
			logging.debug('Spidering target %s' % self.target)
			self.zap.start_spider(self.target)
			# Give the Spider a chance to start
			time.sleep(2)
			while (int(self.zap.spider_status[0]) < 100):
				logging.debug('Spider progress %s' % self.zap.spider_status[0])
				time.sleep(5)
			
			logging.debug('Spider completed')
			# Give the passive scanner a chance to finish
			time.sleep(5)
			
			logging.debug('Scanning target %s' % self.target)
			self.zap.start_scan(self.target)
			time.sleep(5)
			while (int(self.zap.scan_status[0]) < 100):
				logging.debug('Scan progress %: ' % self.zap.scan_status[0])
				time.sleep(5)
	
			logging.debug('Scan completed? %s' % self.zap.scan_status[0])
			self.status = MinionPlugin.STATUS_COMPLETE
			logging.debug('Scan completed? zap status %s' % self.status)
		except Exception as e:
			logging.error("run() " + e)
			self.status = MinionPlugin.STATUS_FAILED
		
	def getProgress(self):
		logging.debug("getProgress()")
		progress = int(self.zap.spider_status[0]) / 2
		if progress == 50:
			progress += (int(self.zap.scan_status[0]) / 2)
		logging.debug("getProgress() returning %i" %progress)
		return progress 
	
	def getState(self):
		logging.debug("getState() " + self.status)
		return self.status

class ZapPlugin(MinionPlugin):

	zap = ZAP(proxies={'http': 'http://127.0.0.1:8090', 'https': 'http://127.0.0.1:8090'})

	default = {
		"template" : {
			"target" : { "type" : "url", "is_list" : True, "required" : True}
		},
		"safechecks" : { "type" : "bool", "value" : True}
	}

	def __init__(self):
		logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
		MinionPlugin.__init__(self, ZapPlugin.default)

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


	def do_validate(self, config):
		return True

	def do_validate_key(self, key, value):
		return True

	def do_status(self):
		logging.debug("ZapPlugin.do_status " + self.state)
		if not hasattr(self, 'zct'):
			return self.create_status(True, self.messages[self.state], self.state)
		progress = self.zct.getProgress()
		state = self.zct.getState()
		if progress == 100:
			logging.debug('ZCT state is %s' % state)
			#self.state = MinionPlugin.STATUS_COMPLETE
			
		return self.create_status(True, self.messages[state] + " " + str(progress), state)

	def do_start(self):
		logging.debug("do_start()")
		try:
			self.zct = ZapScanThread()
			self.zct.setZap(self.zap)
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
		for alert in self.zap.alerts:
			issues.append({
				"Summary" : alert.get('alert'), 
				"Description" : alert.get('description'), 
				"Further-Info" : alert.get('other'), 
				"Severity" : alert.get('risk'), 
				"Confidence" : alert.get('reliability'), 
				"Solution" : alert.get('solution'), 
				"URLs" : alert.get('url')});
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
		
