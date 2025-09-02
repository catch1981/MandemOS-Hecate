import os
import runpy
import argparse
import subprocess
import sys

def main():
    parser = argparse.ArgumentParser(description="Launch the Hecate API server")
    parser.add_argument(
        "-b",
        "--background",
        action="store_true",
        help="Run the server in the background",
    )
    parser.add_argument(
        "--host",
        default=os.getenv("HOST", "0.0.0.0"),
        help="Host interface to bind to",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("PORT", "8080")),
        help="Port to listen on",
    )
    args = parser.parse_args()

    current_dir = os.path.dirname(__file__)
    script = os.path.join(current_dir, "OK workspaces", "main.py")

    script_args = ["--host", args.host, "--port", str(args.port)]

    if args.background:
        cmd = [sys.executable, script, "-b"] + script_args
        subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
        print("Server started in background")
    else:
        sys.argv = [script] + script_args
        runpy.run_path(script, run_name="__main__")

if __name__ == "__main__":
    main()
import os
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return 'MandemOS Hecate online.'

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))  # 👈 uses Railway's port
    host = os.environ.get('HOST', '0.0.0.0')
    app.run(host=host, port=port)
