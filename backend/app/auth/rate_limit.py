from collections import defaultdict
from time import time

_ip_store: dict[str, float] = {}


def check_ip(ip: str, interval: float = 60.0) -> bool:
    now = time()
    last = _ip_store.get(ip)
    if last and (now - last) < interval:
        return False
    _ip_store[ip] = now
    # 定期清理过期记录
    if len(_ip_store) > 1000:
        cutoff = now - 300
        for k in list(_ip_store):
            if _ip_store[k] < cutoff:
                del _ip_store[k]
    return True
