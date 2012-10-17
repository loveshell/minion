# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from setuptools import setup

install_requires = [
    'bottle==0.11.2'
]

setup(name="minion.task_engine",
      version="0.1",
      description="Minion Task Engine",
      url="https://github.com/ygjb/minion",
      author="Mozilla",
      author_email="minion@mozilla.com",
      packages=['minion', 'minion.task_engine'],
      namespace_packages=['minion'],
      include_package_data=True,
      install_requires = install_requires,
      scripts=['scripts/minion-task-engine'])
