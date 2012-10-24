'''
Created on 25 Sep 2012

@author: psiinon

Simple wrapper around the TaskEngine providing, yes, a REST API

'''
import logging
import requests
import urllib

key = "64c4c469ab0743a368d00466e1eb8608"

class TaskEngineClient(object):
    
    def __init__(self, url):
        ''' A list of PluginService (local) or PluginServiceClient (remote) - they have the same interface '''
        self.url = url
        self.headers = {'Authorization' : key}
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
        pass
    
    def get_plugin_services(self):
        r = requests.put("%s/pluginservices"%(self.url), data={}, headers=self.headers)
        logging.debug(r.json)
        return r.json

    def get_all_plugins(self):
        r = requests.get("%s/plugins"%(self.url), data={}, headers=self.headers)
        logging.debug(r.json)
        return r.json
    
    def add_plugin_service(self, ps):
        r = requests.put("%s/pluginservice/create/%s"%(self.url, ps), data={}, headers=self.headers)
        logging.debug(r.json)
        return r.json
    
    def remove_plugin_service(self, ps):
        r = requests.delete("%s/pluginservice/%s"%(self.url, ps), data={}, headers=self.headers)
        logging.debug(r.json)
        return r.json
    
    def get_plugin_template(self, plugin, version):
        r = requests.get("%s/plugin/%s/%s/template"%(self.url, plugin, version), data={}, headers=self.headers)
        logging.debug(r.json)
        return r.json
    
    def get_plugin_service_info(self, service_name):
        r = requests.get("%s/pluginservice/%s/info"%(self.url, service_name), data={}, headers=self.headers)
        logging.debug(r.json)
        return r.json
    
    def create_plugin_session(self, plugin, version):
        r = requests.put("%s/plugin/session/create/%s/%s"%(self.url, plugin, version), data={}, headers=self.headers)
        logging.debug(r.json)
        return r.json
    
    '''
    def create_plugin_service_session(service_name, plugin_name):
    
    def get_plugin_service_sessions(service_name):
    
    def terminate_plugin_service_session(service_name, session):
        if (not is_authorized(app.request)):
            app.abort(401, "Unauthorized request.")
        try:
            return task_engine.terminate_plugin_service_session(service_name, session)
        except TaskEngineError as e:
            return { "success" : False, "message" : e}
    '''

    def get_plugin_service_session_status(self, service_name, session):
        r = requests.get("%s/pluginservice/%s/session/%s/status"%(self.url, service_name, session), data={}, headers=self.headers)
        logging.debug(r.json)
        return r.json
    
    def get_plugin_service_session_states(self, service_name, session):
        r = requests.get("%s/pluginservice/%s/session/%s/states"%(self.url, service_name, session), data={}, headers=self.headers)
        logging.debug(r.json)
        return r.json

    def set_plugin_service_session_state(self, service_name, session, state):
        r = requests.put("%s/pluginservice/%s/session/%s/state/%s"%(self.url, service_name, session, state), data={}, headers=self.headers)
        logging.debug(r.json)
        return r.json

    def set_plugin_service_session_config(self, service_name, session, config):
        r = requests.put("%s/pluginservice/%s/session/%s/config/%s"%(self.url, service_name, session, config), data={}, headers=self.headers)
        #r = requests.post("%s/pluginservice/%s/session/%s/config"%(self.url, service_name, session), data={config}, headers=self.headers)
        logging.debug(r.json)
        return r.json
    
    def get_plugin_service_session_config(self, service_name, session):
        r = requests.get("%s/pluginservice/%s/session/%s/config"%(self.url, service_name, session), data={}, headers=self.headers)
        logging.debug(r.json)
        return r.json
    
    def set_plugin_service_session_value(self, service_name, session, key, value):
        #r = requests.put("%s/pluginservice/%s/session/%s/value/%s/%s"%(self.url, service_name, session, key, urllib.quote(value, '')), data={}, headers=self.headers)
        r = requests.put("%s/pluginservice/%s/session/%s/value?key=%s&value=%s"%(self.url, service_name, session, key, urllib.quote(value, '')), data={}, headers=self.headers)
        logging.debug(r.json)
        return r.json

    def get_plugin_service_session_results(self, service_name, session):
        r = requests.get("%s/pluginservice/%s/session/%s/results"%(self.url, service_name, session), data={}, headers=self.headers)
        logging.debug(r.json)
        return r.json
