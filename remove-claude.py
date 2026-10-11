import re
import sys

for line in sys.stdin:
    line = re.sub(
        r"(?im)^Co-Authored-By:\s*Claude Opus 5\.5\s*<noreply@anthropic\.com>\s*\r?\n?",
        "",
        line
    )
    sys.stdout.write(line)
