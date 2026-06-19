import time

_rate_limit_store: dict = {}
_rate_limit_last_gc: float = 0.0
_RATE_LIMIT_GC_INTERVAL: float = 300.0


def _rate_limit_gc():
    global _rate_limit_last_gc
    now = time.time()
    if now - _rate_limit_last_gc < _RATE_LIMIT_GC_INTERVAL:
        return
    _rate_limit_last_gc = now
    keys_to_delete = []
    for key, timestamps in _rate_limit_store.items():
        _rate_limit_store[key] = [t for t in timestamps if t > now - 3600]
        if not _rate_limit_store[key]:
            keys_to_delete.append(key)
    for key in keys_to_delete:
        del _rate_limit_store[key]


def check_rate_limit(key: str, max_requests: int, window_seconds: int) -> bool:
    _rate_limit_gc()
    now = time.time()
    _rate_limit_store[key] = [t for t in _rate_limit_store.get(key, []) if t > now - window_seconds]
    if len(_rate_limit_store[key]) >= max_requests:
        return False
    _rate_limit_store[key].append(now)
    return True
