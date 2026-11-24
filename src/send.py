"""The only file allowed to grow a send path later. v0.1 has none.

There is no SMTP client, no HTTP client, and no --send implementation.
Adding one later requires an explicit flag, a rate limit, and a human
confirming the exact recipient. Until that exists, this script exits.
"""

import sys


def main():
    sys.stderr.write(
        "v0.1 does not send email and does not submit applications.\n"
        "Write a draft with src/outbox.py. A person sends it.\n"
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
