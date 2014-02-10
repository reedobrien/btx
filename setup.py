"""
Copyright 2013 Reed O'Brien <reed@reedobrien.com>.
All rights reserved. Use of this source code is governed by a
BSD-style license that can be found in the LICENSE file.
"""

import os

from setuptools import setup
from setuptools import find_packages

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.md')).read()
CHANGES = open(os.path.join(here, 'CHANGES.md')).read()

requires = ["botocore", "pyaml"]
tests_requires = requires + ['nose', 'coverage']

setup(name='btx',
      version='0.1',
      description='A botocore helper class',
      long_description=README + '\n\n' + CHANGES,
      classifiers=[
          "Intended Audience :: Developers",
          "Programming Language :: Python"],
      keywords='AWS botocore',
      author="Reed O'Brien",
      author_email="reed.foss@reedobrien.com",
      url="https://github.com/reedobrien/btx",
      license="BSD-derived. See LICENSE file",
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      tests_require=tests_requires,
      install_requires=requires,
      test_suite="nose.collector",
      entry_points="""\
        #[console_scripts]
        #ascript = btx.scripts.thing:main
      """
      )
