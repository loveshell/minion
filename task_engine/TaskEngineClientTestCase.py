'''
Created on 25 Sep 2012

@author: test
'''
import unittest
from TaskEngineClient import TaskEngineClient

class TaskEngineTestCase(unittest.TestCase):


    def setUp(self):
        pass


    def tearDown(self):
        pass

    def testBasicApi(self):
        ''' Was hoping to be able to use the TaskEngineTestCase for testing the client, but
        there are reasons why its not easy to do that right now
        '''
        te = TaskEngineClient("http://localhost:8181")
        
        ''' Should now be one plugion '''
        result = te.get_all_plugins()
        if (len(result["plugins"]) is not 1):
            self.fail("Unexpected number of plugin services returned %s" % result)

        # TODO: Check the results - just doing manually nowe ;)            
        ''' Get the interface for a plugin '''
        result = te.get_plugin_template("TemplatePlugin", 1)
        print result
        
        print "create_plugin_session"
        result = te.create_plugin_session("TemplatePlugin", 1)
        print result

        session = result["session"]
        service_name = result["plugin_service"]["name"]
        result = te.get_plugin_service_session_status(service_name, session)
        print result

        result = te.set_plugin_service_session_value(service_name, session, "target", "http://localhost:8080/")
        print result

        print "get_plugin_service_session_config"
        result = te.get_plugin_service_session_config(service_name, session)
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