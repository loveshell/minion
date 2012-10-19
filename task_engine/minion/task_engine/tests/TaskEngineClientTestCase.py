'''
Created on 25 Sep 2012

@author: test
'''

import random
import unittest
import threading
import time

from minion.task_engine.TaskEngineClient import TaskEngineClient

class ServerThread(threading.Thread):
    def __init__(self, port):
        threading.Thread.__init__(self)
        self.port = port
    def run(self):
        from minion.task_engine.TaskEngineRestApi import app
        from bottle import run
        run(app, host="127.0.0.1", port=self.port)

class TaskEngineTestCase(unittest.TestCase):

    def setUp(self):
        self.server_port = random.randint(16384,32767)
        self.server_thread = ServerThread(self.server_port)
        self.server_thread.daemon = True
        self.server_thread.start()
        time.sleep(2.5) # Give the server a little time start

    def tearDown(self):
        pass

    def testBasicApi(self):
        ''' Was hoping to be able to use the TaskEngineTestCase for testing the client, but
        there are reasons why its not easy to do that right now
        '''
        te = TaskEngineClient("http://127.0.0.1:" + str(self.server_port))
        
        ''' Should now be one plugin '''
        result = te.get_all_plugins()
        if (len(result["plugins"]) is not 1):
            self.fail("Unexpected number of plugin services returned %s" % result)

        # TODO: Check the results - just doing manually nowe ;)            
        ''' Get the interface for a plugin '''
        result = te.get_plugin_template("TemplatePlugin", 1)
        print "\n\nResult after get_plugin_template: "
        print result
        
        result = te.create_plugin_session("TemplatePlugin", 1)
        print "\n\ncreate_plugin_session result:"
        print result

        session = result["session"]
        service_name = result["plugin_service"]["name"]
        result = te.get_plugin_service_session_status(service_name, session)
        print "\n\nget_plugin_service_session_status result:"
        print result

        result = te.set_plugin_service_session_value(service_name, session, "target", "localhost")
        #te.set_plugin_service_session_value(service_name, session, "target", "http://localhost")
        #te.set_plugin_service_session_config(service_name, session, {"target" : "http://localhost"})
        #te.set_plugin_service_session_config(service_name, session, "XXX")
        print "\n\nset_plugin_service_session_value:"
        print result
        result = te.set_plugin_service_session_state(service_name, session, "START")
        if ( result["status"] != "RUNNING"):
            self.fail("Unexpected result - should have worked %s" % result)

        result = te.get_plugin_service_session_status(service_name, session)
        print result
        result = te.get_plugin_service_session_results(service_name, session)
        print result

        
if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
