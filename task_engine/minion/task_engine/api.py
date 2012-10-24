'''
Created on 25 Sep 2012

@author: psiinon

Simple wrapper around the TaskEngine providing, yes, a REST API

'''
from minion.task_engine.engine import TaskEngine, TaskEngineError
from minion.plugin_service.service import PluginService
#from bottle import abort, get, put, post, delete, request, run
from bottle import Bottle, abort, request

keys = [ 
        "64c4c469ab0743a368d00466e1eb8608",  
        "ca8601b9a687c34703e46328e3dc69eb" 
        ] 

app = Bottle()
task_engine = TaskEngine()
task_engine.add_plugin_service(PluginService("TestService1"))

def is_authorized(req):
    if len (keys) is 0:
        ''' No keys, no security (developer mode) '''
        return True
    key = req.headers.get('Authorization')
    # XX - timing independent check of key strings is required.
    return (key in keys)

@app.get("/pluginservices")
def get_plugin_services():
    if (not is_authorized(request)):
        abort(401, "Unauthorized request.")
    try:
        return task_engine.get_plugin_services()
    except TaskEngineError as e:
        return { "success" : False, "message" : e}

@app.get("/plugins")
def get_all_plugins():
    if (not is_authorized(request)):
        abort(401, "Unauthorized request.")
    try:
        return task_engine.get_all_plugins()
    except TaskEngineError as e:
        return { "success" : False, "message" : e}

''' Do we want/need remote access to this? '''
@app.put("/pluginservice/create/<ps>")
def add_plugin_service(ps):
    if (not is_authorized(request)):
        abort(401, "Unauthorized request.")
    try:
        return task_engine.add_plugin_service(ps)
    except TaskEngineError as e:
        return { "success" : False, "message" : e}

@app.delete("/pluginservice/<ps>")
def remove_plugin_service(ps):
    if (not is_authorized(request)):
        abort(401, "Unauthorized request.")
    try:
        return task_engine.remove_plugin_service(ps)
    except TaskEngineError as e:
        return { "success" : False, "message" : e}

@app.get("/plugin/<plugin>/<version>/template")
def get_plugin_template(plugin, version):
    if (not is_authorized(request)):
        abort(401, "Unauthorized request.")
    try:
        return task_engine.get_plugin_template(plugin, version)
    except TaskEngineError as e:
        return { "success" : False, "message" : e}

@app.get("/pluginservice/<ps>/info")
def get_plugin_service_info(service_name):
    if (not is_authorized(request)):
        abort(401, "Unauthorized request.")
    try:
        return task_engine.get_plugin_service_info(service_name)
    except TaskEngineError as e:
        return { "success" : False, "message" : e}

@app.put("/plugin/session/create/<plugin>/<version>")
def create_plugin_session(plugin, version):
    if (not is_authorized(request)):
        abort(401, "Unauthorized request.")
    try:
        return task_engine.create_plugin_session(plugin, version)
    except TaskEngineError as e:
        return { "success" : False, "message" : e}

def create_plugin_service_session(service_name, plugin_name):
    if (not is_authorized(request)):
        abort(401, "Unauthorized request.")
    try:
        return task_engine.create_plugin_service_session(service_name, plugin_name)
    except TaskEngineError as e:
        return { "success" : False, "message" : e}

def get_plugin_service_sessions(service_name):
    if (not is_authorized(request)):
        abort(401, "Unauthorized request.")
    try:
        return task_engine.get_plugin_service_sessions(service_name)
    except TaskEngineError as e:
        return { "success" : False, "message" : e}

def terminate_plugin_service_session(service_name, session):
    if (not is_authorized(request)):
        abort(401, "Unauthorized request.")
    try:
        return task_engine.terminate_plugin_service_session(service_name, session)
    except TaskEngineError as e:
        return { "success" : False, "message" : e}

@app.get("/pluginservice/<service_name>/session/<session>/status")
def get_plugin_service_session_status(service_name, session):
    if (not is_authorized(request)):
        abort(401, "Unauthorized request.")
    try:
        return task_engine.get_plugin_service_session_status(service_name, session)
    except TaskEngineError as e:
        return { "success" : False, "message" : e}

@app.get("/pluginservice/<service_name>/session/<session>/states")
def get_plugin_service_session_states(service_name, session):
    if (not is_authorized(request)):
        abort(401, "Unauthorized request.")
    try:
        return task_engine.get_plugin_service_session_states(service_name, session)
    except TaskEngineError as e:
        return { "success" : False, "message" : e}

@app.put("/pluginservice/<service_name>/session/<session>/state/<state>")
def set_plugin_service_session_state(service_name, session, state):
    if (not is_authorized(request)):
        abort(401, "Unauthorized request.")
    try:
        return task_engine.set_plugin_service_session_state(service_name, session, state)
    except TaskEngineError as e:
        return { "success" : False, "message" : e}

# TODO: Dont use this - its not working yet ;)
#@app.put("/pluginservice/<service_name>/session/<session>/config/<config>")
#def set_plugin_service_session_config(service_name, session, config):
@app.post("/pluginservice/<service_name>/session/<session>/config")
def set_plugin_service_session_config(service_name, session):
    if (not is_authorized(request)):
        abort(401, "Unauthorized request.")
    try:
        # TODO hack!
        config = {"target" : "http://localhost"}
        task_engine.set_plugin_service_session_config(service_name, session, config)
        return { "success" : True}
    except TaskEngineError as e:
        return { "success" : False, "message" : e}

@app.get("/pluginservice/<service_name>/session/<session>/config")
def get_plugin_service_session_config(service_name, session):
    if (not is_authorized(request)):
        abort(401, "Unauthorized request.")
    try:
        return task_engine.get_plugin_service_session_config(service_name, session)
    except TaskEngineError as e:
        return { "success" : False, "message" : e}

@app.put("/pluginservice/<service_name>/session/<session>/value")
def set_plugin_service_session_value(service_name, session):
    print 'set_plugin_service_session_value(%s, %s)' % (service_name, session)
    if (not is_authorized(request)):
        abort(401, "Unauthorized request.")
    try:
        key = request.query.key
        value = request.query.value
        task_engine.set_plugin_service_session_value(service_name, session, key, value)
        return { "success" : True}
    except TaskEngineError as e:
        return { "success" : False, "message" : e}

@app.get("/pluginservice/<service_name>/session/<session>/results")
def get_plugin_service_session_results(service_name, session):
    if (not is_authorized(request)):
        abort(401, "Unauthorized request.")
    try:
        return task_engine.get_plugin_service_session_results(service_name, session)
    except TaskEngineError as e:
        return { "success" : False, "message" : e}
