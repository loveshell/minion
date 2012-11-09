# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

__import__('pkg_resources').declare_namespace(__name__)

import base64
import copy
import json
import logging
import optparse
import os
import sys
import uuid

import cyclone.web

from twisted.internet import reactor
from twisted.internet.defer import Deferred
from twisted.internet.defer import DeferredList
from twisted.internet.defer import DeferredSemaphore
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.internet.task import deferLater
from twisted.internet.threads import deferToThread
from twisted.python import log
from twisted.web.client import Agent
from twisted.web.http_headers import Headers
from twisted.web.iweb import IBodyProducer
from twisted.internet.defer import succeed
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

SCANS = {}

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

    def __init__(self):
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
        self._path = path

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


class Scan:

    def __init__(self, plan, configuration, database):
        self.plan = plan
        self.configuration = configuration
        self.database = database
        self.id = str(uuid.uuid4())
        self.state = 'CREATED'
        self.plugin_configurations = []
        self.semaphore = DeferredSemaphore(1)
        self.plugin_service_api = PLUGIN_SERVICE_API
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
    def _periodic_session_task(self):
        logging.debug("Scan._periodic_session_task")
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
                logging.debug("Scan._periodic_session_task - Going to start " + session['plugin_name'])
                url = self.plugin_service_api + "/session/%s/state" % session['id']
                result = yield getPage(url.encode('ascii'), method='PUT', postdata='START').addCallback(json.loads)
                break
            elif session['state'] in ('STARTED', 'FINISHED') and session.get('_done') != True:
                # If the status is STARTED or FINISHED then collect the results periodically
                logging.debug("Scan._periodic_session_task - Going to get results from " + session['plugin_name'])
                url = self.plugin_service_api + "/session/%s/results" % session['id']
                result = yield getPage(url.encode('ascii')).addCallback(json.loads)
                session['issues'] = result['issues']
                # If the task is finished, and we just grabbed the final results, then mark it as done
                if session['state'] == 'FINISHED':
                    session['_done'] = True                    
                break
        # If we have more work to do then we schedule ourself again.
        if not self._all_sessions_are_done():
            yield deferLater(reactor, PLUGIN_SERVICE_POLL_INTERVAL, self._periodic_session_task)        
        else:
            self.state = 'FINISHED'
            result = yield self.database.store(self.summary())
    
    #
    # Start the scan. We change the status to STARTED and call our periodic
    # poller which will be responsible for starting the plugins in the right
    # order and determining wether are done executing.
    #

    def start(self):
        self.state = 'STARTED'
        reactor.callLater(PLUGIN_SERVICE_POLL_INTERVAL, self._periodic_session_task)

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

    def stop(self):
        self.state = 'STOPPED'

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

class PlansHandler(cyclone.web.RequestHandler):

    def get(self):
        plans = [{'name': plan['name'], 'description': plan['description']} for plan in PLANS.values()]
        self.finish({'success': True, 'plans': plans})

class PlanHandler(cyclone.web.RequestHandler):

    def get(self, plan_name):
        plan = PLANS.get(plan_name)
        if plan is None:
            return {'success': False, 'error': 'no-such-plan'}
        self.finish({'success': True, 'plan': PLANS[plan_name]})

class CreateScanHandler(cyclone.web.RequestHandler):

    @inlineCallbacks
    def put(self, plan_name):

        plan = PLANS.get(plan_name)
        if plan is None:
            self.finish({'success': False, 'error': 'no-such-plan'})
            return

        plan = copy.deepcopy(plan)

        configuration = json.loads(self.request.body)
        scan = Scan(plan, configuration, self.application.database)
        SCANS[scan.id] = scan

        summary = yield scan.create()
        self.finish({ 'success': True, 'scan': summary })

class ChangeScanStateHandler(cyclone.web.RequestHandler):
    
    def post(self, scan_id):

        state = self.request.body
        if state not in ('START', 'STOP'):
            self.finish({'success': False, 'error': 'unknown-state'})
            return

        scan = SCANS.get(scan_id)
        if scan is None:
            self.finish({'success': False, 'error': 'no-such-scan'})
            return
        
        if state == 'START':
            if scan.state != 'CREATED':
                self.finish({'success': False, 'error': 'unknown-state-transition'})
                return
            scan.start()
        elif state == 'STOP':
            if scan.state != 'STARTED':
                self.finish({'success': False, 'error': 'unknown-state-transition'})
                return
            scan.stop()

        self.finish({'success': True})

class ScanHandler(cyclone.web.RequestHandler):

    @inlineCallbacks
    def get(self, scan_id):

        scan = SCANS.get(scan_id)
        if scan is not None:
            self.finish({ 'success': True, 'scan': scan.summary() })
            return

        result = yield self.application.database.load(scan_id)
        if result is None:
            self.finish({'success': False, 'error': 'no-such-scan'})
        else:
            self.finish({ 'success': True, 'scan': result })


class ScanResultsHandler(cyclone.web.RequestHandler):

    def _parse_token(self, token):
        return int(base64.b64decode(token))
    
    def _all_sessions_done(self, sessions):
        for session in sessions:
            if session['state'] in ('CREATED', 'STARTED'):
                return False
        return True

    def _generate_token(self, since, sessions):
        if not self._all_sessions_done(sessions):
            max_time = since
            for session in sessions:
                issues = []
                for i in session['issues']:
                    if i['_time'] > max_time:
                        max_time = i['_time']
            return base64.b64encode(str(max_time))

    def get(self, scan_id):

        scan = SCANS.get(scan_id)
        if scan is None:
            self.finish({'success': False, 'error': 'no-such-scan'})
            return

        since = 0
        token = self.get_argument('token', None)
        if token:
            since = self._parse_token(token)
        results = scan.results(since=since)
        self.finish({ 'success': True,
                      'scan': results,
                      'token': self._generate_token(since, results['sessions']) })


class TaskEngineApplication(cyclone.web.Application):

    def __init__(self, database):

        self.database = database

        handlers = [
            (r"/plans", PlansHandler),
            (r"/plan/(.+)", PlanHandler),
            (r"/scan/create/(.+)", CreateScanHandler),
            (r"/scan/(.+)/state", ChangeScanStateHandler),
            (r"/scan/(.+)/results", ScanResultsHandler),
            (r"/scan/(.+)", ScanHandler),
        ]

        settings = dict(
            debug=True,
            template_path="./template",
            repository_path="./uploaded_files",
        )

        cyclone.web.Application.__init__(self, handlers, **settings)

Application = lambda: TaskEngineApplication(MemoryScanDatabase())
