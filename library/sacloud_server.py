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
module: sacloud_server
short_description: Manage sacloud server.
description:
  - Create, update, remove sacloud servers.
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
    default: is1a
    choices: [ 'is1a', is1b', 'tk1a' ]
  server_resource_id:
    description:
      - The resource id for the server
    required: false
    default: false
  cpu:
    description:
      - Server cpu
    required: false
    default: 1
  mem:
    description:
      - Server memory
    required: false
    default: 1
  name:
    description:
      - Server name
    required: false
    default: default
  desc:
    description:
      - Server description
    required: false
    default: false
  icon:
    description:
      - Server icon
    required: false
    default: false
  tags:
    description:
      - Server tags
    required: false
    default: false
  state:
    description:
      - On C(present), it will create if server does not exist.
      - On C(absent) will remove a server if it exists.
      - On C(stopped) will stop a server if it exists.
      - On C(running) check if a server exists and is running.
    required: false
    choices: [ 'present', 'absent', 'stopped', 'running' ]
    default: 'present'
'''

EXAMPLES = '''
# Create a server
- sacloud_server:
    access_token: _YOUR_ACCESS_TOKEN_HERE_
    access_token_secret: _YOUR_ACCESS_TOKEN_SECRET_HERE_
    name: ubuntu14_LTS_64
    zone_id: tk1a
    cpu: 2
    mem: 2
    icon: Ubuntu
    desc: |-
        this
        is
        a
        server
    tags:
      - auto-reboot
      - keyboard-us
    state: present

# Destroy a server
- sacloud_server:
    access_token: _YOUR_ACCESS_TOKEN_HERE_
    access_token_secret: _YOUR_ACCESS_TOKEN_SECRET_HERE_
    server_resource_id: _SERVER_RESOURCE_ID_HERE_
    state: absent
'''

try:
    from saklient.cloud.api import API
    HAS_SAKLIENT = True
except ImportError:
    HAS_SAKLIENT = False


class Server():

    def __init__(self, module, saklient):
        self._module = module
        self._saklient = saklient

    def _get_plan_by_spec(self, cpu, mem):
        try:
            return self._saklient.product.server \
                    .get_by_spec(cpu, mem)
        except Exception, e:
            self._fail(msg='Failed to find plan: %s' % e)

    def _get_tags(self, tags):
        if tags:
            return self._parse_tags(tags)
        else:
            return tags

    def _parse_tags(self, tags):
        return [''.join(['@', x]) for x in tags]

    def _get_desc(self, desc):
        if desc:
            return self._str2triple_quoted_str(desc)
        else:
            return desc

    def _str2triple_quoted_str(self, desc):
        return '''%s''' % desc

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
            self._fail(msg='Failed to find server icon: %s' % e)

    def _get_server(self, server_resource_id):
        try:
            return self._saklient.server.get_by_id(str(server_resource_id))
        except Exception:
            self._fail(msg='Failed to find server: %d' % server_resource_id)

    def destroy(self):
        _server = self._get_server(self._module.params['server_resource_id'])

        try:
            if _server.is_up():
                _server.stop()
                _server.sleep_until_down()
            _server.destroy()
        except Exception, e:
            self._fail(msg='Failed to destroy server: %s' % e)
        self._success(msg='Successfully destroy server: %s' % int(_server.id))

    def stop(self):
        _server = self._get_server(self._module.params['server_resource_id'])

        if _server.is_down():
            self._success(changed=False,
                            msg='The server already stopped: %d'
                            % int(_server.id))

        try:
            _server.stop()
            _server.sleep_until_down()
        except Exception, e:
            self._success(msg='Failed to stop server: %s' % e)

        self._success(msg='Successfully stop server: %d'
                        % int(_server.id))

    def boot(self):
        _server = self._get_server(self._module.params['server_resource_id'])

        if _server.is_up():
            self._success(changed=False,
                            msg='The server already booted: %d'
                            % int(_server.id))

        try:
            _server.boot()
            _server.sleep_until_up()
        except Exception, e:
            self._fail(msg='Failed to boot server: %s' % e)

        self._success(msg='Successfully boot server: %d'
                        % int(_server.id))

    def create(self):
        _server = self._saklient.server.create()
        self._set_params(_server)

        if self._module.check_mode:
            self._success()

        try:
            _server.save()
        except Exception, e:
            self._fail(msg='Failed to create server: %s' % e)
        self._success(result='Successfully add server: %d' % int(_server.id),
                        ansible_facts=dict(sacloud_server_resource_id=_server.id))

    def _set_params(self, _server):
        _server.name = self._module.params['name']
        _server.plan = self._get_plan_by_spec(self._module.params['cpu'],
                                        self._module.params['mem'])

        if self._module.params['desc']:
            _server.description = self._get_desc(self._module.params['desc'])
        if self._module.params['tags']:
            _server.tags = self._get_tags(self._module.params['tags'])
        if self._module.params['icon']:
            _server.icon = self._get_icon(self._module.params['icon'])

    def _fail(self, msg):
        self._module.fail_json(msg=msg)

    def _success(self, changed=True, **kwargs):
        self._module.exit_json(changed=changed, **kwargs)


def main():
    module = AnsibleModule(
        argument_spec=dict(
            access_token=dict(required=True, aliases=['token']),
            access_token_secret=dict(required=True, aliases=['token_secret']),
            zone_id=dict(required=False, default='is1a',
                            choices=['is1a', 'is1b', 'tk1a']),
            server_resource_id=dict(required=False, type='int'),
            cpu=dict(required=False, default='1', type='int'),
            mem=dict(required=False, default='1', type='int'),
            name=dict(required=False, default='default'),
            desc=dict(required=False),
            tags=dict(required=False, type='list'),
            icon=dict(required=False),
            state=dict(required=False, default='present',
                        choices=['present', 'absent', 'stopped', 'running'])
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

    server = Server(module, saklient)

    if module.params['state'] in ['absent', 'stopped', 'running'] \
            and not module.params['server_resource_id']:
        module.fail_json(msg='missing required arguments: server_resource_id')

    if module.params['state'] == 'absent':
        server.destroy()
    elif module.params['state'] == 'stopped':
        server.stop()
    elif module.params['state'] == 'running':
        server.boot()
    else:
        if module.params['server_resource_id']:
            # TODO: implement update
            #server.update()
            module.exit_json(changed=False)
        else:
            server.create()


from ansible.module_utils.basic import *
if __name__ == '__main__':
    main()
