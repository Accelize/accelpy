"""Extra Ansible filters"""


def rules_ports(
        firewall_rules, only_restricted=False, redirect=False, *_, **__):
    """
    Return restricted ports (<1024) from firewall rules.

    Args:
        firewall_rules (list of dict): Firewall rules.
        only_restricted (bool): If True, list only ports < 1024.
        redirect (bool): If True, provides a redirect for ports < 1024 in the
            unrestricted port range.

    Returns:
        list of dict: port, redirected port, protocol
    """
    filtered = []
    for rule in firewall_rules:
        start = int(rule['start_port'])
        end = int(rule['end_port'])
        if not only_restricted or start < 1024:
            protocol = rule['protocol']
            filtered += [{
                'port': str(port),
                'redirect': str(port + (
                    60000 if port < 1024 and redirect else 0)),
                'protocol': protocol} for port in range(start, end + 1)]
    return filtered


def publish_ports(firewall_rules, redirect=False, *_, **__):
    """
    Returns all ports as "--publish" arguments.

    Args:
        firewall_rules (list of dict): Firewall rules.
        redirect (bool): Apply port redirection for port <1024.

    Returns:
        str: arguments
    """
    return ' '.join(
        f"-p {port['redirect']}:{port['port']}"
        f"{'' if port['protocol'] == 'all' else '/' + port['protocol']}"
        for port in rules_ports(firewall_rules, redirect=redirect))


def publish_devices(path_list, *_, device=False, privileged=False, **__):
    """
    Returns paths as "--device" or "--mount" arguments.

    Fall back to "--privileged" if no devices found.

    Args:
        path_list (str): List of devices paths, one path per line.
        device (bool): If True, use "--device" args, else use only "--mount"
        privileged (bool): If True, force the add of "--privileged" argument.

    Returns:
        str: arguments
    """
    path_list = [path for path in path_list.strip().splitlines()
                 if path.lstrip('/').split('/', 1)[0] in ('dev', 'sys')]
    args_list = []
    prefixes = ('/dev/dri', '/sys/devices/pci0000:00')

    # Always use "--privileged" if no paths.
    if privileged or not path_list:
        args_list.append('--privileged')

    # Ensure sufficient paths are shared
    for prefix in prefixes:
        if not any(path.startswith(prefix) for path in path_list):
            path_list.append(prefix)

    # Generate arguments
    for path in path_list:
        path = path.strip()
        if device and path.startswith('/dev') and path not in prefixes:
            args_list.append(f'--device={path}')
        else:
            args_list.append(f'--mount=type=bind,src={path},target={path}')

    return ' '.join(args_list)


class FilterModule(object):
    """Return filter plugin"""

    @staticmethod
    def filters():
        """Return filter"""
        return {'rules_ports': rules_ports,
                'publish_ports': publish_ports,
                'publish_devices': publish_devices}
