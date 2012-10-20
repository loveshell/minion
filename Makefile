
VIRTUALENV=virtualenv
INSTALL=bin/pip install --quiet

.PHONY: all build test clean

all: build

setup:
	$(VIRTUALENV) .
	#$(INSTALL) nosexcover
	#$(INSTALL) pylint

eggs:
	(cd plugin_service; ../bin/python setup.py bdist_egg)
	(cd task_engine; ../bin/python setup.py bdist_egg)

develop:
	(cd plugin_service; ../bin/python setup.py develop)
	(cd task_engine; ../bin/python setup.py develop)

test:
	(cd plugin_service; ../bin/python setup.py test)
	(cd task_engine; ../bin/python setup.py test)
	#(cd plugin_service; ../bin/nosetests --with-xcoverage --with-xunit --cover-package=minion.plugin_service.tests --cover-erase)
	#(cd task_engine; ../bin/nosetests --with-xcoverage --with-xunit --cover-package=minion.task_engine.tests --cover-erase)

clean:
	rm -rf bin lib include
	rm -rf plugin_service/dist plugin_service/build plugin_service/*.egg plugin_service/*.egg-info plugin_service/nosetests.xml
	rm -rf task_engine/dist task_engine/build task_engine/*.egg task_engine/*.egg-info task_engine/nosetests.xml

