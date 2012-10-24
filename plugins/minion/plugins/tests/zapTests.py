'''
Created on 24 Sep 2012

@author: psiinon
'''
import unittest
from minion.plugins.minionBase import MinionPlugin
from minion.plugins.zap import ZapPlugin
from time import sleep

class ZapPluginTestCase(unittest.TestCase):

    def check_result(self, result, expected):
        if (result.get("status") != expected):
            self.fail("Expected " + expected + " got " + result.get("status") )

    def testBodgeitRunName(self):
        plugin = ZapPlugin()
        self.check_result(plugin.status(), MinionPlugin.STATUS_PENDING);
        plugin.setValue("target", "http://localhost:8080/bodgeit/")
        plugin.start()
        self.check_result(plugin.status(), MinionPlugin.STATUS_RUNNING);
        
        while plugin.status().get("status") == MinionPlugin.STATUS_RUNNING:
            #print ("TEST Status: %s Message: %s", (plugin.status().get("status"), plugin.status().get("message") ))
            sleep(5)
            
        for issue in plugin.getResults()['issues']:
            print issue
        
            

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
    
