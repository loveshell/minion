'''
Created on 24 Sep 2012

@author: test
'''
import unittest
from MinionPlugin import MinionPlugin
from ZapPlugin import ZapPlugin
from time import sleep

class ZapPluginTestCase(unittest.TestCase):

    def check_result(self, result, expected):
        if (result.get("status") != expected):
            self.fail("Expected " + expected + " got " + result.get("status") )

    def XXtestStandardRunName(self):
        plugin = ZapPlugin()
        self.check_result(plugin.status(), MinionPlugin.STATUS_PENDING);
        plugin.start()
        self.check_result(plugin.status(), MinionPlugin.STATUS_RUNNING);
        plugin.suspend()
        self.check_result(plugin.status(), MinionPlugin.STATUS_WAITING);
        plugin.resume()
        self.check_result(plugin.status(), MinionPlugin.STATUS_RUNNING);
        plugin.terminate()
        self.check_result(plugin.status(), MinionPlugin.STATUS_CANCELLED);

    def testBodgeitRunName(self):
        plugin = ZapPlugin()
        self.check_result(plugin.status(), MinionPlugin.STATUS_PENDING);
        plugin.setValue("target", "http://localhost:8080/bodgeit/")
        plugin.start()
        self.check_result(plugin.status(), MinionPlugin.STATUS_RUNNING);
        
        while plugin.status().get("status") == MinionPlugin.STATUS_RUNNING:
            #print ("TEST Status: %s Message: %s", (plugin.status().get("status"), plugin.status().get("message") ))
            sleep(5)
            
        print plugin.getResults()
            

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()