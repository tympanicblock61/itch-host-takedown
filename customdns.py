import dns.message
import dns.query
import dns.resolver
from urllib3.util import connection


class DNSAdapter:
    def resolve(self, hostname: str) -> str:
        raise NotImplementedError("resolve must be implemented")

class StandardDNSAdapter(DNSAdapter):
    def __init__(self, nameserver: str):
        self.resolver = dns.resolver.Resolver()
        self.resolver.nameservers = [nameserver]

    def resolve(self, hostname: str) -> str:
        try:
            answer = self.resolver.resolve(hostname)
            return answer[0].to_text()
        except Exception as e:
            raise RuntimeError(f"Standard DNS failed: {e}")

# DNS-over-HTTPS (DoH)
class DoHDNSAdapter(DNSAdapter):
    def __init__(self, doh_url="https://dns.google/dns-query"):
        self.doh_url = doh_url

    def resolve(self, hostname: str) -> str:
        request = dns.message.make_query(hostname, dns.rdatatype.A)
        try:
            response = dns.query.https(request, self.doh_url)
            for answer in response.answer:
                for item in answer.items:
                    if item.rdtype == dns.rdatatype.A:
                        return item.address
        except Exception as e:
            raise RuntimeError(f"DoH failed: {e}")
        raise RuntimeError("No A record found in DoH response")

class ChainedDNSAdapter(DNSAdapter):
    def __init__(self, adapters):
        self.adapters = adapters

    def resolve(self, hostname: str) -> str:
        for adapter in self.adapters:
            try:
                return adapter.resolve(hostname)
            except Exception as e:
                print(f"[!] DNS Adapter failed: {type(adapter).__name__}: {e}")
        raise RuntimeError(f"All DNS adapters failed to resolve {hostname}")

def monkey_patch_dns():
    _orig_create_connection = connection.create_connection

    resolver = ChainedDNSAdapter([
        StandardDNSAdapter("8.8.8.8"), # google
        StandardDNSAdapter("8.8.4.4"), # google
        StandardDNSAdapter("1.1.1.1"), # cloudflare
    ])

    def patched_create_connection(address, *args, **kwargs):
        host, port = address
        ip = resolver.resolve(host)
        return _orig_create_connection((ip, port), *args, **kwargs)

    connection.create_connection = patched_create_connection
