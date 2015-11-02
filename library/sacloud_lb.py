#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# (c) 2015, Koji Nakayama <knakayama.sh@gmail.com>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible. If not, see <http://www.gnu.org/licenses/>.

DOCUMENTATION = '''
---
module: sacloud_lb
short_description: Manage sacloud load balancer.
description:
  - Create, update and remove sacloud load balancers.
author:
  - "Koji Nakayama (@knakayama)"
requirements:
  - "python >= 2.6"
  - saklient
options:
  access_token:
    description:
      - The sacloud access token to use.
    required: true
    default: false
    aliases: ['token']
  access_token_secret:
    description:
      - The sacloud secret access token to use.
    required: true
    default: false
    aliases: ['token_secret']
  zone:
    description:
      - The sacloud zone to use.
    required: false
    default: 'is1a'
    choices: ['is1a', 'is1b', 'tk1a']
  name:
    description:
      - The router name
    required: false
    default: false
  desc:
    description:
      - The router description
    required: false
    default: false
  router_resource_id:
    description:
      - The resource id for the router
    required: false
    default: false
  icon:
    description:
      - The router icon
    required: false
    default: false
  vrid:
    description:
      - The VRID
    required: false
    default: false
  real_ips:
    description:
      - ipv4 address range
    required: false
    default: false
  high_spec:
    description:
      - high spec
    required: false
    default: false
  force:
    description:
      - force to stop load balancer
    required: false
    default: false
  virtual_ip:
    description:
      - The virtual ip to use
    required: false
    default: false
  port:
    description:
      - The port to use
    required: false
    default: 80
  delay_loop:
    description:
      - The delay loop to use
    required: false
    default: 10
  lbserver_ips:
    description:
      - The lbserver ips to check
    required: false
    default: false
  lbserver_port:
    description:
      - The lbserver port to check
    required: false
    default: 80
  lbserver_protocol:
    description:
      - The lbserver protocol to check
    required: false
    default: http
    choices: ['http', 'https', 'tcp', 'ping']
  lbserver_path:
    description:
      - The lbserver path to check
    required: false
    default: /index.html
  lbserver_response:
    description:
      - The lbserver response code to expect
    required: false
    default: 200
  state:
    description:
      - On C(present), it will create if load balancer does not exist.
      - On C(absent) will remove a load balancer if it exists.
      - On C(stopped) will stop a load balancer if it exists.
      - On C(running) check if a load balancer exists and is running.
      - On C(applied) apply settings.
    required: false
    choices: ['present', 'absent', 'stopped', 'running', 'applied']
    default: 'present'
'''

EXAMPLES = '''
# Create a load balancer
sacloud_lb:
  access_token: "{{ lookup('env', 'ACCESS_TOKEN') }}"
  access_token_secret: "{{ lookup('env', 'ACCESS_TOKEN_SECRET') }}"
  zone: is1a
  name: a test load balancer
  icon: Wall
  desc: |-
    this
    is
    a
    load balancer
  tags:
    - load balancer
  router_resource_id: _YOUR_ROUTER_RESOURCE_ID_HERE_
  vrid: 1
  real_ips:
    - _YOUR_REAL_IP_HERE_
  high_spec: false
  virtual_ip:
    - _YOUR_VIRTUAL_IP_HERE_
  port: 80
  delay_loop: 10
  lbserver_ips:
    - _YOUR_LBSERVER_IP_HERE_
  lbserver_port: 80
  lbserver_protocol: http
  lbserver_path: /index.html
  lbserver_response: 200
  state: present

# Destroy a load balancer
- sacloud_lb:
    access_token: _YOUR_ACCESS_TOKEN_HERE_
    access_token_secret: _YOUR_ACCESS_TOKEN_SECRET_HERE_
    lb_resource_id: _YOUR_LB_RESOURCE_ID_HERE_
    state: absent
'''

try:
    from saklient.cloud.api import API
    HAS_SAKLIENT = True
except ImportError:
    HAS_SAKLIENT = False


class LoadBalancer():

    def __init__(self, module, saklient):
        self._module = module
        self._saklient = saklient

    def _get_desc(self, desc):
        if desc:
            return self._str2triple_quoted_str(desc)
        else:
            return desc

    def _str2triple_quoted_str(self, desc):
        return '''%s''' % desc

    def _get_tags(self, tags):
        if tags:
            return self._parse_tags(tags)
        else:
            return tags

    def _parse_tags(self, tags):
        return [''.join(['@', x]) for x in tags]

    def _get_icon(self, icon):
        if icon:
            return self._get_icon_with_name_like(icon)
        else:
            return icon

    def _get_icon_with_name_like(self, icon):
        try:
            return self._saklient.icon \
                    .with_name_like(icon) \
                    .limit(1) \
                    .find()[0]
        except Exception, e:
            self._fail(msg='Failed to find router icon: %s' % e)

    def _get_swytch_by_id(self, router_resource_id):
        return self._get_router_by_id(router_resource_id).get_swytch()

    def _get_router_by_id(self, router_resource_id):
        try:
            return self._saklient.router.get_by_id(str(router_resource_id))
        except Exception:
            self._fail(msg='Failed to find router: %s' % router_resource_id)

    def stop(self, lb_resource_id):
        _lb = self._get_lb_by_id(lb_resource_id)

        if _lb.status == 'down':
            self._success(changed=False, result='The load balancer already stopped')
        elif self._module.check_mode:
            self._success()

        try:
            if self._module.params['force']:
                _lb.stop()
            else:
                _lb.shutdown()
            _lb.sleep_until_down()
        except Exception, e:
            self._fail(msg='Failed to stop load balancer: %s' % e)
        self._success(result='Successfully stop load balancer')

    def boot(self, lb_resource_id):
        _lb = self._get_lb_by_id(lb_resource_id)

        if _lb.status == 'up':
            self._success(changed=False, result='The load balancer already running')
        elif self._module.check_mode:
            self._success()
        try:
            _lb.boot()
            _lb.sleep_until_up()
        except Exception, e:
            self._fail(msg='Failed to boot load balancer: %s' % e)
        self._success(result='Successfully boot load balancer')

    def destroy(self, lb_resource_id):
        _lb = self._get_lb_by_id(lb_resource_id)

        if self._module.check_mode:
            self._success()

        try:
            if _lb.status == 'up':
                _lb.stop()
            _lb.destroy()
        except Exception, e:
            self._fail(msg='Failed to destroy load balancer: %s' % e)
        self._success(result='Successfully destroy load balancer: %d'
                        % int(_lb.id))

    def _get_lb_by_id(self, lb_resource_id):
        try:
            return self._saklient.appliance.get_by_id(str(lb_resource_id))
        except Exception, e:
            self._fail(msg='Failed to find load balancer: %s' % e)

    def update(self, lb_resource_id):
        # TODO: implement update
        pass

    def create(self, router_resource_id, vrid, real_ips, high_spec, virtual_ip, lbserver_ips):
        swytch = self._get_swytch_by_id(router_resource_id)

        if self._module.check_mode:
            self._success()

        try:
            _lb = self._saklient.appliance.create_load_balancer(swytch, vrid, real_ips, high_spec)
        except Exception, e:
            self._fail(msg='Failed to create load balancer object: %s' % e)

        self._set_params(_lb, swytch.id, vrid, virtual_ip, lbserver_ips)
        try:
            _lb.save()
            _lb.sleep_while_creating()
        except Exception, e:
            self._fail(msg='Failed to create load balancer: %s' % e)
        self._success(result='Successfully create load balancer: %s' % _lb.id,
                            ansible_facts=dict(sacloud_lb_resource_id=_lb.id))

    def _set_params(self, _lb, swytch_id, vrid, virtual_ip, lbserver_ips):
        _lb.name = self._module.params['name']
        _lb.vrid = vrid

        if self._module.params['desc']:
            _lb.description = self._get_desc(self._module.params['desc'])
        if self._module.params['tags']:
            _lb.tags = self._get_tags(self._module.params['tags'])
        if self._module.params['icon']:
            _lb.icon = self._get_icon(self._module.params['icon'])

        self._add_lbservers(_lb, virtual_ip, lbserver_ips)

    def _add_lbservers(self, _lb, virtual_ip, lbserver_ips):
        vip = self._add_virtual_ip(_lb, virtual_ip)

        for lbserver_ip in lbserver_ips:
            lbserver = vip.add_server()
            lbserver.ip_address = lbserver_ip
            lbserver.port = self._module.params['lbserver_port']
            lbserver.protocol = self._module.params['lbserver_protocol']
            lbserver.path_to_check = self._module.params['lbserver_path']
            lbserver.response_expected = self._module.params['lbserver_response']

    def _add_virtual_ip(self, _lb, virtual_ip):
        vip = _lb.add_virtual_ip()
        vip.virtual_ip_address = virtual_ip
        vip.port = self._module.params['port']
        vip.delay_loop = self._module.params['delay_loop']

        return vip

    def apply(self, lb_resource_id):
        _lb = self._get_lb_by_id(lb_resource_id)

        if self._module.check_mode:
            self._success()

        try:
            _lb.apply()
        except Exception, e:
            self._fail(msg='Failed to apply load balancer: %s' % e)
        self._success(result='Successfully apply load balancer: %d'
                        % int(_lb.id))

    def _fail(self, msg):
        self._module.fail_json(msg=msg)

    def _success(self, changed=True, **kwargs):
        self._module.exit_json(changed=changed, **kwargs)


def main():
    module = AnsibleModule(
        argument_spec=dict(
            access_token=dict(required=True, aliases=['token']),
            access_token_secret=dict(required=True, aliases=['token_secret']),
            zone=dict(required=False, default='is1a',
                            choices=['is1a', 'is1b', 'tk1a']),
            router_resource_id=dict(required=False, type='int'),
            lb_resource_id=dict(required=False, type='int'),
            name=dict(required=False, default='default'),
            desc=dict(required=False),
            tags=dict(required=False, type='list'),
            icon=dict(required=False),
            vrid=dict(required=False, type='int'),
            real_ips=dict(required=False, type='list'),
            high_spec=dict(required=False, default=False, type='bool'),
            force=dict(required=False, default=False, type='bool'),
            virtual_ip=dict(required=False),
            port=dict(required=False, default=80, type='int'),
            delay_loop=dict(required=False, default=10, type='int'),
            lbserver_ips=dict(required=False, type='list'),
            lbserver_port=dict(required=False, default=80, type='int'),
            lbserver_protocol=dict(required=False, default='http',
                                    choices=['http', 'https', 'tcp', 'ping']),
            lbserver_path=dict(required=False, default='/index.html'),
            lbserver_response=dict(required=False, default=200, type='int'),
            state=dict(required=False, default='present',
                        choices=['present', 'absent', 'stopped', 'running', 'applied'])
        ),
        supports_check_mode=True
    )

    if not HAS_SAKLIENT:
        module.fail_json(msg='Required module saklient not found')

    try:
        saklient = API.authorize(module.params['access_token'],
                                module.params['access_token_secret'],
                                module.params['zone'])
    except Exception, e:
        module.fail_json(msg='Failed to access sacloud: %s' % e)

    lb = LoadBalancer(module, saklient)

    if module.params['state'] in ['absent', 'stopped', 'running', 'applied'] \
            and not module.params['lb_resource_id']:
        module.fail_json(msg='missing required arguments: lb_resource_id')

    # TODO: more convinient way to handle args
    if module.params['state'] == 'present':
        if module.params['lb_resource_id']:
            ## TODO: implement update
            #lb.update(module.params['lb_resource_id'])
            module.exit_json(changed=False)
        elif not module.params['router_resource_id']:
            module.fail_json(msg='missing required arguments: router_resource_id')
        elif not module.params['vrid']:
            module.fail_json(msg='missing required arguments: vrid')
        elif not module.params['real_ips']:
            module.fail_json(msg='missing required arguments: real_ips')
        elif not module.params['lbserver_ips']:
            module.fail_json(msg='missing required arguments: lbserver_ips')
        else:
            lb.create(module.params['router_resource_id'],
                        module.params['vrid'],
                        module.params['real_ips'],
                        module.params['high_spec'],
                        module.params['virtual_ip'],
                        module.params['lbserver_ips'])
    elif module.params['state'] == 'absent':
        lb.destroy(module.params['lb_resource_id'])
    elif module.params['state'] == 'stopped':
        lb.stop(module.params['lb_resource_id'])
    elif module.params['state'] == 'running':
        lb.boot(module.params['lb_resource_id'])
    else:
        lb.apply(module.params['lb_resource_id'])


from ansible.module_utils.basic import *
if __name__ == '__main__':
    main()
