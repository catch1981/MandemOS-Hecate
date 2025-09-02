import os
import subprocess
import sys
import time

SCRIPT = os.getenv("HECATE_ENTRY", "__main__.py")
ARGS = os.getenv("HECATE_ARGS", "").split()
DELAY = float(os.getenv("RESTART_DELAY", "5"))
MAX_CRASHES = int(os.getenv("MAX_CRASHES", "5"))
CRASH_FILE = os.getenv("CRASH_FILE", ".hecate_crashes")
GOOD_FILE = os.getenv("GOOD_COMMIT_FILE", ".hecate_good_commit")


def read_int(path, default=0):
    try:
        with open(path, "r") as fh:
            return int(fh.read().strip() or default)
    except Exception:
        return default


def write_int(path, value):
    try:
        with open(path, "w") as fh:
            fh.write(str(value))
    except Exception:
        pass


def get_current_commit():
    try:
        return (
            subprocess.check_output(["git", "rev-parse", "HEAD"], text=True)
            .strip()
        )
    except Exception:
        return ""


def write_good_commit(commit):
    try:
        with open(GOOD_FILE, "w") as fh:
            fh.write(commit)
    except Exception:
        pass


def read_good_commit():
    try:
        with open(GOOD_FILE, "r") as fh:
            return fh.read().strip()
    except Exception:
        return ""


def rollback():
    commit = read_good_commit()
    if not commit:
        print("No known good commit to roll back to.")
        return
    print(f"Rolling back to last known good commit {commit}...")
    try:
        subprocess.check_call(["git", "reset", "--hard", commit])
    except Exception as e:
        print(f"Rollback failed: {e}")


def main():
    crashes = read_int(CRASH_FILE)
    if crashes >= MAX_CRASHES:
        print(
            f"Detected {crashes} consecutive crashes. Attempting rollback before restarting."
        )
        rollback()
        crashes = 0
        write_int(CRASH_FILE, crashes)

    while True:
        try:
            proc = subprocess.Popen([sys.executable, SCRIPT] + ARGS)
            ret = proc.wait()
        except KeyboardInterrupt:
            proc.terminate()
            proc.wait()
            return 1

        if ret == 0:
            write_int(CRASH_FILE, 0)
            good = get_current_commit()
            if good:
                write_good_commit(good)
            return 0

        crashes += 1
        write_int(CRASH_FILE, crashes)
        if crashes >= MAX_CRASHES:
            print(
                f"Process crashed {crashes} times. Performing rollback to avoid crash loop."
            )
            rollback()
            crashes = 0
            write_int(CRASH_FILE, crashes)

        print(
            f"Process exited with code {ret}, restarting in {DELAY}s (crash {crashes}/{MAX_CRASHES})..."
        )
        time.sleep(DELAY)


if __name__ == "__main__":
    sys.exit(main())
