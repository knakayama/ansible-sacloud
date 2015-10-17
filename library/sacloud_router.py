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
module: sacloud_router
short_description: Manage sacloud router.
description:
  - Create, update and remove sacloud routers.
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
    aliases: [ 'token' ]
  access_token_secret:
    description:
      - The sacloud secret access token to use.
    required: true
    default: false
    aliases: [ 'token_secret' ]
  zone_id:
    description:
      - The sacloud zone id to use.
    required: false
    default: 'is1a'
    choices: [ 'is1a', 'is1b', 'tk1a']
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
  resource_id:
    description:
      - The resource id for the router
    required: false
    default: false
  band_width_mbps:
    description:
      - The band widgh mbps for the router
    required: false
    default: 100
    choices: [100, 500, 1000]
  network_mask_len:
    description:
      - The network mask length the router
    required: false
    default: 28
    choices: [26, 27, 28]
  icon:
    description:
      - The router icon
    required: false
    default: false
  state:
    description:
      - On C(present), it will create if router does not exist.
      - On C(absent) will remove a router if it exists.
    required: false
    choices: ['present', 'absent']
    default: 'present'
  connect:
    description:
      - Server resource id to connect to
    required: false
    default: false
'''

EXAMPLES = '''
# Create a router
- sacloud_router:
    access_token: _YOUR_ACCESS_TOKEN_HERE_
    access_token_secret: _YOUR_ACCESS_TOKEN_SECRET_HERE_
    zone_id: tk1a
    name: a test router
    band_width_mbps: 500
    network_mask_len: 26
    icon: DNS
    desc: |-
      this
      is
      a
      router
    tags:
      - auto-reboot
      - boot-network
    state: present

# Destroy a router
- sacloud_router:
    access_token: _YOUR_ACCESS_TOKEN_HERE_
    access_token_secret: _YOUR_ACCESS_TOKEN_SECRET_HERE_
    resource_id: _ROUTER_RESOURCE_ID_HERE_
    state: absent
'''

try:
    from saklient.cloud.api import API
    HAS_SAKLIENT = True
except ImportError:
    HAS_SAKLIENT = False


class Router():

    def __init__(self, module, saklient):
        self._module = module
        self._saklient = saklient

    def get_desc(self, desc):
        if desc:
            return self._str2triple_quoted_str(desc)
        else:
            return desc

    def _str2triple_quoted_str(self, desc):
        return '''%s''' % desc

    # FIXME: don't work
    def get_tags(self, tags):
        if tags:
            return self._parse_tags(tags)
        else:
            return tags

    def _parse_tags(self, tags):
        return [''.join(['@', x]) for x in tags]

    def get_icon(self, icon):
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

    def get_router_by_id(self, resource_id):
        try:
            return self._saklient.router.get_by_id(str(resource_id))
        except Exception:
            self._fail(msg='Failed to find router: %s' % resource_id)

    def destroy(self):
        _router = self.get_router_by_id(self._module.params['resource_id'])

        if self._module.check_mode:
            self._success(changed=True)
        try:
            _router.destroy()
        except Exception, e:
            self._fail(msg='Failed to destroy router: %s' % e)
        self._success(result='Successfully destroy router: %d'
                        % int(_router.id))

    def create(self):
        _router = self._saklient.router.create()
        self._set_params(_router)

        if self._module.check_mode:
            self._success()

        try:
            _router.save()
            _router.sleep_while_creating()
        except Exception, e:
            self._fail(msg='Failed to create router: %s' % e)

        if self._module.params['connect']:
            self._connect(_router, self._module.params['connect'])

        self._success(result='Successfully create router: %s'
                            % _router.id,
                            ansible_facts=self._get_facts(_router))

    def _get_facts(self, _router):
        _swytch = _router.get_swytch()
        default_route = _swytch.dump()['Subnets'][0]['DefaultRoute']
        try:
            ipv4_address = _swytch.collect_unused_ipv4_addresses()[0]
        except Exception, e:
            self._fail(msg='Failed to collect unused ipv4 address: %s' % e)

        return dict(
                sacloud_router_resource_id=_router.id,
                sacloud_default_route=default_route,
                sacloud_ipv4_address=ipv4_address
                )

    # TODO: implement shared segment
    def _connect(self, _router, server_resource_id):
        _iface = self._get_iface_by_id(server_resource_id)

        try:
            return _iface.connect_to_swytch(_router.get_swytch())
        except Exception, e:
            self._fail('Failed to connect to sywitch: %s' % e)

    def _get_iface_by_id(self, server_resource_id):
        try:
            return self._saklient.server.get_by_id(str(server_resource_id)).add_iface()
        except Exception, e:
            self._fail(msg='Failed to find server iface: %s' % e)

    def update(self, resource_id):
        _router = self.get_router_by_id(resource_id)

        if self._module.check_mode:
            self._success(changed=True)

        self._set_params(_router, resource_id)
        try:
            _router.save()
            _router.sleep_while_creating()
        except Exception, e:
            self._fail(msg='Failed to update router: %s' % e)
        self._success(result='Successfully update router: %d'
                        % int(_router.id),
                        ansible_facts=dict(sacloud_router_resource_id=_router.id))

    def _set_params(self, _router, resource_id=None):
        _router.name = self._module.params['name']
        _router.description = self.get_desc(self._module.params['desc'])
        _router.tags = self.get_tags(self._module.params['tags'])
        _router.icon = self.get_icon(self._module.params['icon'])

        if resource_id:
            if self._module.params['network_mask_len']:
                # FIXME: Immutable fields cannot be modified after the resource creation
                #_router.set_network_mask_len(self._module.params['network_mask_len'])
                pass

            if self._module.params['band_width_mbps']:
                try:
                    _router.change_plan(self._module.params['band_width_mbps'])
                except Exception, e:
                    self._fail(msg='Failed to change bandwidth: %s' % e)
        else:
            _router.network_mask_len = self._module.params['network_mask_len']
            _router.band_width_mbps = self._module.params['band_width_mbps']

    def _fail(self, msg):
        self._module.fail_json(msg=msg)

    def _success(self, **kwargs):
        self._module.exit_json(changed=True, **kwargs)


def main():
    module = AnsibleModule(
        argument_spec=dict(
            access_token=dict(required=True, aliases=['token']),
            access_token_secret=dict(required=True, aliases=['token_secret']),
            zone_id=dict(required=False, default='is1a',
                            choices=['is1a', 'is1b', 'tk1a']),
            resource_id=dict(required=False, type='int'),
            name=dict(required=False, default='default'),
            desc=dict(required=False),
            tags=dict(required=False, type='list'),
            icon=dict(required=False),
            band_width_mbps=dict(required=False,
                                       default=100, type='int',
                                       choices=[100, 500, 1000]),
            network_mask_len=dict(required=False,
                                        default=28, type='int',
                                        choices=[26, 27, 28]),
            state=dict(required=False, default='present',
                        choices=['present', 'absent']),
            connect=dict(required=False, type='int')
        ),
        supports_check_mode=True
    )

    if not HAS_SAKLIENT:
        module.fail_json(msg='Required module saklient not found')

    try:
        saklient = API.authorize(module.params['access_token'],
                                module.params['access_token_secret'],
                                module.params['zone_id'])
    except Exception, e:
        module.fail_json(msg='Failed to access sacloud: %s' % e)

    router = Router(module, saklient)

    if module.params['resource_id']:
        if module.params['state'] == 'absent':
            router.destroy()
        elif module.params['state'] == 'present':
            ## TODO: only works with band_width_mbps
            #router.update(module.params['resource_id'])
            module.exit_json(changed=False)
    else:
        # TODO: more convinient way to handle args
        if module.params['state'] == 'absent':
            module.fail_json(msg='missing required arguments: resource_id')
        elif module.params['state'] == 'present':
            router.create()


from ansible.module_utils.basic import *
if __name__ == '__main__':
    main()
