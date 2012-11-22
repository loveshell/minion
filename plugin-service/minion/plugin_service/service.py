#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/

import datetime
import json
import logging
import optparse
import os
import time
import uuid

import zope.interface
from twisted.internet import protocol
from twisted.internet import reactor
from twisted.internet.error import ProcessDone, ProcessTerminated

from minion.plugin_api import AbstractPlugin

class PluginRunnerProcessProtocol(protocol.ProcessProtocol):

    def __init__(self, plugin_session):
        self.plugin_session = plugin_session

    def connectionMade(self):
        logging.debug("PluginRunnerProcessProtocol.connectionMade")
        pass

    # TODO We should redirect plugin output to separate log files like date-session.{stdout,stderr}

    def outReceived(self, data):
        logging.debug("PluginRunnerProcessProtocol.outReceived: " + data)

    def errReceived(self, data):
        logging.debug("PluginRunnerProcessProtocol.errReceived: " + data)

    def processEnded(self, reason):
        #logging.debug("PluginRunnerProcessProtocol.processEnded %s" % str(reason))
        self.plugin_session.duration = int(time.time()) - self.plugin_session.started
        if isinstance(reason.value, ProcessDone):
            self.plugin_session.state = 'FINISHED'
        elif isinstance(reason.value, ProcessTerminated):
            exit_code = reason.value.status / 256
            if exit_code == AbstractPlugin.EXIT_CODE_ABORTED:
                self.plugin_session.state = 'ABORTED' # User aborted
            elif exit_code == AbstractPlugin.EXIT_CODE_FAILED:
                self.plugin_session.state = 'FAILED'  # Failed because of an exception usually
            else:
                self.plugin_session.state = 'FAILED'  # ??? Can this happen if the plugin service catches all?

class PluginSession:

    """
    This class represents one running plugin or its session. It handles the plugin state,
    collecting from the plugin, etc.
    """

    def __init__(self, plugin_name, plugin_class, configuration, debug = False):
        self.plugin_name = plugin_name
        self.plugin_class = plugin_class
        self.configuration = configuration
        self.debug = debug
        self.id = str(uuid.uuid4())
        self.state = 'CREATED'
        self.started = int(time.time())
        self.duration = None
        self.results = []
        self.errors = []
        self.progress = None
        self.files = []
        
    def start(self):
        logging.debug("PluginSession %s %s start()" % (self.id, self.plugin_name))
        protocol = PluginRunnerProcessProtocol(self)
        arguments = ["minion-plugin-runner"]
        if self.debug:
            arguments += ["-d"]
        arguments += ["-p", self.plugin_name]
        environment = { 'MINION_PLUGIN_SERVICE_API': 'http://127.0.0.1:8181', 'MINION_PLUGIN_SESSION_ID': self.id, 'PATH': os.getenv('PATH') }
        self.process = reactor.spawnProcess(protocol, "minion-plugin-runner", arguments, environment)
        self.state = 'STARTED'

    def stop(self):
        logging.debug("PluginSession %s %s stop()" % (self.id, self.plugin_name))

    def terminate(self):
        logging.debug("PluginSession %s %s terminate()" % (self.id, self.plugin_name))

    def add_results(self, results):
        # Add a timestamp to the results. This is not super accurate but that is ok, it is
        # just to get them incrementally later from the task engine api.
        for result in results:
            date = datetime.datetime.utcnow()
            result['Date'] = date.isoformat() + 'Z'
        for result in results:
            result['Id'] = str(uuid.uuid4())
        self.results += results

    def summary(self):
        return { 'id': self.id,
                 'state': self.state,
                 'configuration': self.configuration,
                 'plugin': { 'name': self.plugin_class.name(),
                             'version': self.plugin_class.version(),
                             'class': self.plugin_class.__module__ + "." + self.plugin_class.__name__ },
                 'progress': self.progress,
                 'started': self.started,
                 'issues': [],
                 'files' : self.files,
                 'duration': self.duration if self.duration else int(time.time()) - self.started }


# TODO Move to Plugin class
def _plugin_descriptor(plugin):
    return {'class': plugin.__module__ + "." + plugin.__name__,
            'name': plugin.name(),
            'version': plugin.version()}

class PluginService:
    
    def __init__(self):
        self.sessions = {}
        self.plugins = {}

    def get_session(self, session_id):
        return self.sessions.get(session_id)

    def create_session(self, plugin_name, configuration, debug):
        plugin_class = self.plugins.get(plugin_name)
        if plugin_class:
            session = PluginSession(plugin_name, plugin_class, configuration, debug)
            self.sessions[session.id] = session
            return session

    def register_plugin(self, plugin_class):
        self.plugins[str(plugin_class)] = plugin_class

    def get_plugin_descriptor(self, plugin_name):
        if plugin_name in self.plugins:
            return _plugin_descriptor(self.plugins[plugin_name])

    def plugin_descriptors(self):
        return map(_plugin_descriptor, self.plugins.values())

