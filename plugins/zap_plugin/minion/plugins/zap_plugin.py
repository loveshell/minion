# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


import logging
import os
import random
import tempfile
import time

from twisted.internet import reactor
from twisted.internet.threads import deferToThread
from minion.plugin_api import ExternalProcessPlugin
from zap import ZAP


class ZAPPlugin(ExternalProcessPlugin):

    ZAP_NAME = "zap.sh"
    
    def do_configure(self):
        logging.debug("ZAPPlugin.do_configure")
        self.zap_path = self.locate_program(self.ZAP_NAME)
        if self.zap_path is None:
            raise Exception("Cannot find %s in PATH" % ZAP_NAME)
        # Validate the configuration
        if self.configuration.get('target') is None or len(self.configuration['target']) == 0:
            raise Exception("Missing or invalid target in configuration")

    def do_process_ended(self, status):
        logging.debug("ZAPPlugin.do_process_ended")
        self.callbacks.report_finish()

    def do_start(self):
        logging.debug("ZAPPlugin.do_start")
        # Start ZAP in daemon mode
        self.zap_port = self._random_port()
        self.zap_dir = tempfile.gettempdir() + '/zap_' + str(self.zap_port)
        args = ['-daemon', '-port', str(self.zap_port), '-dir', self.zap_dir]
        self.spawn(self.zap_path, args)
        self.callbacks.report_files([{'id' : 'zaplog', 'name' : 'ZAP log file', 'location' : self.zap_dir + '/zap.log'}])
        
        # Start the main code in a thread
        return deferToThread(self._blocking_zap_main)
        
    def _random_port(self):
        return random.randint(8192, 16384)

    def _blocking_zap_main(self):
        logging.debug("ZAPPlugin._blocking_zap_main")
        try:
            self.zap = ZAP(proxies={'http': 'http://127.0.0.1:%d' % self.zap_port, 'https': 'http://127.0.0.1:%d' % self.zap_port})
            target = self.configuration['target']
            time.sleep(5)
            logging.info('Accessing target %s' % target)
            
            while (True):
                try:
                    self.zap.urlopen(target)
                    break
                except:
                    logging.exception("Failed to zap.urlopen")
                    time.sleep(2)
            
            # Give the sites tree a chance to get updated
            time.sleep(2)
            
            logging.info('Spidering target %s' % target)
            self.zap.start_spider(target)
            # Give the Spider a chance to start
            time.sleep(2)
            while (int(self.zap.spider_status[0]) < 100):
                logging.debug('Spider progress %s' % self.zap.spider_status[0])
                progress = int(self.zap.spider_status[0]) / 2
                self.report_progress(progress, 'Spidering target')
                time.sleep(5)
            
            logging.debug('Spider completed')
            # Give the passive scanner a chance to finish
            time.sleep(5)
            
            logging.debug('Scanning target %s' % target)
            self.zap.start_scan(target)
            time.sleep(5)
            while (int(self.zap.scan_status[0]) < 100):
                logging.debug('Scan progress %s' % self.zap.scan_status[0])
                progress = 50 + int(self.zap.spider_status[0]) / 2
                self.report_progress(progress, 'Scanning target')
                self.report_results(self.get_results())
                time.sleep(5)
    
            logging.debug('Scan completed? %s' % self.zap.scan_status[0])
            
            self.report_results(self.get_results())
            
            logging.info('Scan completed, shutting down')
            self.zap.shutdown()
            self.report_finish()
            
        except Exception as e:
            logging.exception("Error while executing zap plugin")

    def get_results(self):
        alerts = self.zap.alerts
        issues = [] 

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

        return issues

