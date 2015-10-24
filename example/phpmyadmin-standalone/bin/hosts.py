#!/usr/bin/env python

import json
import yaml
import os


def main():
    python_interp = os.popen('which python').read().rstrip()
    hosts = yaml.load(file('hosts.yml'))
    hosts.update({'_meta': {'hostvars': {'127.0.0.1': {'ansible_python_interpreter': python_interp}}}})

    print json.dumps(hosts)


if __name__ == '__main__':
    main()
