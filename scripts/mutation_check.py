"""Policy mutation testing: neutralise each Cedar `forbid` in turn; the test-suite MUST then fail.
A surviving mutant means a security rule is not actually covered by tests.

    python scripts/mutation_check.py
"""
import re
import subprocess
import sys
from pathlib import Path

POLICY = Path(__file__).resolve().parents[1] / "policies" / "transfer.cedar"


def main() -> int:
    original = POLICY.read_text()
    ids = re.findall(r'@id\("(forbid-[^"]+)"\)', original)
    survivors = []
    try:
        for pid in ids:
            blocks = original.split("\n\n")
            mutated = [re.sub(r"(when|unless) \{[^}]*\};", "when { false };", b) if f'@id("{pid}")' in b else b
                       for b in blocks]
            POLICY.write_text("\n\n".join(mutated))
            r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-x"], capture_output=True, text=True, check=False)
            killed = r.returncode != 0
            print(f"{'KILLED  ' if killed else 'SURVIVED'}  {pid}")
            if not killed:
                survivors.append(pid)
    finally:
        POLICY.write_text(original)
    print(f"\n{len(ids) - len(survivors)}/{len(ids)} mutants killed")
    return 1 if survivors else 0


if __name__ == "__main__":
    sys.exit(main())
