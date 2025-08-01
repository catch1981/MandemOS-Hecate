import os
import subprocess
import sys
import time

SCRIPT = os.getenv("HECATE_ENTRY", "__main__.py")
ARGS = os.getenv("HECATE_ARGS", "").split()
DELAY = float(os.getenv("RESTART_DELAY", "5"))


def main():
    while True:
        try:
            proc = subprocess.Popen([sys.executable, SCRIPT] + ARGS)
            ret = proc.wait()
        except KeyboardInterrupt:
            proc.terminate()
            proc.wait()
            return 1
        if ret == 0:
            return 0
        print(f"Process exited with code {ret}, restarting in {DELAY}s...")
        time.sleep(DELAY)


if __name__ == "__main__":
    sys.exit(main())
