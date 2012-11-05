

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
            self.report_error([{"info":"Received a non-200 response: %d" % r.status_code}])
        else:
            if 'x-frame-origin' in r.headers:
                if r.headers['x-frame-options'] not in ('DENY', 'SAMEORIGIN'):
                    self.report_results([{ "summary":"Site has X-Frame-Options header but it has an unknown or invalid value: %s" % r.headers['x-frame-options'],"severity":"high" }])
                else:
                    self.report_results([{ "summary":"Site has a correct X-Frame-Options header", "severity":"info" }])
            else:
                self.report_results([{"summary":"Site has no X-Frame-Options header set", "severity":"high"}])


class HSTSPlugin(BlockingPlugin):

    """
    This plugin checks if the site sends out an HSTS header if it is HTTPS enabled.
    """

    def do_run(self):
        r = requests.get(self.configuration['target'])
        if r.status_code != 200:
            self.report_errors([{ "summary":"Received a non-200 response: %d" % r.status_code, "severity":"info" }])
        else:            
            if r.url.startswith("https://") and 'hsts' not in r.headers:
                self.report_results([{ "summary":"Site does not set HSTS header", "severity":"high" }])
            else:
                self.report_results([{ "summary":"Site sets HSTS header", "severity":"info" }])


class LongRunningPlugin(BlockingPlugin):

    def do_run(self):
        time.sleep(15)


class IncrementalAsyncPlugin(AbstractPlugin):

    def emit_results(self):
        logging.debug("IncrementalAsyncPlugin.emit_results")
        self.count += 1
        self.report_results([{"summary":"This is issue #" + str(self.count), "severity":"low"}])
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
    
    def do_run(self):
        for n in range(0,10):
            time.sleep(2)
            self.report_results([{"summary":"This is issue #" + str(n), "severity":"low"}])
