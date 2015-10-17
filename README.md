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

Next, download this repository with `ansible-galaxy`:

```bash
$ ansible-galaxy install knakayama.sacloud -p path/to/role
```

Finally, enable `sacloud.py` in your `role` like this:

```yaml
roles:
  - knakayama.sacloud
```

# Usage

See [example](https://github.com/knakayama/ansible-sacloud/example).

# Author

[knakayama](https://github.com/knakayama)
