import validators   # pip3 install validators
import dns.resolver # pip3 install dnspython

def is_domain(text):
    return bool(validators.domain(text))

def is_ipv4(text):
    return bool(validators.ip_address.ipv4(text))

def is_url(text):
    return bool(validators.url(text))

def is_valid_dns(text):
    try:
        dns_resolved = dns.resolver.query(text, 'A')
    except:
        dns_resolved = None
    return bool(dns_resolved)