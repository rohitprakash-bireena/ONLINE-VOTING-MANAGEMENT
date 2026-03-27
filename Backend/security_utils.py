import time
from collections import defaultdict, deque

# In-memory tracker: key -> timestamps of failed attempts
_FAILED_LOGIN_ATTEMPTS = defaultdict(deque)


def get_client_ip(request):
    # Respect reverse proxy header when available (e.g., PythonAnywhere)
    forwarded_for = request.headers.get('X-Forwarded-For', '').split(',')[0].strip()
    return forwarded_for or (request.remote_addr or 'unknown')


def _cleanup_old_attempts(attempts, window_seconds, now):
    while attempts and (now - attempts[0] > window_seconds):
        attempts.popleft()


def is_login_rate_limited(key, max_attempts=5, window_seconds=600):
    now = time.time()
    attempts = _FAILED_LOGIN_ATTEMPTS[key]
    _cleanup_old_attempts(attempts, window_seconds, now)
    if len(attempts) >= max_attempts:
        retry_after = int(window_seconds - (now - attempts[0]))
        return True, max(retry_after, 1)
    return False, 0


def register_failed_login_attempt(key):
    _FAILED_LOGIN_ATTEMPTS[key].append(time.time())


def clear_failed_login_attempts(key):
    _FAILED_LOGIN_ATTEMPTS.pop(key, None)
