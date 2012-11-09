
VIRTUALENV=virtualenv
INSTALL=env/bin/pip install --quiet

.PHONY: all build test clean

all: build

setup:
	$(VIRTUALENV) --no-site-packages env
	# These are not in PyPi
	(cd dependencies/klein && ../../env/bin/python setup.py install)
	(cd dependencies/garmr && ../../env/bin/python setup.py install)
	(cd frontend && ../env/bin/pip install -r requirements/compiled.txt)

develop:
	(cd plugin-service; ../env/bin/python setup.py develop)
	(cd task-engine; ../env/bin/python setup.py develop)
	(cd plugins/garmr; ../../env/bin/python setup.py develop)
	(cd plugins/nmap; ../../env/bin/python setup.py develop)
	(cd plugins/zap_plugin; ../../env/bin/python setup.py develop)

test:
	(cd plugin-service; ../env/bin/python setup.py test)
	(cd task-engine; ../env/bin/python setup.py test)
	(cd plugins/garmr; ../../env/bin/python setup.py test)
	(cd plugins/nmap; ../../env/bin/python setup.py test)
	(cd plugins/zap_plugin; ../../env/bin/python setup.py test)

eggs:
	(cd plugin-service; ../env/bin/python setup.py bdist_egg)
	(cd task-engine; ../env/bin/python setup.py bdist_egg)
	(cd plugins/garmr; ../../env/bin/python setup.py bdist_egg)
	(cd plugins/nmap; ../../env/bin/python setup.py bdist_egg)
	(cd plugins/zap_plugin; ../../env/bin/python setup.py bdist_egg)

clean:
	rm -rf env
	rm -rf */*.egg */*.egg-info */nosetests.xml */dist */build

