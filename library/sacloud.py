#!/usr/bin/python
# -*- coding: utf-8 -*-

DOCUMENTATION = '''
---
module: sacloud
short_description: Create sacloud resources
description:
  - This module allows you to create sacloud resources
author:
  - "Koji Nakayama (@knakayama)"
requirements:
  - "python >= 2.7"
  - saklient
options:
  access_token:
    description:
      - The sacloud access token to use.
    required: true
    default: null
    aliases: ["token"]
  access_token_secret:
    description:
      - The sacloud secret access token to use.
    required: true
    default: null
    aliases: ["secret"]
  zone_id:
    description:
      - The sacloud zone id to use.
    required: false
    default: is1a
    choices: ["is1a", "is1b", "tk1a"]
    aliases: []
  server_resource_id:
    description:
      - The resource id for the server
    required: false
    default: null
    aliases: ["server_id"]
  server_cpu:
    description:
      - Sacloud cpu
    required: false
    default: 1
    aliases: ["cpu"]
  server_mem:
    description:
      - Sacloud memory
    required: false
    default: 1
    aliases: ["mem"]
  server_name:
    description:
      - Sacloud name
    required: false
    default: null
    aliases: []
  server_desc:
    description:
      - Sacloud description
    required: false
    default: null
    aliases: []
  server_icon:
    description:
      - Sacloud icon
    required: false
    default: null
    aliases: []
  server_tags:
    description:
      - Sacloud tags
    required: false
    default: null
    aliases: []
  disk_config_host_name:
    description:
      - disk config hostname
    required: false
    default: localhost
    aliases: []
  disk_config_ssh_key:
    description:
      - The sacloud sshkey to use.
    required: false
    default: null
    aliases: []
  disk_config_password:
    description:
      - The sacloud password to use.
    required: false
    default: null
    aliases: []
  disk_plan:
    description:
      - disk plan
    required: false
    default: ssd
    choices: ["ssd", "hdd"]
    aliases: []
  disk_name:
    description:
      - disk name
    required: false
    default: default
    aliases: []
  disk_size_gib:
    description:
      - disk size (GB)
    required: false
    default: 20
    aliases: []
  disk_desc:
    description:
      - disk description
    required: false
    default: null
    aliases: []
  disk_tags:
    description:
      - disk tags
    required: false
    default: null
    aliases: []
  archive_resource_id:
    description:
      - The archive resource id
    required: false
    default: null
    aliases: ["archive_id"]
  disk_resource_id:
    description:
      - The disk resource id
    required: false
    default: null
    aliases: ["disk_id"]
  state:
    description:
      - On C(present), it will create if server does not exist.
      - On C(absent) will remove a server if it exists.
      - On C(stopped) will stop a server if it exists.
      - On C(running) check if a server exists and is running.
    required: false
    choices: ["present", "absent", "stopped", "running"]
    default: "present"
'''

EXAMPLES = '''
- name: Bootstrap sacloud resource
  connection: local
  sacloud:
    access_token: "{{ lookup('env', 'ACCESS_TOKEN')  }}"
    access_token_secret: "{{ lookup('env', 'ACCESS_TOKEN_SECRET')  }}"
    zone_id: is1a
    archive_resource_id: "{{ lookup('env', 'ARCHIVE_RESOURCE_ID') }}"
    disk_icon: Ubuntu
    disk_plan: ssd
    disk_size: 20
    disk_desc: |-
      this
      is
      a
      disk
    disk_name: test disk
    disk_tags:
      - virtio-net-pci
      - boot-cdrom
    disk_config_host_name: example.com
    disk_config_password: pAssw0rd
    disk_config_ssh_key: "{{ lookup('file', 'id_rsa.pub') }}"
    server_cpu: 1
    server_mem: 1
    server_icon: Ubuntu
    server_desc: |-
      this
      is
      a
      server
    server_name: test server
    server_tags:
      - group=a
      - keyboard-us
    state: present

- name: Destroy a server
  sacloud_server:
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


class Sacloud():

    def __init__(self, module, saklient):
        self._module = module
        self._saklient = saklient

    def get_server_plan_by_spec(self, server_cpu, server_mem):
        try:
            return self._saklient.product.server \
                    .get_by_spec(server_cpu, server_mem)
        except Exception, e:
            self._fail(msg="Failed to find plan: %s" % e)

    def get_tags(self, tags):
        if tags:
            return self._parse_tags(tags)
        else:
            return tags

    def _parse_tags(self, tags):
        return ["".join(["@", x]) for x in tags]

    def get_desc(self, desc):
        if desc:
            return self._str2triple_quoted_str(desc)
        else:
            return desc

    def _str2triple_quoted_str(self, desc):
        return '''%s''' % desc

    def get_icon_with_name_like(self, icon):
        if icon:
            try:
                return self._saklient.icon \
                        .with_name_like(icon) \
                        .limit(1) \
                        .find()[0]
            except Exception, e:
                self._fail(msg="Failed to find icon: %s" % e)
        else:
            return icon

    def destroy(self, server_resource_id, disk_resource_id):
        _server = self._get_server_by_id(server_resource_id)
        _disk = self._get_disk_by_id(disk_resource_id)

        try:
            if self._module.check_mode:
                self._module.exit_json(changed=True, msg="Destroy server")
            else:
                self.destroy_server(_server)
        except Exception, e:
            self._module.exit_json(changed=True, msg="Destroy server")

        try:
            if self._module.check_mode:
                self._module.exit_json(changed=True, msg="Destroy disk")
            else:
                self.destroy_disk(_disk)
        except Exception, e:
            self._module.exit_json(changed=True, msg="Destroy disk" % e)

        self._success(msg="Successfully destroy server/disk: %s/%s"
                        % (_server.id, _disk.id))

    def _get_server_by_id(self, server_resource_id):
        try:
            return self._saklient.server \
                    .get_by_id(str(server_resource_id))
        except Exception:
            # FIXME: UnicodeEncodeError
            self._fail(msg="Failed to find server")

    def _get_disk_by_id(self, disk_resource_id):
        try:
            return self._saklient.disk \
                    .get_by_id(str(disk_resource_id))
        except Exception:
            # FIXME: UnicodeEncodeError
            self._fail(msg="Failed to find disk")

    def stop_server(self, server_resource_id):
        _server = self._get_server_by_id(server_resource_id)

        if _server.is_down():
            self._success(changed=False,
                            msg="The server already stopped: %s"
                            % _server.id)
        try:
            if self._module.check_mode:
                self._module.exit_json(changed=True, msg="Stop server")
            else:
                _server.stop()
                _server.sleep_until_down()
        except Exception, e:
            self._success(msg="Failed to stop server: %s" % e)
        self._success(msg="Successfully stop server: %s" % _server.id)

    def boot_server(self, server_resource_id):
        _server = self._get_server_by_id(server_resource_id)

        if _server.is_up():
            self._success(changed=False,
                            msg="The server already started: %s"
                            % _server_resource_id.id)
        try:
            if self._module.check_mode:
                self._module.exit_json(changed=True, msg="Boot server")
            else:
                _server.boot()
                _server.sleep_until_up()
        except Exception, e:
            self._success(msg="Failed to start server: %s" % e)
        self._success(msg="Successfully start server: %s" % _server.id)

    def get_archive_by_id(self, archive_resource_id):
        try:
            return self._saklient \
                    .archive.get_by_id(str(archive_resource_id))
        except Exception, e:
            self._fail(msg="Failed to find archive: %s" % e)

    def get_default_route(self, ip_address):
        tmp = str(ip_address).split('.')[:-1]
        tmp.append("1")

        return ".".join(tmp)

    def get_disk_plan(self, disk_plan):
        if disk_plan == "ssd":
            return self._saklient.product.disk.ssd
        else:
            # FIXME: hdd plan does not work
            return self._saklient.product.disk.hdd

    def _fail(self, msg):
        self._module.fail_json(msg=msg)

    def _success(self, changed=True, msg=None):
        self._module.exit_json(changed=changed, result=msg)


def main():
    module = AnsibleModule(
        argument_spec=dict(
            access_token=dict(required=True, no_log=True, aliases=["token"]),
            access_token_secret=dict(required=True, no_log=True,
                                        aliases=["secret"]),
            zone_id=dict(required=False, default="is1a",
                            choices=["is1a", "is1b", "tk1a"]),
            disk_plan=dict(required=False, default="ssd",
                                choices=["ssd", "hdd"]),
            archive_resource_id=dict(required=False, type="int",
                                        aliases=["archive_id"]),
            server_cpu=dict(required=False, default="1",
                                type="int", aliases=["cpu"]),
            server_mem=dict(required=False, default="1",
                                type="int", aliases=["mem"]),
            disk_name=dict(required=False, default="default"),
            disk_desc=dict(required=False),
            disk_tags=dict(required=False, type="list"),
            disk_icon=dict(required=False),
            disk_size_gib=dict(required=False, default=20,
                                    type="int", aliases=["disk_size"]),
            disk_config_password=dict(required=False, no_log=True),
            disk_config_host_name=dict(required=False),
            disk_config_ssh_key=dict(required=False, no_log=True),
            server_name=dict(required=False, default="default"),
            server_desc=dict(required=False),
            server_tags=dict(required=False, type="list"),
            server_icon=dict(required=False),
            server_resource_id=dict(required=False, type="int"),
            disk_resource_id=dict(required=False, type="int"),
            state=dict(required=False, default="present",
                        choices=["present", "absent", "stopped", "running"])
        ),
        supports_check_mode=True
    )

    if not HAS_SAKLIENT:
        module.fail_json(msg="Required module saklient not found")

    access_token = module.params["access_token"]
    access_token_secret = module.params["access_token_secret"]
    zone_id = module.params["zone_id"]
    archive_resource_id = module.params["archive_resource_id"]
    server_cpu = module.params["server_cpu"]
    server_mem = module.params["server_mem"]
    disk_name = module.params["disk_name"]
    disk_desc = module.params["disk_desc"]
    disk_tags = module.params["disk_tags"]
    disk_icon = module.params["disk_icon"]
    disk_plan = module.params["disk_plan"]
    disk_size_gib = module.params["disk_size_gib"]
    disk_config_password = module.params["disk_config_password"]
    disk_config_host_name = module.params["disk_config_host_name"]
    disk_config_ssh_key = module.params["disk_config_ssh_key"]
    server_name = module.params["server_name"]
    server_desc = module.params["server_desc"]
    server_tags = module.params["server_tags"]
    server_icon = module.params["server_icon"]
    server_resource_id = module.params["server_resource_id"]
    disk_resource_id = module.params["disk_resource_id"]
    state = module.params["state"]

    saklient = None

    try:
        saklient = API.authorize(access_token, access_token_secret, zone_id)
    except Exception, e:
        module.fail_json(msg="Failed to access sacloud: %s" % e)

    sacloud = Sacloud(module, saklient)

    if state == "absent":
        sacloud.destroy(server_resource_id, disk_resource_id)
    elif state == "stopped":
        sacloud.stop_server(server_resource_id)
    elif state == "running":
        sacloud.boot_server(server_resource_id)

    server = sacloud._saklient.server.create()
    server.name = server_name
    server.plan = sacloud.get_server_plan_by_spec(server_cpu, server_mem)
    server.description = sacloud.get_desc(server_desc)
    server.tags = sacloud.get_tags(server_tags)
    server.icon = sacloud.get_icon_with_name_like(server_icon)

    try:
        if module.check_mode:
            module.exit_json(changed=True, msg="Create server")
        server.save()
    except Exception, e:
        module.fail_json(msg="Failed to create server: %s" % e)

    iface = server.add_iface()
    try:
        iface.connect_to_shared_segment()
    except Exception, e:
        module.fail_json(msg="Failed to connect shared segment: %s" % e)

    disk = sacloud._saklient.disk.create()
    disk.name = disk_name
    disk.description = sacloud.get_desc(disk_desc)
    disk.tags = sacloud.get_tags(disk_tags)
    disk.icon = sacloud.get_icon_with_name_like(disk_icon)
    disk.plan = sacloud.get_disk_plan(disk_plan)
    disk.size_gib = disk_size_gib
    disk.source = sacloud.get_archive_by_id(archive_resource_id)

    try:
        if module.check_mode:
            module.exit_json(changed=True, msg="Create disk")
        disk.save()
        disk.sleep_while_copying()
    except Exception, e:
        module.fail_json(msg="Failed to create disk: %s" % e)

    disk_config = disk.create_config()
    disk_config.ip_address = str(iface.ip_address)
    disk_config.network_mask_len = 24
    disk_config.default_route = sacloud.get_default_route(iface.ip_address)

    if disk_config_host_name:
        disk_config.host_name = disk_config_host_name
    if disk_config_password:
        disk_config.password = disk_config_password
    if disk_config_ssh_key:
        disk_config.ssh_key = disk_config_ssh_key

    try:
        if module.check_mode:
            module.exit_json(changed=True, msg="Modify disk")
        disk_config.write()
    except Exception, e:
        module.fail_json(msg="Failed to modify disk: %s" % e)

    try:
        if module.check_mode:
            module.exit_json(changed=True, msg="Connect disk to server")
        disk.connect_to(server)
    except Exception, e:
        module.fail_json(msg="Failed to connect disk to server: %s" % e)

    try:
        if module.check_mode:
            module.exit_json(changed=True, msg="Boot server")
        server.boot()
        server.sleep_until_up()
    except Exception, e:
        module.fail_json(msg="Failed to boot server: %s" % e)

    module.exit_json(changed=True, result="Successfully added server: %s"
                        % server.name, ansible_facts=dict(sacloud_ip_address=iface.ip_address))

from ansible.module_utils.basic import *
if __name__ == "__main__":
    main()
