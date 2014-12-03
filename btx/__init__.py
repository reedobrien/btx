"""=
Copyright 2013 Reed O'Brien <reed@reedobrien.com>.
All rights reserved. Use of this source code is governed by a
BSD-style license that can be found in the LICENSE file.


Purpose: Wrap botocore for easier use with serialized configuration files
"""
from __future__ import unicode_literals

import json
import logging
import sys

import botocore.session
from botocore.exceptions import (
        ApiVersionNotFoundError,
        ConfigNotFound
        )

try:
    from yaml import CSafeLoader, CSafeDumper
except ImportError:
    optimized = False
else:
    optimized = True

from yaml import dump as _dump
from yaml import load as _load


def yaml_dump(value):
    if optimized:
        return _dump(value, Dumper=CSafeDumper, default_flow_style=False)
    return _dump(value, default_flow_style=False)


def yaml_load(value):
    if optimized:
        return _load(value, Loader=CSafeLoader)
    return _load(value)


## At some point this was a fine example of IAM config info. It may be out of
## date
examplish_config = """
service: IAM

groups:
  - group_name: "group1"
    policy_name: "allow-rw-to-s3"
    policy_document: "example-allow-rw-to-s3.json"
  - group_name: "group2"
    policy_name: "allow-rw-to-s3"
    policy_document: "example-allow-rw-to-s3.json"
  - group_name: "group3"
    policy_name: "allow-rw-to-s3"
    policy_document: "example-allow-rw-to-s3.json"

users:
  - user_name: "user1"
    groups: [group2, group1]
  - user_name: "user2"
    groups: [group1]
  - user_name: "user3"
    groups: [group3, group2, group1]
  - user_name: "user4"
    groups: [group2, group3]

roles:
  - role_name: "role1-service"
    policy_name: "allow-rw-to-s3"
    assume_role_policy_document: "allow-assume-role-by-ec2-service.json"
    policy_document: "example-allow-rw-to-s3.json"
  - role_name: "role2-service"
    policy_name: "allow-rw-to-s3"
    assume_role_policy_document: "allow-assume-role-by-ec2-service.json"
    policy_document: "example-allow-rw-to-s3.json"
  - role_name: "role3-service"
    policy_name: "allow-rw-to-s3"
    assume_role_policy_document: "allow-assume-role-by-ec2-service.json"
    policy_document: "example-allow-rw-to-s3.json"
"""

allow_assume_role_by_ec2_service = """{
    "Statement":
    [
        {
            "Effect": "Allow",
            "Action": [
                "sts:AssumeRole"
                ],
            "Principal":
            {
                "Service" :
                [
                    "ec2.amazonaws.com"
                ]
            }
        }
    ]
}
"""

example_allow_rw_to_s3 = """{
    "Version":"2012-10-17",
    "Statement":
        [
            {
                "Effect":"Allow",
                "Action":
                [
                "s3:AbortMultipartUpload",
                "s3:DeleteObject",
                "s3:GetObject",
                "s3:GetObjectAcl",
                "s3:ListMultipartUploadParts",
                "s3:PutObject",
                "s3:PutObjectAcl"
                ],
                "Resource":
                    [
                    "arn:aws:s3:::hqmigrat-stage/*"
                    ]
            },
            {
                "Sid":"Stmt1391189122000",
                "Effect":"Allow",
                "Action":
                [
                "s3:AbortMultipartUpload",
                "s3:DeleteObject",
                "s3:GetObject",
                "s3:GetObjectAcl",
                "s3:ListMultipartUploadParts",
                "s3:PutObject",
                "s3:PutObjectAcl"
                ],
                "Resource":
                [
                "arn:aws:s3:::hqmigrat-prod/*"
                ]
            }
        ]
}
"""

class BTX(object):
    """
    BTX is a wrapper for services.
    Parameters

    ```service```
    The AWS services we wish to use, e.g. "s3".

    ```debug``` 
    If the debug flag is set. **Default:** False

    ```logger```
    Your application's logger should you wish to pass it.

    ```region```
    The region to connect to. **Default:** us-east-1
    """
    def __init__(self, service, debug=False, logger=None, region="us-east-1"):
        if logger:
            # TODO: assert it is of type logger
            self.log = logger
        elif debug:
            self.setup_logger(level=logging.DEBUG, service=service)
        else:
            self.setup_logger(service=service)

        assert not (debug and logger)

        self._session = botocore.session.get_session()
        
        try:
            self._service = self._session.get_service(service.lower())
        except ApiVersionNotFoundError as e:
            self.log.critical(
                    "Error loading service '{}' ".format(e))
        ## TODO: does this need try: except?
        self._ep = self._service.get_endpoint(region)
        


    def __call__(self, operation, **kwargs):
        self.log.info("Performing {} with {}".format(operation, kwargs))
        op = self._service.get_operation(operation)
        r, d = op.call(self._ep, **kwargs)
        if not r.ok:
            self.log.error(
                "Error code: {}, reason: {}".format(
                    r.status_code, r.reason))
            self.log.debug("content: {}".format(r.content))
        # let caller decide if it is an "Exception"
        return r, d

    

    def setup_logger(self, level=logging.INFO, service="Exception"):
        log = logging.getLogger("BTX-{}".format(service))
        log.setLevel(level)
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        handler.setFormatter(logging.Formatter(
            "%(asctime)s %(name)s: [%(levelname)s] %(message)s"))
        log.addHandler(handler)
        self.log = log

class Command(BTX):
    """
    BTXCmd is a wrapper for botocore which is suitable for command line scripts.
    
    ```service```
    The AWS services we wish to use, e.g. "s3".

    ```debug``` 
    If the debug flag is set. **Default:** False

    ```logger```
    Your application's logger should you wish to pass it.

    ```region```
    The region to connect to. **Default:** us-east-1
    """
    def __init__(self, config_path,
                 debug=False, dryrun=False, logger=None, region="us-east-1",
                 config_format="yaml"):
        
        assert config_format in ("yaml", "json"
                ), "Unknown configuration format: {}".format(config_format)
        self.config_format = config_format
        self.load_config(config_path)
        assert not (debug and logger), "Set either debug or logger, not both."
        ## Setup the logger here with our config service before
        ## initializing the super class
        if logger:
            self.log= logger
        elif debug:
            super(self).setup_logger(
                level=logging.DEBUG, service=self.config["service"])
        else:
            super(self).setup_logger(service=self.config["service"])
        
        super(self).__init__(debug=debug, logger=logger, region=region)
        self.dryrun = dryrun
        if self.dryrun:
            self.log.critical(
                "dryrun (-n) is set to {}. No action will be taken but "
                "this is what I would do...".format(self.dryrun))
    
    def __call__(self, operation, **kwargs):
        self.log.info("Performing {} with {}".format(operation, kwargs))
        if not self.dryrun:
            op = self._service.get_operation(operation)
            r, d = op.call(self._ep, **kwargs)
            if not r.ok:
                self.log.error(
                    "Error code: {}, reason: {}".format(
                        r.status_code, r.reason))
                self.log.debug("content: {}".format(r.content))
            # let caller decide if it is an "Exception"
            return r, d



    def load_config(self, path):
        with open(path) as f:
            if self.config_format == "yaml":
                self.config = yaml_load(f.read())
            else:
                with open(path) as f:
                    self.config = json.load(f)

    def load_policy(self, path):
        with open(path) as f:
            # load as json
            return json.load(f)

    def policy_string(self, path):
        ## AWS wants a string of JSON
        return json.dumps(self.load_policy(path))

