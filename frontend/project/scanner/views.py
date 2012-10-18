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

from minion.task_engine.TaskEngineClient import TaskEngineClient

log = commonware.log.getLogger('playdoh')

te = TaskEngineClient("http://localhost:8181")

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
        data = {"url_entered":url_entered}
        
        #Task Engine work
        
        result = te.get_all_plugins()
        data.update(result)
        
        result = te.get_plugin_template("TemplatePlugin", 1)
        data.update(result)
        
        result = te.create_plugin_session("TemplatePlugin", 1)
        data.update(result)
        
        session = result["session"]
        service_name = result["plugin_service"]["name"]
        result = te.set_plugin_service_session_value(service_name, session, "target", "localhost")
        
        
        
        log.debug("data " + str(data))
        log.debug("RESULT " + str(result))

        return render(request, template, data)
    #Page has not been posted to
    else:
        data = {}  # You'd add data here that you're sending to the template.
        return render(request, template, data)

def xhr_scan_status(request):
    if request.is_ajax():
        message = "x"
        if request.method == 'POST':
            #log.debug("\n\nAJAX_POST_RECEIVED " + str(request.POST))
            service_name = request.POST["service_name"]
            session = request.POST["session"]
            message = te.get_plugin_service_session_status(service_name, session)
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
