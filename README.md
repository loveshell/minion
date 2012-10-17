Minion
=======

Minion is a security testing framework built by Mozilla to brdige the gap between developers and security testers. To do so, it enables developers to scan their projects using a friendly interface.

Full [documentation][docs] is available as well.

[docs]: http://rtfd.org/

Setting up a development environment
------------------------------------

Grab the code. The --recursive option is important because the project has git submodules that need to be recursively checked out.

    $ git clone --recursive https://github.com/st3fan/minion

Create a virtualenv and configure the three modules of minion:

    $ cd minion
    $ virtualenv env
    $ source env/bin/activate

    $ (cd plugin_service; python setup.py develop)
    $ (cd task_engine; python setup.py develop)

    $ cd frontend
    $ cp project/settings/local.py-dist project/settings/local.py
    $ pip install -r requirements/compiled.txt

Minion requires a MySQL database. By default it uses minion as the database, username and password and expects the database to be running on localhost. You can change these settings in projects/settings/local.py.

Minion uses BrowserID, which means you need to configure the IP address or hostname on which you run Minion. This is done with the SITE_URL option in projects/settings/local.py. If you forget to set this, you will not be able to login.

Running Minion in Development Mode
----------------------------------

To run Minion you need to have both the task_engine and the frontend running.

Start the task_engine in a new shell window:

    $ cd minion
    $ source env/bin/activate
    $ minion-task-engine
    Starting Minion Task Engine on localhost:8181
    Bottle v0.11.2 server starting up (using WSGIRefServer())...
    Listening on http://localhost:8181/
    Hit Ctrl-C to quit.

Start the frontend in a new shell window:

    $ cd minion
    $ source env/bin/activate
    $ cd frontend
    $ python manage.py syncdb
    $ python manage.py runserver 127.0.0.0:8000
    Validating models...

    0 errors found
    Django version 1.4.1, using settings 'project.settings'
    Development server is running at http://0.0.0.0:8000/
    Quit the server with CONTROL-C.

License
-------
This software is licensed under the [New BSD License][BSD]. For more
information, read the file ``LICENSE``.

[BSD]: http://creativecommons.org/licenses/BSD/
