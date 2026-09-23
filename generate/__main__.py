"""`python3 -m generate [--check | --dry N | --sample N | --sample-ko N [effort] | --ko DATE]`"""

import sys
import urllib.error

from .check import check
from .run import dry, korean_pass, main, sample, sample_ko


def dispatch() -> None:
    if "--check" in sys.argv:
        check()
    elif "--dry" in sys.argv:
        at = sys.argv.index("--dry")
        dry(int(sys.argv[at + 1]) if len(sys.argv) > at + 1 else 3)
    elif "--sample-ko" in sys.argv:
        args = sys.argv[sys.argv.index("--sample-ko") + 1 :]
        sample_ko(int(args[0]) if args else 1, *args[1:2])
    elif "--ko" in sys.argv:
        korean_pass(sys.argv[sys.argv.index("--ko") + 1])
    elif "--sample" in sys.argv:
        at = sys.argv.index("--sample")
        sample(int(sys.argv[at + 1]) if len(sys.argv) > at + 1 else 1)
    else:
        main()


if __name__ == "__main__":
    # Line-buffered: piped to a file or an Actions log, buffering hides every line
    # until the run ends, and splices stderr tracebacks into the middle of a card.
    sys.stdout.reconfigure(line_buffering=True)
    try:
        dispatch()
    except (urllib.error.URLError, TimeoutError, OSError) as err:
        # A cron log should say "the network died", not print 40 lines of urllib.
        sys.exit(f"network error reaching a source: {err}")
