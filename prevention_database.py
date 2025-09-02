"""Create a small database of security prevention methods and example tools.

Running this script creates ``prevention.db`` with a single table named
``preventions``. Each row stores a prevention technique and a concrete example
that organizations can apply when planning defenses.
"""

import sqlite3

DB_NAME = "prevention.db"

PREVENTION_DATA = [
    ("Antivirus Software", "Deploy solutions like ClamAV or Windows Defender"),
    ("Regular Patching", "Keep operating systems and applications up to date"),
    ("Firewalls", "Use iptables or hardware appliances to filter traffic"),
    ("User Education", "Train staff to identify phishing and social engineering"),
]


def init_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS preventions (
            id INTEGER PRIMARY KEY,
            method TEXT NOT NULL,
            example TEXT NOT NULL
        )
        """
    )
    cur.executemany("INSERT INTO preventions (method, example) VALUES (?, ?)", PREVENTION_DATA)
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print(f"Database '{DB_NAME}' initialized with {len(PREVENTION_DATA)} prevention methods.")
