
VIRTUALENV=virtualenv
INSTALL=env/bin/pip install --quiet

.PHONY: all build test clean

all: build

setup:
	$(VIRTUALENV) env

eggs:
	(cd minion-plugin-service; ../env/bin/python setup.py bdist_egg)
	(cd minion-nmap-plugin; ../env/bin/python setup.py bdist_egg)
	(cd minion-garmr-plugin; ../env/bin/python setup.py bdist_egg)
	(cd minion-task-engine; ../env/bin/python setup.py bdist_egg)

develop:
	(cd minion-plugin-service; ../env/bin/python setup.py develop)
	(cd minion-nmap-plugin; ../env/bin/python setup.py develop)
	(cd minion-garmr-plugin; ../env/bin/python setup.py develop)
	(cd minion-task-engine; ../env/bin/python setup.py develop)

test:
	(cd minion-plugin-service; ../env/bin/python setup.py test)
	(cd minion-nmap-plugin; ../env/bin/python setup.py test)
	(cd minion-garmr-plugin; ../env/bin/python setup.py test)
	(cd minion-task-engine; ../env/bin/python setup.py test)

clean:
	rm -rf env bin lib include
	rm -rf minion-*/*.egg minion-*/*.egg-info minion-*/nosetests.xml minion-*/dist minion-*/build

