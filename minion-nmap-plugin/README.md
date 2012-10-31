Minion NMAP Plugin
===================

This is a plugin for Minion that executes the NMAP tool. It assumes NMAP is installed on your system and that is is on the system PATH. If you use Ubuntu, Debian, Redhat or Fedora you can simply install the `nmap` package through `yum` or `apt-get`.

Setting up a Development Environment
====================================

This needs a Python virtualenv setup as described on https://github.com/st3fan/minion-plugin-service/blob/master/README.md

It is important that you use the same virtualenv as you used for the Minion Plugin Service otherwise the plugin will not be found and registered.

### Check out the code

    $ cd ~ # (or any directory where you do your development)
    $ git clone --recursive https://github.com/st3fan/minion-nmap-plugin.git

Be sure to use the `--recursive` option as we will also need to clone the git submodules in `dependencies/`.

### Activate the virtualenv and setup the project for development

    $ cd ~ # (or any directory where you do your development)
    $ source env/bin/activate
    $ cd minion-nmap-plugin
    $ python setup.py develop
    
At this point the plugin has been installed in the virtualenv. It will now be found when you start the `minion-plugin-service`.
