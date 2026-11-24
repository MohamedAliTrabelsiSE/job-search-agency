"""One process-wide eight-request budget shared by all scout threads."""
import json
import threading
import time
import urllib.error
import urllib.request

REQUEST_BUDGET = threading.BoundedSemaphore(8)
UA = 'job-search-agency/0.2 (public posting reader; does not apply)'


def fetch(url, timeout=25):
    for attempt in range(3):
        try:
            request = urllib.request.Request(url, headers={'User-Agent':UA, 'Accept':'application/json'})
            with REQUEST_BUDGET:
                with urllib.request.urlopen(request, timeout=timeout) as response:
                    return json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504) or attempt == 2:
                raise
        except (TimeoutError, urllib.error.URLError):
            if attempt == 2:
                raise
        time.sleep(0.25 * (2 ** attempt))
