# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


import os
from xml.etree import ElementTree
from minion.plugin_api import ExternalProcessPlugin


def parse_garmr_xml(xml):
    root = ElementTree.fromstring(xml)
    results = []
    for testsuite in root.iter('testsuite'):        
        for testcase in testsuite.iter('testcase'):
            failure = testcase.find('failure')
            skipped = testcase.find('skipped')
            severity = "info"
            if failure is not None:
                severity = "high"
            elif skipped is not None:
                severity = "info"
	    results.append({ 'summary': testcase.get('name'), 'severity': severity})
    return results


class GarmrPlugin(ExternalProcessPlugin):

    GARMR_NAME = "garmr"
    GARMR_ARGS = ['-o', '/dev/stdout', '-u']

    def do_start(self):
        garmr_path = self.locate_program(self.GARMR_NAME)
        if garmr_path is None:
            raise Exception("Cannot find garm in path")
        self.output = ""
        self.spawn(garmr_path, self.GARMR_ARGS + [self.configuration['target']])

    def do_process_stdout(self, data):
        self.output += data

    def do_process_ended(self, status):
        self.callbacks.report_results(parse_garmr_xml(self.output))
        self.callbacks.report_finish()
