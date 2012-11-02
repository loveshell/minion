import logging
from django.shortcuts import render
import bleach
import commonware
from funfactory.log import log_cef
from mobility.decorators import mobile_template
from session_csrf import anonymous_csrf
from django.core.context_processors import csrf
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt, csrf_protect
import urllib2
from django.conf import settings
from django.utils import simplejson
import json
from django.core import serializers
import time
import requests

#from minion.task_engine.TaskEngineClient import TaskEngineClient

log = commonware.log.getLogger('playdoh')

@mobile_template('scanner/{mobile/}home.html')
def home(request, template=None):
    """Home main view"""
    data = {}  # You'd add data here that you're sending to the template.
    return render(request, template, data)

@mobile_template('scanner/{mobile/}newscan.html')
def newscan(request, template=None):
    #Page has been POSTED to
    if request.method == 'POST':
        url_entered = request.POST["new_scan_url_input"]        #Needs sanitization??
        plan_selected = request.POST["plan_selection"]
        time_started = time.asctime(time.localtime(time.time()))
        
        #Task Engine work
        #Start the scan using provided url to PUT to the API endpoint
        payload = json.dumps({"target": url_entered})
        r = requests.put(settings.TASK_ENGINE_URL + "/scan/create/" + plan_selected, data=payload)
        #Decode the response and extract the ID
        json_r = r.json
        scan_id = json_r['scan']['id']
        
        #Post START to the API endpoint to begin the scan
        starter = requests.post(settings.TASK_ENGINE_URL + "/scan/" + scan_id + "/state", data="START")
        log.debug("STARTER " + str(starter))
        
        data = {"url_entered":url_entered, "plan_selected":plan_selected, "scan_id":scan_id, "time_started":time_started, "task_engine_url":settings.TASK_ENGINE_URL}
        
        log.debug("data " + str(data))

        return render(request, template, data)
    #Page has not been posted to
    else:
        #Retrieve list of plans
        r = requests.get(settings.TASK_ENGINE_URL + '/plans')
        resp_json = r.json
        
        data = {"resp":resp_json['plans'], "task_engine_url":settings.TASK_ENGINE_URL}
        return render(request, template, data)

@csrf_exempt
def xhr_scan_status(request):
    if request.is_ajax():
        message = "x"
        if request.method == 'POST':
            #log.debug("\n\nAJAX_POST_RECEIVED " + str(request.POST))
            scan_id = request.POST["scan_id"]
            scan_status = requests.get(settings.TASK_ENGINE_URL + '/scan/' + scan_id)
            message = scan_status.content
    else:
        message = ""
    return HttpResponse(str(message))

@anonymous_csrf
def bleach_test(request):
    """A view outlining bleach's HTML sanitization."""
    allowed_tags = ('strong', 'em')

    data = {}

    if request.method == 'POST':
        bleachme = request.POST.get('bleachme', None)
        data['bleachme'] = bleachme
        if bleachme:
            data['bleached'] = bleach.clean(bleachme, tags=allowed_tags)

        # CEF logging: Log user input that needed to be "bleached".
        if data['bleached'] != bleachme:
            log_cef('Bleach Alert', logging.INFO, request,
                    username='anonymous', signature='BLEACHED',
                    msg='User data needed to be bleached: %s' % bleachme)

    return render(request, 'scanner/bleach.html', data)
