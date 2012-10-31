Minion Task Engine
==================

This is a back-end component of Minion that is responsible for running many plugins as part of a test plan.

Also see the following two projects:

 * Minion Plugin Service at https://github.com/st3fan/minion-plugin-service
 * Minion NMAP Plugin at https://github.com/st3fan/minion-nmap-plugin
 * Minion Garmr Plugin at https://github.com/st3fan/minion-garmr-plugin

> Note that this is work in progress. The API and responses are likely to change a bit.

Setting up a development environment
-----------------------------------

Development is best done in a Python Virtualenv. These instructions
assume you have Python 2.7.x and virtualenv installed.

If you are unfamiliar with virtualenv then please read
http://www.virtualenv.org/en/latest/#what-it-does first.

### Set up a virtualenv

    $ cd ~ # (or any directory where you do your development)
    $ virtualenv env
    $ source env/bin/activate

### Check out the project, install it's dependencies and set it up for development

    (env) $ git clone --recursive https://github.com/st3fan/minion-task-engine.git
    (env) $ (cd minion-task-engine/dependencies/klein; python setup.py install)
    (env) $ (cd minion-task-engine; python setup.py develop)

Be sure to use the `--recursive` option as we will also need to clone the git submodules in `dependencies/`.

### Run the Minion Task Engine

Note that you also need to have the Plugin Service running. The Task Engine currently expects the Plugin service to be running on it's default port (8181) on localhost.

    (env) $ minion-task-engine --debug
    12-10-31 13:06:51 I Starting task-engine on 127.0.0.1:8282
    2012-10-31 13:06:51+0000 [-] Log opened.
    2012-10-31 13:06:51+0000 [-] Site starting on 8282
    2012-10-31 13:06:51+0000 [-] Starting factory <twisted.web.server.Site instance at 0x245bdd0>

At this point you have a plugin service running. You can edit the code
and simply Control-C the server and start it again to see your changes
in effect.

Run a scan with the Task Engine
-------------------------------

There are currently two plans defined in the Task Engine. They are called `tickle` and `scratch`. The first does a very minimal scan and the second a more complete one with Garmr and NMAP.

(The plans are currently defined in the minion-task-engine script but will move to some external place.)

To execute a plan, start by sourcing in the virtualenv:

    $ cd ~ # (or any directory where you do your development)
    $ source env/bin/activate

Assuming the task-engine is running in a separate window, you can now execute the client:

    (env) $ minion-task-client http://127.0.0.1:8282 tickle '{"target":"http://www.soze.com"}'
    
This will print out the raw JSON responses of all the calls made to the Task Engine and finally the results of the scan.
