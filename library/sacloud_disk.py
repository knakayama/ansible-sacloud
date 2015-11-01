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
module: sacloud_disk
short_description: Manage sacloud disk.
description:
  - Create, update and remove sacloud disks.
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
  zone_id:
    description:
      - The sacloud zone id to use.
    required: false
    default: is1a
    choices: ['is1a', 'is1b', 'tk1a']
  name:
    description:
      - The disk name
    required: false
    default: default
  desc:
    description:
      - The disk description
    required: false
    default: default
  disk_resource_id:
    description:
      - The resource id for the disk
    required: false
    default: false
    aliases: ['disk_id']
  icon:
    description:
      - The disk icon
    required: false
    default: false
  tags:
    description:
      - The disk tags
    required: false
    default: false
  plan:
    description:
      - The disk plan
    required: false
    default: ssd
    choices: ['ssd', 'hdd']
  size_gib:
    description:
      - disk size (GB)
    required: false
    default: 20
  archive_resource_id:
    description:
      - The resource id for the archive
    required: false
    default: false
    aliases: ['archive_id']
  server_resource_id:
    description:
      - The resource id for the server
    required: false
    default: false
    aliases: ['server_id']
  config_host_name:
    description:
      - The disk hostname
    required: false
    default: default
  config_password:
    description:
      - The disk password
    required: false
    default: false
  config_ipv4_address:
    description:
      - The disk ipv4 address
    required: false
    default: false
  config_ssh_key:
    description:
      - The disk ssh key
    required: false
    default: false
  config_network_mask_len:
    description:
      - The disk network mask length
    required: false
    default: false
  config_default_route:
    description:
      - The disk default route
    required: false
    default: false
  state:
    description:
      - On C(present), it will create if disk does not exist.
      - On C(absent) will remove a disk if it exists.
      - On C(connected) will connect a disk to the server
      - On C(disconnected) will disconnect a disk from the server
    required: false
    choices: ['present', 'absent', 'connected', 'disconnected']
    default: 'present'
'''

EXAMPLES = '''
# Create a disk
- sacloud_disk:
    access_token: _YOUR_ACCESS_TOKEN_HERE_
    access_token_secret: _YOUR_ACCESS_TOKEN_SECRET_HERE_
    archive_resource_id: __ARCHIVE_RESOURCE_ID_HERE_
    zone_id: tk1a
    name: a test disk
    icon: Ubuntu
    plan: ssd
    size_gib: 20
    desc: |-
      this
      is
      a
      disk
    tags:
      - virtio-net-pci
      - boot-cdrom
    config_host_name: example.com
    config_password: _YOUR_PASSWORD_HERE_
    config_ipv4_address: _YOUR_IP_ADDRESS_HERE_
    config_ssh_key: _YOUR_SSH_KEY_HERE_
    config_network_mask_len: 28
    config_default_route: _YOUR_DEFAULT_ROUTE_HERE_
    state: present

# Destroy a disk
- sacloud_disk:
    access_token: _YOUR_ACCESS_TOKEN_HERE_
    access_token_secret: _YOUR_ACCESS_TOKEN_SECRET_HERE_
    disk_resource_id: _DISK_RESOURCE_ID_HERE_
    state: absent
'''

try:
    from saklient.cloud.api import API
    HAS_SAKLIENT = True
except ImportError:
    HAS_SAKLIENT = False


class Disk():

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

    # FIXME: don't work
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
            self._fail(msg='Failed to find disk icon: %s' % e)

    def _get_disk_by_id(self, disk_resource_id):
        try:
            return self._saklient.disk.get_by_id(str(disk_resource_id))
        except Exception:
            self._fail(msg='Failed to find disk: %d' % disk_resource_id)

    def destroy(self, disk_resource_id):
        _disk = self._get_disk_by_id(disk_resource_id)

        if self._module.check_mode:
            self._success()

        try:
            _disk.destroy()
        except Exception, e:
            self._fail(msg='Failed to destroy disk: %s' % e)
        self._success(msg='Successfully destroy disk: %d' % int(_disk.id))

    def _get_plan(self, plan):
        if plan == 'ssd':
            return self._saklient.product.disk.ssd
        else:
            # FIXME: hdd plan does not work
            return self._saklient.product.disk.hdd

    def _get_archive_by_id(self, archive_resource_id):
        try:
            return self._saklient.archive.get_by_id(str(archive_resource_id))
        except Exception:
            self._fail(msg='Failed to find disk source archive: %d'
                        % archive_resource_id)

    def create(self):
        _disk = self._saklient.disk.create()
        self._set_params(_disk)

        if self._module.check_mode:
            self._success()

        try:
            _disk.save()
            _disk.sleep_while_copying()
        except Exception, e:
            self._fail(msg='Failed to create disk: %s' % e)

        if self._config_param_exist():
            self._set_config(_disk)

        self._success(result='Successfully add disk: %d' % int(_disk.id),
                            ansible_facts=dict(sacloud_disk_resource_id=_disk.id))

    def disconnect(self, disk_resource_id):
        _disk = self._get_disk_by_id(disk_resource_id)

        if self._module.check_mode:
            self._success(changed=False)

        try:
            _disk.disconnect()
        except Exception, e:
            self._fail(msg='Failed to disconnect disk from server: %s' % e)
        self._success(result='Successfully disconnect disk')

    def connect(self, disk_resource_id, server_resource_id):
        _server = self._get_server_by_id(server_resource_id)
        _disk = self._get_disk_by_id(disk_resource_id)

        if self._module.check_mode:
            self._success(changed=False)

        try:
            _disk.connect_to(_server)
        except Exception, e:
            self._fail(msg='Failed to connect disk to server: %s' % e)
        self._success(result='Successfully connect to server')

    def _get_server_by_id(self, server_resource_id):
        try:
            return self._saklient.server.get_by_id(str(server_resource_id))
        except Exception:
            # FIXME: UnicodeEncodeError
            #self._fail('Failed to find server: %s' % e)
            self._fail(msg='Failed to find server: %d' % server_resource_id)

    def _set_params(self, _disk):
        _disk.name = self._module.params['name']
        _disk.plan = self._get_plan(self._module.params['plan'])
        _disk.size_gib = self._module.params['size_gib']

        if self._module.params['desc']:
            _disk.description = self._get_desc(self._module.params['desc'])
        if self._module.params['tags']:
            _disk.tags = self._get_tags(self._module.params['tags'])
        if self._module.params['icon']:
            _disk.icon = self._get_icon(self._module.params['icon'])
        if self._module.params['archive_resource_id']:
            _disk.source = self._get_archive_by_id(self._module.params['archive_resource_id'])

    def _config_param_exist(self):
        # FIXME: very ugly
        return ([self._module.params['config_host_name'],
                self._module.params['config_password'],
                self._module.params['config_ipv4_address'],
                self._module.params['config_ssh_key'],
                self._module.params['config_network_mask_len'],
                self._module.params['config_default_route']])

    def _set_config(self, _disk):
        _disk_config = _disk.create_config()

        if self._module.params['config_host_name']:
            _disk_config.host_name = self._module.params['config_host_name']
        if self._module.params['config_password']:
            _disk_config.password = self._module.params['config_password']
        if self._module.params['config_ipv4_address']:
            _disk_config.ip_address = self._module.params['config_ipv4_address']
        if self._module.params['config_ssh_key']:
            _disk_config.ssh_key = self._module.params['config_ssh_key']
        if self._module.params['config_network_mask_len']:
            _disk_config.network_mask_len = \
                    self._module.params['config_network_mask_len']
        if self._module.params['config_default_route']:
            _disk_config.default_route = \
                    self._module.params['config_default_route']

        try:
            _disk_config.write()
        except Exception, e:
            self._fail(msg='Failed to modify disk: %s' % e)

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
            disk_resource_id=dict(required=False, type='int', aliases=['disk_id']),
            name=dict(required=False, default='default'),
            desc=dict(required=False),
            tags=dict(required=False, type='list'),
            icon=dict(required=False),
            size_gib=dict(required=False, default=20,
                                type='int', aliases=['disk_size']),
            archive_resource_id=dict(required=False, type='int',
                                        aliases=['archive_id']),
            server_resource_id=dict(required=False, type='int',
                                        aliases=['server_id']),
            plan=dict(required=False, default='ssd',
                            choices=['ssd', 'hdd']),
            config_host_name=dict(required=False),
            config_password=dict(required=False),
            config_ipv4_address=dict(required=False),
            config_ssh_key=dict(required=False),
            config_network_mask_len=dict(required=False, type='int'),
            config_default_route=dict(required=False),
            state=dict(required=False, default='present',
                        choices=['present', 'absent', 'connected', 'disconnected']),
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

    disk = Disk(module, saklient)

    if module.params['state'] == 'connected':
        if not module.params['disk_resource_id']:
            module.fail_json(msg='missing required arguments: disk_resource_id')
        elif not module.params['server_resource_id']:
            module.fail_json(msg='missing required arguments: server_resource_id')
        else:
            disk.connect(module.params['disk_resource_id'], module.params['server_resource_id'])
    elif module.params['state'] == 'disconnected':
        if module.params['disk_resource_id']:
            disk.disconnect(module.params['disk_resource_id'])
        else:
            module.fail_json(msg='missing required arguments: disk_resource_id')
    elif module.params['state'] == 'absent':
        if module.params['disk_resource_id']:
            disk.destroy(module.params['disk_resource_id'])
        else:
            module.fail_json(msg='missing required arguments: disk_resource_id')
    else:
        if module.params['archive_resource_id']:
            disk.create()
        elif not module.params['disk_resource_id']:
            module.fail_json(msg='missing required arguments: disk_resource_id')
        else:
            # TODO: implement update
            #disk.update(module.params['disk_resource_id'])
            module.exit_json(changed=False)


from ansible.module_utils.basic import *
if __name__ == '__main__':
    main()
