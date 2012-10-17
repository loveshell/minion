# A simple Template plugin

from MinionPlugin import MinionPlugin

class TemplatePlugin(MinionPlugin):

	VERSION = 1
	TYPE = MinionPlugin.PLUGIN_TYPE_WEBAPP

	default = {
		"template" : {
			"target" : { "type" : "url", "is_list" : True, "required" : True}
		},
		"safechecks" : { "type" : "bool", "value" : True}
	}

	def __init__(self):
		MinionPlugin.__init__(self, TemplatePlugin.default)
		#super().__init__(TemplatePlugin.default)

		self.state = MinionPlugin.STATUS_PENDING
		self.progress = 0

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
		if self.state is MinionPlugin.STATUS_RUNNING:
			''' Fake progress - inc 10% each time ;) '''
			self.progress += 10
			if self.progress >= 100:
				self.state = MinionPlugin.STATUS_COMPLETE
				
		if self.state is MinionPlugin.STATUS_RUNNING:
			return self.create_status_plus(True, self.messages[self.state], self.state, {"progress" : self.progress})
		
		return self.create_status(True, self.messages[self.state], self.state)

	def do_start(self):
		self.state = MinionPlugin.STATUS_RUNNING
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
		''' Base on the faked progress '''
		issues = [] 
		if self.progress >= 20:
			issues.append(self.create_issue("Issue1", "Cookie set without HttpOnly flag", "Description 1", "Moreinfo 1", "LOW", "DEFINITE", ["http://localhost/home"]));
		if self.progress >= 40:
			issues.append(self.create_issue("Issue2", "Password Autocomplete in browser", "Description 2", "Moreinfo 2", "LOW", "DEFINITE", ["http://localhost/login"]));
		if self.progress >= 60:
			issues.append(self.create_issue("Issue3", "Cross Site Script", "Description 3", "Moreinfo 3", "HIGH", "LIKELY", ["http://localhost/basket"]));
			issues.append(self.create_issue("Issue4", "Cross Site Script", "Description 4", "Moreinfo 4", "HIGH", "LIKELY", ["http://localhost/checkout"]));
		if self.progress >= 80:
			issues.append(self.create_issue("Issue4", "SQL Injection", "Description 5", "Moreinfo 5", "HIGH", "LIKELY", ["http://localhost/basket"]));
		return {"issues" : issues};

	def create_issue(self, ref, summary, description, moreinfo, severity, confidence, urlList):
		return {
			"Reference" : ref, 
			"Summary" : summary, 
			"Description" : description, 
			"Further-Info" : moreinfo, 
			"Severity" : severity, 
			"Confidence" : confidence, 
			"URLs" : urlList}