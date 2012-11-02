Minion
=======

Minion is a security testing framework built by Mozilla to brdige the gap between developers and security testers. To do so, it enables developers to scan their projects using a friendly interface.

For more information see https://wiki.mozilla.org/Security/Projects/Minion

Full [documentation][docs] will be available in time.

[docs]: http://rtfd.org/

Setting up a development environment
------------------------------------
Whatever platform you use, you will need the following tools:

    Python
    virtualenv
    git
    mysql

If you work on Ubuntu, install the following packages:

    $ sudo apt-get install git build-essential python-virtualenv python-dev mysql-server libmysqlclient-dev

If you work on Fedora, install the following packages:

    $ sudo yum groupinstall 'Development Tools'
    $ sudo yum install python-devel mysql-devel

Grab the code. The --recursive option is important because the project has git submodules that need to be recursively checked out.

    $ git clone --recursive https://github.com/ygjb/minion

Using the Makefile you can setup the virtualenv and setup the code for development:

    $ cd minion
    $ make setup develop

To setup the frontend you need to copy the template `local.py-dist` to `local.py`:

    $ cp frontend/project/settings/local.py-dist frontend/project/settings/local.py

Minion requires a MySQL database. By default it uses minion as the database, username and password and expects the database to be running on localhost. You can change these settings in projects/settings/local.py.

If you have MySQL running on localhost, you can add a new database and user for Minion as follows:

    mysql -u root
    mysql>CREATE DATABASE minion;
    mysql>CREATE USER 'minion'@'localhost' IDENTIFIED BY 'minion';
    mysql>GRANT ALL PRIVILEGES on minion.* to minion@localhost ;
    mysql>exit;

*DO NOT USE THESE SETTINGS FOR PRODUCTION - WE ENCOURAGE YOU TO HARDEN YOUR MYSQL SETUP AND USE A DIFFICULT TO GUESS USERNAME AND PASSWORD*

Minion uses BrowserID, which means you need to configure the IP address or hostname on which you run Minion. This is done with the SITE_URL option in projects/settings/local.py. If you forget to set this, you will not be able to login.

Running Minion in Development Mode
----------------------------------

To run Minion you need to have three things up and running:

* The Task Engine
* The Plugin Service
* The Frontend

The order is not important, just start them all up in separate terminal windows.

To start the Task Engine:

    $ cd minion
    $ source env/bin/activate
    (env) $ minion-task-engine --debug
    12-10-31 16:06:53 I Starting task-engine on 127.0.0.1:8282
    2012-10-31 16:06:53-0400 [-] Log opened.
    2012-10-31 16:06:53-0400 [-] Site starting on 8282
    2012-10-31 16:06:53-0400 [-] Starting factory <twisted.web.server.Site instance at 0x10d4e0d88>

To start the Plugin Service:

    $ cd minion
    $ source env/bin/activate
    (env) $ minion-plugin-service --debug
    12-10-31 16:08:52 I Starting plugin-service on 127.0.0.1:8181
    12-10-31 16:08:52 I Registered plugin minion.plugins.basic.AbortedPlugin
    12-10-31 16:08:52 I Registered plugin minion.plugins.basic.DummyPlugin
    12-10-31 16:08:52 I Registered plugin minion.plugins.basic.ExceptionPlugin
    12-10-31 16:08:52 I Registered plugin minion.plugins.basic.FailedPlugin
    12-10-31 16:08:52 I Registered plugin minion.plugins.basic.HSTSPlugin
    12-10-31 16:08:52 I Registered plugin minion.plugins.basic.LongRunningPlugin
    12-10-31 16:08:52 I Registered plugin minion.plugins.basic.XFrameOptionsPlugin
    12-10-31 16:08:52 I Registered plugin minion.plugins.garmr.GarmrPlugin
    12-10-31 16:08:52 I Registered plugin minion.plugins.nmap.NMAPPlugin
    2012-10-31 16:08:52-0400 [-] Log opened.
    2012-10-31 16:08:52-0400 [-] Site starting on 8181
    2012-10-31 16:08:52-0400 [-] Starting factory <twisted.web.server.Site instance at 0x11086f6c8>

Start the frontend in a new shell window:

    $ cd minion
    $ source env/bin/activate
    (env) $ cd frontend
    (env) $ python manage.py syncdb
    (env) $ python manage.py runserver 127.0.0.0:8000
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
