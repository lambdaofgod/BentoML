# Copyright 2019 Atalaya Tech, Inc.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

# http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function


import sys
import platform
import json
import logging

import uuid
import requests

from bentoml import config, __version__ as BENTOML_VERSION, _version as version_mod


logger = logging.getLogger(__name__)

AMPLITUDE_URL = "https://api.amplitude.com/httpapi"
PLATFORM = platform.platform()
PY_VERSION = "{major}.{minor}.{micro}".format(
    major=sys.version_info.major,
    minor=sys.version_info.minor,
    micro=sys.version_info.micro,
)
SESSION_ID = str(uuid.uuid4())  # uuid that marks current python session


def is_pypi_release():
    is_installed_package = hasattr(version_mod, 'version_json')
    is_tagged = not BENTOML_VERSION.startswith('0+untagged')
    is_clean = not version_mod.get_versions()['dirty']
    return is_installed_package and is_tagged and is_clean


# Use dev amplitude key
API_KEY = '7f65f2446427226eb86f6adfacbbf47a'
if is_pypi_release():
    # Use prod amplitude key
    API_KEY = '1ad6ee0e81b9666761aebd55955bbd3a'


def get_bento_service_info(bento_service):
    artifact_types = []
    handler_types = []

    for artifact in bento_service.artifacts.items():
        artifact_instance = artifact[1]
        artifact_types.append(artifact_instance.__class__.__name__)

    for api in bento_service.get_service_apis():
        handler_types.append(api.handler.__class__.__name__)

    return {
        "handler_types": handler_types,
        "artifact_types": artifact_types,
        "env": bento_service.env.to_dict(),
    }


def track(event_type, info):
    info['py_version'] = PY_VERSION
    info["bento_version"] = BENTOML_VERSION
    info["platform_info"] = PLATFORM

    return send_amplitude_event(event_type, info)


def track_save(bento_service):
    if config['core'].getboolean("usage_tracking"):
        info = get_bento_service_info(bento_service)
        return track("save", info)


def track_loading(bento_service):
    if config['core'].getboolean("usage_tracking"):
        info = get_bento_service_info(bento_service)
        return track("load", info)


def track_cli(command, deploy_platform=None):
    if config['core'].getboolean("usage_tracking"):
        info = {}
        if deploy_platform is not None:
            info['platform'] = deploy_platform
        return track('cli-' + command, info)


def send_amplitude_event(event, event_properties):
    """Send event to amplitude
    https://developers.amplitude.com/?java#keys-for-the-event-argument
    """
    event_info = [
        {
            "event_type": event,
            "user_id": SESSION_ID,
            "event_properties": event_properties,
        }
    ]
    event_data = {"api_key": API_KEY, "event": json.dumps(event_info)}

    try:
        return requests.post(AMPLITUDE_URL, data=event_data, timeout=1)
    except Exception as err:  # pylint:disable=broad-except
        # silently fail since this error is not important for BentoML user
        logger.info(str(err))
