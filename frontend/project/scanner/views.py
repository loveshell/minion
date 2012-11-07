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
from models import Scan

#from minion.task_engine.TaskEngineClient import TaskEngineClient

log = commonware.log.getLogger('playdoh')

@mobile_template('scanner/{mobile/}home.html')
def home(request, template=None):
    """Home main view"""
    data = {}  # You'd add data here that you're sending to the template.
    return render(request, template, data)

@mobile_template('scanner/{mobile/}newscan.html')
def newscan(request, template=None):
    data = {}
    try:
        r = requests.get(settings.TASK_ENGINE_URL + '/plans')
        resp_json = r.json
    except:
        data = {"error":"Error retrieving available plans. Check connection to task engine."}
        #If you can't retrieve the plans, no use in continuing, return error now.
        return render(request, template, data)
    #Page has been POSTed to
    if request.method == 'POST':
        if request.POST["new_scan_url_input"] and request.POST["plan_selection"] in r.text:
            url_entered = request.POST["new_scan_url_input"]        #Needs sanitization??
            plan_selected = request.POST["plan_selection"]
            time_started = time.asctime(time.localtime(time.time()))
            
            #Task Engine work
            #Start the scan using provided url to PUT to the API endpoint
            payload = json.dumps({"target": url_entered})
            try:
                put = requests.put(settings.TASK_ENGINE_URL + "/scan/create/" + plan_selected, data=payload)
                #Decode the response and extract the ID
                put_resp = put.json
                scan_id = put_resp['scan']['id']
                
                #Post START to the API endpoint to begin the scan
                starter = requests.post(settings.TASK_ENGINE_URL + "/scan/" + scan_id + "/state", data="START")
            except:
                data = {"error":"Error starting session. Check connection to the task engine."}
                #If you can't start a session, no use in continuing, return now
                return render(request, template, data)
            
            try:
                #Retrieve the first set of responses to construct progress bars
                first_results = requests.get(settings.TASK_ENGINE_URL + '/scan/' + scan_id)
                first_results_json = first_results.json
                
                data = {"url_entered":url_entered, "plan_selected":plan_selected, "scan_id":scan_id, "time_started":time_started, "first_results":first_results_json['scan']['sessions'], "task_engine_url":settings.TASK_ENGINE_URL}
                
                log.debug("data " + str(data))
            except:
                data = {"error":"Scan was started, but the initial results could not be retrieved."}
                return render(request, template, data)
    
            #Add the new scan to the database
            newscan1 = Scan(scan_id=scan_id, scan_creator=request.user, scan_date=time_started, scan_url=url_entered, scan_plan=plan_selected)
            newscan1.save()
    
            return render(request, template, data)
        else:
            data = {"error_retry":"Invalid URL or plan. Please enter a valid URL and select a plan.", "resp":resp_json['plans'], "task_engine_url":settings.TASK_ENGINE_URL}
            return render(request, template, data)
    #Page has not been POSTed to
    else:
        data = {"resp":resp_json['plans'], "task_engine_url":settings.TASK_ENGINE_URL}
        return render(request, template, data)
    
@mobile_template('scanner/{mobile/}myscans.html')
def myscans(request, template=None):
    try:
        myscan = Scan.objects.filter(scan_creator=request.user).order_by("scan_date")
        data = {"scans":myscan}
    except:
        data = {"error":"Database could not be reached. Check database connection."}
    return render(request, template, data)

@mobile_template('scanner/{mobile/}plans.html')
def plans(request, template=None):
    try:
        plans = requests.get(settings.TASK_ENGINE_URL + '/plans')
        plans = plans.json
        data = {"plans":plans['plans']}
    except:
        data = {"error":"Error retrieving plans. Check the connection to the task engine."}
    return render(request, template, data)

@mobile_template('scanner/{mobile/}scan.html')
def scan(request, template=None, scan_id="0"):
    #myscan = Scan.objects.filter(scan_creator=request.user).order_by("scan_date")
    data = {"scan_id":scan_id}
    return render(request, template, data)

@csrf_exempt
def xhr_scan_status(request):
    if request.is_ajax():
        message = "Invalid GET Request. Must POST with ID."
        if request.method == 'POST':
            #log.debug("\n\nAJAX_POST_RECEIVED " + str(request.POST))
            scan_id = request.POST["scan_id"]
            scan_token = request.POST["token"]
            if scan_token:
                scan_status = requests.get(settings.TASK_ENGINE_URL + '/scan/' + scan_id + '/results?token=' + scan_token)
            else:
                scan_status = requests.get(settings.TASK_ENGINE_URL + '/scan/' + scan_id + '/results')
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
