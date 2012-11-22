

import logging
import time
import sys

from twisted.internet.task import LoopingCall

import requests
from minion.plugin_api import AbstractPlugin,BlockingPlugin


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
                    self.report_results([{ "Summary":"Site has X-Frame-Options header but it has an unknown or invalid value: %s" % r.headers['x-frame-options'],"Severity":"High" }])
                else:
                    self.report_results([{ "Summary":"Site has a correct X-Frame-Options header", "Severity":"Info" }])
            else:
                self.report_results([{"Summary":"Site has no X-Frame-Options header set", "Severity":"High"}])


class HSTSPlugin(BlockingPlugin):

    """
    This plugin checks if the site sends out an HSTS header if it is HTTPS enabled.
    """

    def do_run(self):
        r = requests.get(self.configuration['target'])
        if r.status_code != 200:
            self.report_errors([{ "Summary":"Received a non-200 response: %d" % r.status_code, "Severity":"Info" }])
        else:            
            if r.url.startswith("https://") and 'hsts' not in r.headers:
                self.report_results([{ "Summary":"Site does not set HSTS header", "Severity":"High" }])
            else:
                self.report_results([{ "Summary":"Site sets HSTS header", "Severity":"Info" }])


class LongRunningPlugin(BlockingPlugin):

    def do_run(self):
        time.sleep(15)


class IncrementalAsyncPlugin(AbstractPlugin):

    def emit_results(self):
        logging.debug("IncrementalAsyncPlugin.emit_results")
        self.count += 1
        self.report_results([{"Summary":"This is issue #" + str(self.count), "Severity":"Low"}])
        if self.count == 3:
            self.loop.stop()
            self.report_finish()

    def do_start(self):
        logging.debug("IncrementalAsyncPlugin.do_start")
        self.count = 0
        self.loop = LoopingCall(self.emit_results)
        self.loop.start(1.0)

    def do_terminate(self):
        logging.debug("IncrementalAsyncPlugin.do_terminate")
        if self.loop:
            self.loop.stop()


class AbortedPlugin(BlockingPlugin):

    def do_run(self):
        self.report_abort(AbstractPlugin.EXIT_CODE_ABORTED)


class FailedPlugin(BlockingPlugin):

    def do_run(self):
        self.report_abort(AbstractPlugin.EXIT_CODE_FAILED)
        

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
            self.report_progress(25*n, description = self.PROGRESS[n-1])
            time.sleep(3)
            self.report_results([{"Summary":"This is issue #" + str(n), "Severity":"Low"}])

class IssueGeneratingPlugin(BlockingPlugin):

    COUNT = 3
    LEVELS = ['High', 'Medium', 'Low', 'Info']

    def do_run(self):
        for i in range(self.COUNT):
            for n in range(len(self.LEVELS)):
                issue = { "Summary":      "This is issue #" + str(n),
                          "Severity":     self.LEVELS[n],
                          "Confidence":   "Warning",
                          "Solution":     "This check is specific to Internet Explorer 8 and Google Chrome. Ensure each page sets a Content-Type header and the X-CONTENT-TYPE-OPTIONS if the Content-Type header is unknown",
                          "Further-Info": 'No known Anti-CSRF tokens [anticsrf, CSRFToken, __RequestVerificationToken] were found in the following HTML forms: [Form 1: "s" ].',
                          "URLs":         ["http://www.foo/abc", "http://www.foo/woo"],
                          "Description":  "No Anti-CSRF tokens were found in a HTML submission form. A cross-site request forgery is an attack that involves forcing a victim to send an HTTP request to a target destination without their knowledge or intent in order to perform an action as the victim. The underlying cause is application functionality using predictable URL/form actions in a repeatable way. The nature of the attack is that CSRF exploits the trust that a web site has for a user."}
                self.report_results([issue])
                time.sleep(1.5)
            
