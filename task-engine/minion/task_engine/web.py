# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import base64
import json
import os
import sys

import cyclone.web
from twisted.internet.defer import inlineCallbacks

from minion.task_engine.engine import TaskEngine, SCAN_DATABASE_CLASSES


TASK_ENGINE_SYSTEM_SETTINGS_PATH = "/etc/minion/task-engine.conf"
TASK_ENGINE_USER_SETTINGS_PATH = "~/.minion/task-engine.conf"


class PlansHandler(cyclone.web.RequestHandler):

    @inlineCallbacks
    def get(self):
        task_engine = self.application.task_engine
        plan_descriptions = yield task_engine.get_plan_descriptions()
        self.finish({'success': True, 'plans': plan_descriptions})


class PlanHandler(cyclone.web.RequestHandler):

    @inlineCallbacks
    def get(self, plan_name):
        task_engine = self.application.task_engine
        plan = yield task_engine.get_plan(plan_name)
        if plan is None:
            self.finish({'success': False, 'error': 'no-such-plan'})
        else:
            self.finish({'success': True, 'plan': plan})


class CreateScanHandler(cyclone.web.RequestHandler):

    @inlineCallbacks
    def put(self, plan_name):

        task_engine = self.application.task_engine
        
        plan = yield task_engine.get_plan(plan_name)
        if plan is None:
            self.finish({'success': False, 'error': 'no-such-plan'})
            return

        configuration = json.loads(self.request.body)
        session = yield task_engine.create_session(plan, configuration)

        self.finish({ 'success': True, 'scan': session.summary() })


class ChangeScanStateHandler(cyclone.web.RequestHandler):
    
    @inlineCallbacks
    def post(self, scan_id):

        task_engine = self.application.task_engine

        state = self.request.body
        if state not in ('START', 'STOP'):
            self.finish({'success': False, 'error': 'unknown-state'})
            return

        session = yield task_engine.get_session(scan_id)
        if session is None:
            self.finish({'success': False, 'error': 'no-such-scan'})
            return
        
        if state == 'START':
            success = yield session.start()
            if not success:
                self.finish({'success': False, 'error': 'invalid-state-transition'})
                return
        elif state == 'STOP':
            success = yield session.stop()
            if not success:
                self.finish({'success': False, 'error': 'invalid-state-transition'})
                return

        self.finish({'success': True})
        
class ScanHandler(cyclone.web.RequestHandler):

    @inlineCallbacks
    def get(self, scan_id):

        task_engine = self.application.task_engine

        # Try to load this from the database. If it is not there then the scan
        # might be still in progress in which case the task engine has it.

        scan = yield self.application.scan_database.load(scan_id)
        if scan is not None:
            self.finish({ 'success': True, 'scan': scan })
            return

        session = yield task_engine.get_session(scan_id)
        if session is None:
            self.finish({'success': False, 'error': 'no-such-scan'})
            return

        self.finish({ 'success': True, 'scan': session.summary() })

class ScanResultsHandler(cyclone.web.RequestHandler):

    def _parse_token(self, token):
        return int(base64.b64decode(token))
    
    def _all_sessions_done(self, sessions):
        for session in sessions:
            if session['state'] in ('CREATED', 'STARTED'):
                return False
        return True

    def _generate_token(self, since, sessions):
        if len(sessions) == 0:
            return base64.b64encode(str(0))
        if not self._all_sessions_done(sessions):
            max_time = since
            for session in sessions:
                issues = []
                for i in session['issues']:
                    if i['_time'] > max_time:
                        max_time = i['_time']
            return base64.b64encode(str(max_time))

    @inlineCallbacks
    def get(self, scan_id):

        task_engine = self.application.task_engine

        session = yield task_engine.get_session(scan_id)
        if session is None:
            self.finish({'success': False, 'error': 'no-such-scan'})
            return

        since = 0
        token = self.get_argument('token', None)
        if token:
            since = self._parse_token(token)
            
        scan_results = session.results(since=since)
        token = self._generate_token(since, scan_results['sessions'])
        self.finish({ 'success': True, 'scan': scan_results, 'token': token })


class TaskEngineApplication(cyclone.web.Application):

    def __init__(self):

        # Configure our settings. We have basic default settings that just work for development
        # and then override those with what is defined in either ~/.minion/ or /etc/minion/

        task_engine_settings = dict(scan_database_type="memory", scan_database_location=None)

        for settings_path in (TASK_ENGINE_USER_SETTINGS_PATH, TASK_ENGINE_SYSTEM_SETTINGS_PATH):
            settings_path = os.path.expanduser(settings_path)
            if os.path.exists(settings_path):
                with open(settings_path) as file:
                    try:
                        task_engine_settings = json.load(file)
                        break
                    except Exception as e:
                        logging.error("Failed to parse configuration file %s: %s" % (settings_path, str(e)))
                        sys.exit(1)

        # Setup the database

        scan_database_type = task_engine_settings['scan_database_type']
        scan_database_class = SCAN_DATABASE_CLASSES.get(scan_database_type)
        if scan_database_class is None:
            logging.error("Unable to configure scan_database_type '%s'. No such type." % scan_database_type)
            sys.exit(1)

        try:
            self.scan_database = scan_database_class(task_engine_settings['scan_database_location'])
        except Exception as e:
            logging.error("Failed to setup the scan database: %s" % str(e))
            sys.exit(1)
        
        # Create the Task Engine

        self.task_engine = TaskEngine(self.scan_database)

        # Setup our routes and initialize the Cyclone application

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
            task_engine=task_engine_settings,
        )

        cyclone.web.Application.__init__(self, handlers, **settings)


Application = lambda: TaskEngineApplication()
