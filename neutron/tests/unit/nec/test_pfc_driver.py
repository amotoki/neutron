# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 NEC Corporation.  All rights reserved.
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
# @author: Ryota MIBU

import random
import string

import mock

from neutron import context
from neutron.openstack.common import uuidutils
from neutron.plugins.nec.common import ofc_client as ofc
from neutron.plugins.nec.db import api as ndb
from neutron.plugins.nec.db import models as nmodels
from neutron.plugins.nec import drivers
from neutron.tests import base


class TestConfig(object):
    """Configuration for this test."""
    host = '127.0.0.1'
    port = 8888
    use_ssl = False
    key_file = None
    cert_file = None


def _ofc(id):
    """OFC ID converter."""
    return "ofc-%s" % id


class PFCDriverTestBase(base.BaseTestCase):

    driver = 'neutron.plugins.nec.drivers.pfc.PFCDriverBase'

    def setUp(self):
        super(PFCDriverTestBase, self).setUp()
        self.driver = drivers.get_driver(self.driver)(TestConfig)
        self.do_req = mock.patch.object(ofc.OFCClient, 'do_request').start()
        self.addCleanup(mock.patch.stopall)

    def get_ofc_item_random_params(self):
        """create random parameters for ofc_item test."""
        tenant_id = uuidutils.generate_uuid()
        network_id = uuidutils.generate_uuid()
        port_id = uuidutils.generate_uuid()
        portinfo = nmodels.PortInfo(id=port_id, datapath_id="0x123456789",
                                    port_no=1234, vlan_id=321,
                                    mac="11:22:33:44:55:66")
        return tenant_id, network_id, portinfo

    def _generate_ofc_tenant_id(self, tenant_id):
        fields = tenant_id.split('-')
        # Strip 1st character (UUID version) of 3rd field
        fields[2] = fields[2][1:]
        return ''.join(fields)

    def get_ofc_description(self, desc):
        """OFC description consists of [A-Za-z0-9_]."""
        return desc.replace('-', '_').replace(' ', '_')

    def _create_tenant(self, t, ofc_t, post_id=False, post_desc=False):
        tenant_path = '/tenants/%s' % ofc_t
        path = "/tenants"
        description = "desc of %s" % t
        body = {}
        if post_desc:
            ofc_description = self.get_ofc_description(description)
            body['description'] = ofc_description
        if post_id:
            body['id'] = ofc_t
            self.do_req.return_value = None
        else:
            self.do_req.return_value = {'id': ofc_t}

        ret = self.driver.create_tenant(description, t)
        self.assertEqual(ret, tenant_path)
        self.do_req.assert_called_once_with("POST", path, body=body)

    def testa_create_tenant(self):
        t, n, p = self.get_ofc_item_random_params()
        ofc_t = self._generate_ofc_tenant_id(t)
        self._create_tenant(t, ofc_t, post_id=True)

    def testc_delete_tenant(self):
        t, n, p = self.get_ofc_item_random_params()

        path = "/tenants/%s" % _ofc(t)

        self.driver.delete_tenant(path)
        self.do_req.assert_called_once_with("DELETE", path)
        self.assertTrue(self.do_req.call_count, 1)

    def testd_create_network(self):
        t, n, p = self.get_ofc_item_random_params()
        description = "desc of %s" % n
        ofc_description = self.get_ofc_description(description)

        tenant_path = "/tenants/%s" % _ofc(t)
        post_path = "%s/networks" % tenant_path
        body = {'description': ofc_description}
        network = {'id': _ofc(n)}
        self.do_req.return_value = network

        ret = self.driver.create_network(tenant_path, description, n)
        net_path = "/tenants/%s/networks/%s" % (_ofc(t), _ofc(n))
        self.assertEqual(ret, net_path)
        self.do_req.assert_called_once_with("POST", post_path, body=body)

    def testf_delete_network(self):
        t, n, p = self.get_ofc_item_random_params()

        net_path = "/tenants/%s/networks/%s" % (_ofc(t), _ofc(n))

        self.driver.delete_network(net_path)
        self.do_req.assert_called_once_with("DELETE", net_path)

    def testg_create_port(self):
        t, n, p = self.get_ofc_item_random_params()

        net_path = "/tenants/%s/networks/%s" % (_ofc(t), _ofc(n))
        post_path = "%s/ports" % net_path
        port_path = "/tenants/%s/networks/%s/ports/%s" % (_ofc(t), _ofc(n),
                                                          _ofc(p.id))
        body = {'datapath_id': p.datapath_id,
                'port': str(p.port_no),
                'vid': str(p.vlan_id)}
        port = {'id': _ofc(p.id)}
        self.do_req.return_value = port

        ret = self.driver.create_port(net_path, p, p.id)
        self.assertEqual(ret, port_path)
        self.do_req.assert_called_once_with("POST", post_path, body=body)

    def testh_delete_port(self):
        t, n, p = self.get_ofc_item_random_params()
        port_path = "/tenants/%s/networks/%s/ports/%s" % (_ofc(t), _ofc(n),
                                                          _ofc(p.id))
        self.driver.delete_port(port_path)
        self.do_req.assert_called_once_with("DELETE", port_path)

    def test_filter_supported(self):
        self.assertFalse(self.driver.filter_supported())


class PFCDriverBaseTest(PFCDriverTestBase):
    pass


class PFCV3DriverTest(PFCDriverTestBase):
    driver = 'pfc_v3'

    def testa_create_tenant(self):
        t, n, p = self.get_ofc_item_random_params()
        ret = self.driver.create_tenant('dummy_desc', t)
        ofc_t_path = "/tenants/" + self._generate_ofc_tenant_id(t)
        self.assertEqual(ofc_t_path, ret)
        self.assertFalse(self.do_req.call_count)

    def testc_delete_tenant(self):
        t, n, p = self.get_ofc_item_random_params()
        path = "/tenants/%s" % _ofc(t)
        self.driver.delete_tenant(path)
        # There is no API call.
        self.assertFalse(self.do_req.call_count)


class PFCV4DriverTest(PFCDriverTestBase):
    driver = 'pfc_v4'


class PFCDriverStringTest(base.BaseTestCase):

    driver = 'neutron.plugins.nec.drivers.pfc.PFCDriverBase'

    def setUp(self):
        super(PFCDriverStringTest, self).setUp()
        self.driver = drivers.get_driver(self.driver)(TestConfig)

    def test_generate_pfc_id_uuid(self):
        id_str = uuidutils.generate_uuid()
        exp_str = (id_str[:14] + id_str[15:]).replace('-', '')[:31]

        ret_str = self.driver._generate_pfc_id(id_str)
        self.assertEqual(exp_str, ret_str)

    def test_generate_pfc_id_uuid_no_hyphen(self):
        # Keystone tenant_id style uuid
        id_str = uuidutils.generate_uuid()
        id_no_hyphen = id_str.replace('-', '')
        exp_str = (id_str[:14] + id_str[15:]).replace('-', '')[:31]

        ret_str = self.driver._generate_pfc_id(id_no_hyphen)
        self.assertEqual(exp_str, ret_str)

    def test_generate_pfc_id_string(self):
        id_str = uuidutils.generate_uuid() + 'x'
        exp_str = id_str[:31].replace('-', '_')

        ret_str = self.driver._generate_pfc_id(id_str)
        self.assertEqual(exp_str, ret_str)

    def test_generate_pfc_desc(self):
        random_list = [random.choice(string.printable) for x in range(128)]
        random_str = ''.join(random_list)

        accept_letters = string.letters + string.digits
        exp_list = [x if x in accept_letters else '_' for x in random_list]
        exp_str = ''.join(exp_list)[:127]

        ret_str = self.driver._generate_pfc_description(random_str)
        self.assertEqual(exp_str, ret_str)


class PFCIdConvertTest(base.BaseTestCase):
    driver = 'neutron.plugins.nec.drivers.pfc.PFCDriverBase'

    def setUp(self):
        super(PFCIdConvertTest, self).setUp()
        self.driver = drivers.get_driver(self.driver)(TestConfig)
        self.ctx = mock.Mock()
        self.ctx.session = "session"
        self.ndb_lookup = mock.patch.object(ndb,
                                            'get_ofc_id_lookup_both').start()
        self.addCleanup(mock.patch.stopall)

    def generate_random_ids(self, count=1):
        if count == 1:
            return uuidutils.generate_uuid()
        else:
            return [uuidutils.generate_uuid() for _ in xrange(count)]

    def test_convert_tenant_id(self):
        ofc_t_id = self.generate_random_ids(1)
        print ofc_t_id
        ret = self.driver.convert_ofc_tenant_id(self.ctx, ofc_t_id)
        self.assertEqual(ret, '/tenants/%s' % ofc_t_id)

    def test_convert_tenant_id_noconv(self):
        ofc_t_id = '/tenants/%s' % self.generate_random_ids(1)
        ret = self.driver.convert_ofc_tenant_id(self.ctx, ofc_t_id)
        self.assertEqual(ret, ofc_t_id)

    def test_convert_network_id(self):
        t_id, ofc_t_id, ofc_n_id = self.generate_random_ids(3)
        self.ndb_lookup.return_value = ofc_t_id

        ret = self.driver.convert_ofc_network_id(self.ctx, ofc_n_id, t_id)
        self.assertEqual(ret, ('/tenants/%(tenant)s/networks/%(network)s' %
                               {'tenant': ofc_t_id, 'network': ofc_n_id}))
        self.ndb_lookup.assert_called_once_with(
            self.ctx.session, 'ofc_tenant', t_id)

    def test_convert_network_id_with_new_tenant_id(self):
        t_id, ofc_t_id, ofc_n_id = self.generate_random_ids(3)
        ofc_t_path = '/tenants/%s' % ofc_t_id
        self.ndb_lookup.return_value = ofc_t_path

        ret = self.driver.convert_ofc_network_id(self.ctx, ofc_n_id, t_id)
        self.assertEqual(ret, ('/tenants/%(tenant)s/networks/%(network)s' %
                               {'tenant': ofc_t_id, 'network': ofc_n_id}))
        self.ndb_lookup.assert_called_once_with(
            self.ctx.session, 'ofc_tenant', t_id)

    def test_convert_network_id_noconv(self):
        t_id = 'dummy'
        ofc_t_id, ofc_n_id = self.generate_random_ids(2)
        ofc_n_id = ('/tenants/%(tenant)s/networks/%(network)s' %
                    {'tenant': ofc_t_id, 'network': ofc_n_id})
        ret = self.driver.convert_ofc_network_id(self.ctx, ofc_n_id, t_id)
        self.assertEqual(ret, ofc_n_id)

    def test_convert_port_id(self):
        t_id, n_id = self.generate_random_ids(2)
        ofc_t_id, ofc_n_id, ofc_p_id = self.generate_random_ids(3)

        self.ndb_lookup.side_effect = [ofc_n_id, ofc_t_id]

        ret = self.driver.convert_ofc_port_id(self.ctx, ofc_p_id, t_id, n_id)
        exp = ('/tenants/%(tenant)s/networks/%(network)s/ports/%(port)s' %
               {'tenant': ofc_t_id, 'network': ofc_n_id, 'port': ofc_p_id})
        self.assertEqual(ret, exp)
        self.ndb_lookup.assert_has_calls([
            mock.call(self.ctx.session, 'ofc_network', n_id),
            mock.call(self.ctx.session, 'ofc_tenant', t_id),
        ])

    def test_convert_port_id_with_new_tenant_id(self):
        t_id, n_id = self.generate_random_ids(2)
        ofc_t_id, ofc_n_id, ofc_p_id = self.generate_random_ids(3)

        ofc_t_path = '/tenants/%s' % ofc_t_id
        self.ndb_lookup.side_effect = [ofc_n_id, ofc_t_path]

        ret = self.driver.convert_ofc_port_id(self.ctx, ofc_p_id, t_id, n_id)
        exp = ('/tenants/%(tenant)s/networks/%(network)s/ports/%(port)s' %
               {'tenant': ofc_t_id, 'network': ofc_n_id, 'port': ofc_p_id})
        self.assertEqual(ret, exp)
        self.ndb_lookup.assert_has_calls([
            mock.call(self.ctx.session, 'ofc_network', n_id),
            mock.call(self.ctx.session, 'ofc_tenant', t_id),
        ])

    def test_convert_port_id_with_new_network_id(self):
        t_id, n_id = self.generate_random_ids(2)
        ofc_t_id, ofc_n_id, ofc_p_id = self.generate_random_ids(3)

        ofc_n_path = ('/tenants/%(tenant)s/networks/%(network)s' %
                      {'tenant': ofc_t_id, 'network': ofc_n_id})
        self.ndb_lookup.return_value = ofc_n_path

        ret = self.driver.convert_ofc_port_id(self.ctx, ofc_p_id, t_id, n_id)
        exp = ('/tenants/%(tenant)s/networks/%(network)s/ports/%(port)s' %
               {'tenant': ofc_t_id, 'network': ofc_n_id, 'port': ofc_p_id})
        self.assertEqual(ret, exp)
        self.ndb_lookup.assert_called_once_with(
                self.ctx.session, 'ofc_network', n_id)

    def test_convert_port_id_noconv(self):
        t_id = n_id = 'dummy'
        ofc_t_id, ofc_n_id, ofc_p_id = self.generate_random_ids(3)
        ofc_p_id = ('/tenants/%(tenant)s/networs/%(network)s/ports/%(port)s'
                    % {'tenant': ofc_t_id, 'network': ofc_n_id,
                       'port': ofc_p_id})
        ret = self.driver.convert_ofc_port_id(self.ctx, ofc_p_id, t_id, n_id)
        self.assertEqual(ret, ofc_p_id)
