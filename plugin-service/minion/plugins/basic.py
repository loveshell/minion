# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import logging
import os
import time
import sys

from twisted.internet.task import LoopingCall

import requests
from minion.plugin_api import AbstractPlugin,BlockingPlugin,ExternalProcessPlugin


class XFrameOptionsPlugin(BlockingPlugin):
    
    """
    This is a minimal plugin that does one http request to find out if
    the X-Frame-Options header has been set. It does not override anything
    except start() since that one check is quick and there is no point
    in suspending/resuming/terminating.

    All plugins run in a separate process so we can safely do a blocking
    HTTP request. The PluginRunner catches exceptions thrown by start() and
    will report that back as an error state of the plugin.
    """
    
    def do_run(self):        
        r = requests.get(self.configuration['target'])
        if r.status_code != 200:
            self.report_error([{"Info":"Received a non-200 response: %d" % r.status_code}])
        else:
            if 'x-frame-origin' in r.headers:
                if r.headers['x-frame-options'] not in ('DENY', 'SAMEORIGIN'):
                    self.report_issues([{ "Summary":"Site has X-Frame-Options header but it has an unknown or invalid value: %s" % r.headers['x-frame-options'],"Severity":"High" }])
                else:
                    self.report_issues([{ "Summary":"Site has a correct X-Frame-Options header", "Severity":"Info" }])
            else:
                self.report_issues([{"Summary":"Site has no X-Frame-Options header set", "Severity":"High"}])


class HSTSPlugin(BlockingPlugin):

    """
    This plugin checks if the site sends out an HSTS header if it is HTTPS enabled.
    """

    def do_run(self):
        r = requests.get(self.configuration['target'])
        if r.status_code != 200:
            self.report_issues([{ "Summary":"Received a non-200 response: %d" % r.status_code, "Severity":"Info" }])
        else:            
            if r.url.startswith("https://") and 'hsts' not in r.headers:
                self.report_issues([{ "Summary":"Site does not set HSTS header", "Severity":"High" }])
            else:
                self.report_issues([{ "Summary":"Site sets HSTS header", "Severity":"Info" }])

#
# All the plugins below are for test cases.
#

class LongRunningPlugin(BlockingPlugin):

    def do_run(self):
        for n in range(60):
            if self.stopped:
                return
            time.sleep(1)


class IncrementalAsyncPlugin(AbstractPlugin):

    def _emit_results(self):
        logging.debug("IncrementalAsyncPlugin.emit_results")
        self.count += 1
        self.report_issues([{"Summary":"This is issue #" + str(self.count), "Severity":"Low"}])
        if self.count == 10:
            self.loop.stop()
            self.report_finish()

    def do_start(self):
        logging.debug("IncrementalAsyncPlugin.do_start")
        self.count = 0
        self.loop = LoopingCall(self._emit_results)
        self.loop.start(1.0)

    def do_stop(self):
        logging.debug("IncrementalAsyncPlugin.do_stop")
        if self.loop:
            self.loop.stop()
            self.report_finish(exit_code=AbstractPlugin.EXIT_CODE_STOPPED)


class SuccessfulPlugin(BlockingPlugin):

    def do_run(self):
        self.report_finish(exit_code=AbstractPlugin.EXIT_CODE_FINISHED)


class FailedPlugin(BlockingPlugin):

    def do_run(self):
        self.report_finish(exit_code=AbstractPlugin.EXIT_CODE_FAILED)
        

class TimingOutPlugin(BlockingPlugin):

    def do_run(self):
        time.sleep(300)


class ExceptionPlugin(BlockingPlugin):

    def do_run(self):
        raise Exception("Oh no I am uncaught")


class IncrementalBlockingPlugin(BlockingPlugin):
    
    PROGRESS = ["Doing some work", "Doing some more work", "Almost done", "Finishing up!"]

    def do_run(self):
        for n in range(1,5):
            if self.stopped:
                return
            self.report_progress(25*n, description = self.PROGRESS[n-1])
            time.sleep(3)
            self.report_issues([{"Summary":"This is issue #" + str(n), "Severity":"Low"}])


class IssueGeneratingPlugin(BlockingPlugin):

    COUNT = 3
    LEVELS = ['High', 'Medium', 'Low', 'Info']

    def do_run(self):
        for i in range(self.COUNT):
            for n in range(len(self.LEVELS)):
                if self.stopped:
                    return
                issue = { "Summary": "This is the summary for issue #" + str(n),
                          "Severity": self.LEVELS[n],
                          "Confidence": "Warning",
                          "Solution": "This is the solution",
                          "Further-Info": "This is the Further-Info",
                          "URLs": ["http://www.foo/abc", "http://www.foo/woo"],
                          "Description": "This is the description."}
                self.report_issues([issue])
                time.sleep(1.5)
            

class ReportGeneratingPlugin(BlockingPlugin):
    
    def do_run(self):
        
        with open(os.path.join(self.work_directory, "temporary.txt"), "w") as f:
            f.write("This is a temporary file that we do not want in the artifacts zip\n")
        
        with open(os.path.join(self.work_directory, "report.txt"), "w") as f:
            f.write("This is my report that we do want in the artifacts zip\n")

        self.report_artifacts("Some Tool Report", ["report.txt"])
        self.report_issues([{"Summary":"This is an issue", "Severity":"Low"}])


class SimpleExternalPlugin(ExternalProcessPlugin):

    TOOL_NAME = "test.sh"

    def do_start(self):
        # Create our test tool in our work directory.
        path = os.path.join(self.work_directory, self.TOOL_NAME)
        with open(path, "w") as f:
            f.write("#!/bin/sh\n")
            f.write("for message in foo bar baz; do echo $message; sleep 3; done\n")
        os.chmod(path, 0755)
        # Spawn our tool
        self.output = ""
        self.spawn(path, [])

    def do_process_stdout(self, data):
        self.output += data

    def do_process_ended(self, status):
         if self.stopping and status == 9:
             self.report_finish("STOPPED")
         elif status == 0:
             issues = []
             for line in self.output.strip().split("\n"):
                 issues.append({"Summary":"Issue " + line, "Severity":"Low"})
             self.report_issues(issues)
             self.report_finish()
         else:
             self.report_finish("FAILED")
             
