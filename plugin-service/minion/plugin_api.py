# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import logging
import os
import sys

from twisted.internet import reactor
from twisted.internet.threads import deferToThread
from twisted.internet.error import ProcessDone, ProcessTerminated
from twisted.internet.protocol import ProcessProtocol
import zope.interface


class IPluginRunnerCallbacks(zope.interface.Interface):

    """
    Plugin implementations use these methods to notify the PluginRunner
    when its state has changed.
    """

    def report_progress(percentage, description):
        """This long running plugin has made some progress"""
    def report_results(results):
        """Plugin has results to report."""
    def report_errors(errors):
        """Plugin has errors to report."""
    def report_artifacts(name, paths):
        """Plugin has files available."""
    def report_finish():
        """Plugin is done"""
    def report_abort(exit_code = 1):
        """Signal the plugin container that we need to abort. Process will exit."""


class IPlugin(zope.interface.Interface):

    """
    All plugins should implement this. This is their API.
    """
    
    # Plugin attributes, provided/configured by the PluginRunner.

    callbacks = zope.interface.Attribute("""The callbacks to send data back""")
    reactor = zope.interface.Attribute("""The reactor this plugin in running in""")
    site = zope.interface.Attribute("""The site to scan""")
    work_directory = zope.interface.Attribute("""The path to the work directory""")

    # Plugin lifecycle methods. These are all called by the PluginRunner.

    def do_start():
        """Start the plugin"""
    def do_start():
        """Start the plugin"""
    def do_suspend():
        """Suspend the plugin"""
    def do_resume():
        """Resume the plugin"""
    def do_terminate():
        """Terminate the plugin"""


class AbstractPlugin:

    """
    Abstract plugin implementation that implements a plugin that does
    nothing. This is a good place for standard behaviour, etc.
    """

    @classmethod
    def name(cls):
        return getattr(cls, "PLUGIN_NAME", cls.__name__)

    @classmethod
    def version(cls):
        return getattr(cls, "PLUGIN_VERSION", "0.0")

    zope.interface.implements(IPlugin, IPluginRunnerCallbacks)
    
    # Plugin methods. By default these do nothing.

    def do_configure(self):
        pass

    def do_start(self):
        self.report_finish()
    
    def do_suspend(self):
        pass

    def do_resume(self):
        pass
    
    def do_terminate(self):
        pass

    # These are simply mapped to the callbacks for convenience

    def report_progress(self, percentage, description):
        self.callbacks.report_progress(percentage, description)

    def report_results(self, results):
        self.callbacks.report_results(results)

    def report_errors(self, errors):
        self.callbacks.report_errors(errors)

    def report_artifacts(self, name, paths):
        self.callbacks.report_artifacts(name, paths)

    def report_abort(self, exit_code = 1):
        self.callbacks.report_abort(exit_code)

    def report_finish(self):
        self.callbacks.report_finish()

    EXIT_CODE_SUCCESS = 0
    EXIT_CODE_ABORTED = 1
    EXIT_CODE_FAILED  = 2


class BlockingPlugin(AbstractPlugin):

    """
    Plugin that needs to run blocking code. It executes do_run() in a thread. It is
    not expected to support suspend/resume/terminate.
    """

    def do_run(self):
        logging.error("You forgot to override BlockingPlugin.run()")

    def _finish_with_success(self, result):
        logging.debug("BlockingPlugin._finish_with_success")
        self.callbacks.report_finish()

    def _finish_with_failure(self, failure):
        logging.error("BlockingPlugin._finish_with_failure: " + str(failure))
        self.report_abort(AbstractPlugin.EXIT_CODE_FAILED)

    def do_start(self):
        return deferToThread(self.do_run).addCallback(self._finish_with_success).addErrback(self._finish_with_failure)
        

class ExternalProcessProtocol(ProcessProtocol):

    """
    Protocol that delegates incoming data on stdout and stderr to the plugin. The
    plugin can capture the data and wait until the process is finished or process
    it immediately and report results back.
    """

    def __init__(self, plugin):
        self.plugin = plugin

    def outReceived(self, data):
        self.plugin.do_process_stdout(data)

    def errReceived(self, data):
        self.plugin.do_process_stderr(data)

    def processEnded(self, reason):
        if isinstance(reason.value, ProcessDone):
            try:
                self.plugin.do_process_ended(reason.value.status)
            except Exception as e:
                logging.exception("Plugin threw an exception in do_process_ended")
                self.plugin.callbacks.report_finish()

class ExternalProcessPlugin(AbstractPlugin):
    
    """
    Plugin that spawns an external tool. This makes it simple to execute tools like
    nmap. The default behaviour of do_terminate() is to simply kill the external tool.
    """

    def locate_program(self, program_name):
        for path in os.getenv('PATH').split(os.pathsep):
            program_path = os.path.join(path, program_name)
            if os.path.isfile(program_path) and os.access(program_path, os.X_OK):
                return program_path

    def spawn(self, path, arguments):
        protocol = ExternalProcessProtocol(self)
        name = path.split('/')[-1]
        logging.debug("Executing %s %s" % (path, " ".join([name] + arguments)))
        self.process = reactor.spawnProcess(protocol, path, [name] + arguments)

    def do_process_ended(self, status):
        self.callbacks.report_finish()

    def do_process_stdout(self, data):
        pass

    def do_process_stderr(self, data):
        pass

    def do_terminate(self):
        if self.process:
            self.process.signalProcess('KILL')
