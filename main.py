from flask import Flask, request, jsonify
from flask_cors import CORS
from hecate import Hecate
import argparse
import subprocess
import sys
import os
import speech_recognition as sr

# Serve static files (e.g., index.html) from the repository root so the
# Flask server can act as a lightweight static site host.
app = Flask(__name__, static_folder=".", static_url_path="")
@app.route("/")
def root():
    """Serve the main interface."""
    return app.send_static_file("index.html")

CORS(app)

# Instantiate Hecate
hecate = Hecate()


@app.route("/")
def home():
    return jsonify({"message": "MandemOS Hecate online."})


def run_server(host: str, port: int) -> None:
    """Start the Flask API server on the given host and port."""
    app.run(host=host, port=port)

@app.route("/health", methods=["GET"])
def health():
    """Simple health check endpoint."""
    return jsonify({"status": "ok"})

@app.route("/talk", methods=["POST"])
def talk():
    data = request.json
    user_input = data.get("message", "")
    response = hecate.respond(user_input)
    try:
        with open("conversation.log", "a") as log:
            log.write(f"User: {user_input}\n")
            log.write(f"Hecate: {response}\n")
    except Exception:
        pass
    return jsonify({"reply": response})


@app.route("/talk/audio", methods=["POST"])
def talk_audio():
    """Accept an audio file and return the transcript and response."""
    if "file" not in request.files:
        return jsonify({"error": "Missing audio file"}), 400
    audio_file = request.files["file"]
    r = sr.Recognizer()
    with sr.AudioFile(audio_file) as source:
        audio = r.record(source)
    try:
        text = r.recognize_google(audio)
    except Exception as e:
        return jsonify({"error": f"Speech recognition failed: {e}"}), 400
    response = hecate.respond(text)
    return jsonify({"transcript": text, "reply": response})


@app.route("/add_api", methods=["POST"])
def add_api():
    data = request.json
    api_url = data.get("api", "")
    if not api_url:
        return jsonify({"status": "missing api"}), 400
    message = hecate.add_api(api_url)
    return jsonify({"status": message})

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Hecate API server")
    parser.add_argument(
        "-b",
        "--background",
        action="store_true",
        help="Run the front end API server in the background",
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

    if args.background:
        # Relaunch this script detached from the current session
        cmd = [
            sys.executable,
            os.path.abspath(__file__),
            "--host",
            args.host,
            "--port",
            str(args.port),
        ]
        subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
        print("Server started in background")
    else:
        run_server(args.host, args.port)
