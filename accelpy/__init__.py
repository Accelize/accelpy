# coding=utf-8
"""Accelpy


Copyright 2019 Accelize

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
__version__ = '1.0.0-beta.10'
__copyright__ = "Copyright 2019 Accelize"
__licence__ = "Apache 2.0"

from sys import version_info as _py
if (_py[0] < 3) or (_py[0] == 3 and _py[1] < 6):
    from sys import version
    raise ImportError(
        'Accelpy require Python 3.6 or more (Currently %s)' % version)
del _py

from accelpy._application import lint
from accelpy._host import Host, iter_hosts

__all__ = ['Host', 'iter_hosts', 'lint', 'exceptions']

# Makes cleaner namespace
for _name in __all__:
    locals()[_name].__module__ = __name__
del _name
