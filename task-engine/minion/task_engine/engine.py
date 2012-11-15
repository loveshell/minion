# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import copy
import json
import logging
import os
import uuid

import cyclone.web

from twisted.internet import reactor
from twisted.internet.defer import DeferredSemaphore
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.internet.task import deferLater, LoopingCall
from twisted.internet.threads import deferToThread
from twisted.web.client import getPage


PLANS = {}

PLANS['tickle'] = {
    'name': 'tickle',
    'description': 'Run basic tests and do a very basic port scan using NMAP.',
    'workflow': [
        {
            'plugin_name': 'minion.plugins.basic.HSTSPlugin',
            'configuration': {
                # No special configuration needed
            }
        },
        {
            'plugin_name': 'minion.plugins.basic.XFrameOptionsPlugin',
            'configuration': {
                # No special configuration needed
            }
        },
        {
            'plugin_name': 'minion.plugins.nmap.NMAPPlugin',
            'configuration': {
                'ports': "U:53,111,137,T:21-25,139,8080,8443"
            }
        }
    ]
}

PLANS['scratch'] = {
    'name': 'scratch',
    'description': 'Run Garmr and do a full port scan using NMAP.',
    'workflow': [
        {
            'plugin_name': 'minion.plugins.garmr.GarmrPlugin',
            'configuration': {
                # No special configuration needed
            }
        },
        {
            'plugin_name': 'minion.plugins.nmap.NMAPPlugin',
            'configuration': {
                # No special configuration needed
            }
        }
    ]
}

# PLANS['stomp'] = {
#     'name': 'scratch',
#     'description': 'Run Garmr and do a full port scan using NMAP, then run ZAP.',
#     'workflow': [
#         {
#             'plugin_name': 'minion.plugins.garmr.GarmrPlugin',
#             'configuration': {
#                 # No special configuration needed
#             }
#         },
#         {
#             'plugin_name': 'minion.plugins.nmap.NMAPPlugin',
#             'configuration': {
#                 # No special configuration needed
#             }
#         },
#         {
#             'plugin_name': 'minion.plugins.zap_plugin.ZAPPlugin',
#             'configuration': {
#                 # No special configuration needed
#             }
#         }
#     ]
# }

PLANS['zap'] = {
    'name': 'zap',
    'description': 'Run ZAP spider and active scanner.',
    'workflow': [
        {
            'plugin_name': 'minion.plugins.zap_plugin.ZAPPlugin',
            'configuration': {
                # No special configuration needed
            }
        }
    ]
}


PLUGIN_SERVICE_API = "http://localhost:8181"
PLUGIN_SERVICE_POLL_INTERVAL = 1.0


class ScanDatabase:
    def load(self, scan_id):
        pass
    def store(self, scan):
        pass
    def delete(self, scan_id):
        pass

class MemoryScanDatabase(ScanDatabase):

    def __init__(self, path):
        self._scans = {}

    def load(self, scan_id):
        def _main():
            return self._scans.get(scan_id)
        return deferLater(reactor, 0, _main)

    def store(self, scan):
        def _main():
            self._scans[scan['id']] = scan
        return deferLater(reactor, 0, _main)

    def delete(self, scan_id):
        def _main():
            if scan_id in self._scans:
                del self._scans[scan_id]
        return deferLater(reactor, 0, _main)

class FileScanDatabase(ScanDatabase):

    def __init__(self, path):
        self._path = os.path.expanduser(path)
        if not os.path.exists(self._path):
            logging.info("Creating scan database directory %s" % self._path)
            os.mkdir(self._path)

    def load(self, scan_id):
        def _main():
            path = os.path.join(self._path, scan_id)
            if os.path.isfile(path):
                with open(path) as file:
                    return json.load(file)
        return deferToThread(_main)

    def store(self, scan):
        def _main():
            path = os.path.join(self._path, scan['id'])
            with open(path, "w") as file:
                json.dump(scan, file, indent=4)
        return deferToThread(_main)

    def delete(self, scan_id):
        def _main():
            path = os.path.join(self._path, scan_id)
            if os.path.isfile(path):
                os.remove(path)
        return deferToThread(_main)

SCAN_DATABASE_CLASSES = { 'files': FileScanDatabase, 'memory': MemoryScanDatabase }


class TaskEngineSession:

    def __init__(self, plan, configuration, database, plugin_service_api):
        self.plan = plan
        self.configuration = configuration
        self.database = database
        self.plugin_service_api = plugin_service_api
        self.id = str(uuid.uuid4())
        self.state = 'CREATED'
        self.plugin_configurations = []
        self.semaphore = DeferredSemaphore(1)
        self.plugin_sessions = []

    #
    # Return True if all plugins have completed.
    #

    def _all_sessions_are_done(self):
        for session in self.plugin_sessions:
            if session['state'] in ('CREATED', 'STARTED'):
                return False
        return True
    
    #
    # Periodically decide what to do in our workflow. We simply walk
    # over all the plugin sessions part of this scan and see what
    # needs to happen based on their status.
    #

    @inlineCallbacks
    def idle(self):
        logging.debug("TaskEngineSession._periodic_session_task")
        # Loop over all sessions and figure out what to do next for them. We do only one thing
        # at a time to minimize calls down to the plugin service.
        for session in self.plugin_sessions:            
            # Update the session so that we have the most recent info
            if session['state'] not in ('FINISHED', 'ABORTED', 'TERMINATED'):
                url = "%s/session/%s" % (self.plugin_service_api, session['id'])
                response = yield getPage(url.encode('ascii')).addCallback(json.loads)
                session.update(response['session'])
            # Now decide what to do based on the session state
            if session['state'] == 'CREATED':
                # Start this plugin session
                logging.debug("TaskEngineSession._periodic_session_task - Going to start " + session['plugin_name'])
                url = self.plugin_service_api + "/session/%s/state" % session['id']
                result = yield getPage(url.encode('ascii'), method='PUT', postdata='START').addCallback(json.loads)
                break
            elif session['state'] in ('STARTED', 'FINISHED') and session.get('_done') != True:
                # If the status is STARTED or FINISHED then collect the results periodically
                logging.debug("TaskEngineSession._periodic_session_task - Going to get results from " + session['plugin_name'])
                url = self.plugin_service_api + "/session/%s/results" % session['id']
                result = yield getPage(url.encode('ascii')).addCallback(json.loads)
                session['issues'] = result['issues']
                # If the task is finished, and we just grabbed the final results, then mark it as done
                if session['state'] == 'FINISHED':
                    session['_done'] = True                    
                break
        # If we have more work to do then we schedule ourself again.
        if not self._all_sessions_are_done():
            returnValue(False)
        else:
            self.state = 'FINISHED'
            result = yield self.database.store(self.summary())
            returnValue(True)
    
    #
    # Start the scan. We change the status to STARTED and call our periodic
    # poller which will be responsible for starting the plugins in the right
    # order and determining wether are done executing.
    #

    def start(self):
        if self.state != 'CREATED':
            return deferLater(reactor, 0, lambda: False)
        self.state = 'STARTED'
        return deferLater(reactor, 0, lambda: True)

    #
    # Create a new scan.
    #
    
    @inlineCallbacks
    def create(self):
        # Create plugin sessions
        for step in self.plan['workflow']:
            # Create the plugin configuration by overlaying the default configuration with the given configuration
            configuration = step['configuration']
            configuration.update(self.configuration)
            # Create the pligin session
            url = self.plugin_service_api + "/session/create/%s" % step['plugin_name']
            response = yield getPage(url.encode('ascii'), method='PUT', postdata=json.dumps(configuration)).addCallback(json.loads)
            self.plugin_sessions.append(response['session'])
        summary = { 'id': self.id, 'state': self.state, 'plan': self.plan, 'configuration': self.configuration,
                    'sessions': self.plugin_sessions }
        returnValue(summary)

    #
    # Stop the current scan
    # TODO Kill periodic tasks, etc.
    #

    @inlineCallbacks
    def stop(self):
        if self.state not in ('STARTED'):
            returnValue(False)
        self.state = 'STOPPED'
        returnValue(True)

    #
    # Return a summary of the current plugin. Contains its state,
    # plan, configuration and sessions (including results). So it
    # really is not a summary :-/
    #
    
    def summary(self):
        return { 'id': self.id,
                 'state': self.state,
                 'plan': self.plan,
                 'configuration': self.configuration,
                 'sessions': self.plugin_sessions }

    #
    # Return just the results of the scan. Condensed form of summary()
    # that has an optional since parameter that will let you specify
    # incremental results.
    #

    def results(self, since = 0):
        sessions = []
        for session in self.plugin_sessions:
            issues = []
            for i in session['issues']:
                if i['_time'] > since:
                    issues.append(i)
            s = { 'id': session['id'],
                  'plugin_name': session['plugin_name'],
                  'state': session['state'],
                  'progress': session['progress'],
                  'issues': issues }
            sessions.append(s)
        return { 'id': self.id, 'state': self.state, 'sessions': sessions }


class TaskEngine:

    def __init__(self, scans_database, plugin_service_api):
        self._scans_database = scans_database
        self._plugin_service_api = plugin_service_api
        self._sessions = {}
        self._looper = None

    def get_plan_descriptions(self):
        plans = [{'name': plan['name'], 'description': plan['description']} for plan in PLANS.values()]
        return deferLater(reactor, 0, lambda: plans)

    def get_plan(self, plan_name):
        return deferLater(reactor, 0, lambda: PLANS.get(plan_name))

    @inlineCallbacks
    def create_session(self, plan, configuration):
        plan = copy.deepcopy(plan)
        configuration = copy.deepcopy(configuration)
        scan = TaskEngineSession(plan, configuration, self._scans_database, self._plugin_service_api)
        yield scan.create()
        self._sessions[scan.id] = scan

        # If we have not yet started a looping call to idle the sessions, do that now
        if self._looper is None:
            self._looper = LoopingCall(self._idleSessions)
            self._looper.start(2.0)
        
        returnValue(scan)

    def get_session(self, scan_id):
        # If this scan is still running then we grab it from in-memory
        # else we load it from the database.
        session = self._sessions.get(scan_id)
        return deferLater(reactor, 0, lambda: session)
            

    @inlineCallbacks
    def _idleSessions(self):
        for scan_id,session in self._sessions.items():
            logging.debug("Idling session {}".format(scan_id))
            done = yield session.idle()
            # TODO Should this be done by the client instead? By sending a DELETE /scan/<id> ?
            #if done:
            #    logging.debug("TaskEngineSession {} is done, removing it".format(scan_id))
            #    del self._sessions[scan_id]

