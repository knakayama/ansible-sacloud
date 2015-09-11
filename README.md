ansible-sacloud
===============

# Description

Manage sacloud with Ansible

# Requirements

* [Ansible](https://github.com/ansible/ansible)
* [saklient](https://github.com/sakura-internet/saklient.python)

# Install

Install `saklient` with pip:

```bash
$ pip install saklient
```

then, clone this repository like this:

```bash
$ git clone https://github.com/knakayama/ansible-sacloud path/to/playbook/library
```

finally, set `library` path to your `ansible.cfg`:

```ini
[default]
library=library
```

# Usage

Please see [example playbooks](https://github.com/knakayama/ansible-sacloud/tree/master/examples).

If you don't want to store tokens in plain text, consider using [lookup plugin](http://docs.ansible.com/ansible/playbooks_lookups.html) or [Vault](http://docs.ansible.com/ansible/playbooks_vault.html).

# License

MIT

# Author

[knakayama](https://github.com/knakayama)
