# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Copyright 2013 NEC Corporation.  All rights reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
# @author: Akihiro MOTOKI

from keystoneclient.v2_0 import client as key_client
from keystoneclient import exceptions as key_exc


class Client(object):

    def __init__(self, conf):
        if conf.auth_uri:
            auth_url = conf.auth_uri
        else:
            auth_url = '%s://%s:%s' % (conf.auth_protocol,
                                       conf.auth_host, conf.auth_port)
        self.client = keystoneclient.Client(username=conf.admin_user,
                                            password=conf.admin_password,
                                            tenant_name=conf.admin_tenant_name,
                                            auth_url=auth_url)

    def get_tenant_name(self, tenant_id):
        try:
            return self.client.tenants.get(tenant_id).name
        except key_exc.ClientException:
            return None
