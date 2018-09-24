from rest_framework import permissions

WHITELIST_IPS = ['192.168.1.220', '127.0.0.1', '192.168.81.57']


def get_ip(request):
    """Returns the IP of the request, accounting for the possibility of being behind a proxy. """
    ip = request.META.get("HTTP_X_FORWARDED_FOR", None)
    if ip:
        # X_FORWARDED_FOR returns client1, proxy1, proxy2,...
        ip = ip.split(", ")[0]
    else:
        ip = request.META.get("REMOTE_ADDR", "")
    return ip


class WhitelistPermission(permissions.BasePermission):
    """
    Global permission check for whitelisted IPs.
    """

    def has_permission(self, request, view):
        ip_addr = get_ip(request)
        return ip_addr in WHITELIST_IPS