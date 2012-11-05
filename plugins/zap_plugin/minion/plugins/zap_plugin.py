# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


import logging
import os
import platform
import time
import traceback
from minion.plugin_api import BlockingPlugin
from zap import ZAP


class ZAPPlugin(BlockingPlugin):

    level = logging.DEBUG    
    logging.basicConfig(level=level, format='%(asctime)s %(levelname).1s %(message)s', datefmt='%y-%m-%d %H:%M:%S')

    zap = ZAP(proxies={'http': 'http://127.0.0.1:8080', 'https': 'http://127.0.0.1:8080'})

    ZAP_NAME = "zap.sh"
    
    def locate_program(self, program_name):
        for path in os.getenv('PATH').split(os.pathsep):
            program_path = os.path.join(path, program_name)
            if os.path.isfile(program_path) and os.access(program_path, os.X_OK):
                return program_path

    def spawn(self, path):
        logging.info("Executing %s" % (path))
        os.system(path)

    def do_configure(self):
        logging.info("ZAP do_configure")

    def do_run(self):
        logging.info("ZAP do_start")
        zap_path = self.locate_program(self.ZAP_NAME)
        if zap_path is None:
            raise Exception("Cannot find ZAP in path")
        logging.debug("ZAP path=" + zap_path)
        
        self.output = ""
        target = self.configuration['target']
        if target is None or len(target) == 0:
            raise Exception("Target not specified")

        logging.debug("ZAP path=" + zap_path)
        
        zap_path +=  ' -daemon > zap.out &'
        self.spawn(zap_path)

        try:
            time.sleep(5)
            logging.info('Accessing target %s' % target)
            
            while (True):
                try:
                    self.zap.urlopen(target)
                    break
                except:
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
            logging.error("run() " + str(e))
            logging.error(traceback.format_exc())

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

