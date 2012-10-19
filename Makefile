
VIRTUALENV=virtualenv

.PHONY: all build test clean

all: build

setup:
	$(VIRTUALENV) --no-site-packages .

eggs: setup
	(cd plugin_service; ../bin/python setup.py bdist_egg)
	(cd task_engine; ../bin/python setup.py bdist_egg)

develop: setup
	(cd plugin_service; ../bin/python setup.py develop)
	(cd task_engine; ../bin/python setup.py develop)

test: develop
	(cd plugin_service; ../bin/python setup.py test)
	(cd task_engine; ../bin/python setup.py test)

clean:
	rm -rf bin lib include
	rm -rf plugin_service/dist plugin_service/build plugin_service/*.egg plugin_service/*.egg-info
	rm -rf task_engine/dist task_engine/build task_engine/*.egg task_engine/*.egg-info
