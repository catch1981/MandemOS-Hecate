from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from hecate import Hecate
import argparse
import subprocess
import sys
import os
import speech_recognition as sr

app = Flask(__name__)
CORS(app)

# Instantiate Hecate
hecate = Hecate()

# Directory for files users can download
SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "scripts")
os.makedirs(SCRIPTS_DIR, exist_ok=True)


def run_server():
    """Start the Flask API server."""
    app.run(host="0.0.0.0", port=8080)

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


@app.route("/files", methods=["GET"])
def list_files():
    """Return a JSON list of files in the scripts directory."""
    files = [f for f in os.listdir(SCRIPTS_DIR) if os.path.isfile(os.path.join(SCRIPTS_DIR, f))]
    return jsonify({"files": files})


@app.route("/files/<path:filename>", methods=["GET"])
def get_file(filename):
    """Serve a file from the scripts directory if present."""
    safe_path = os.path.abspath(os.path.join(SCRIPTS_DIR, filename))
    if not safe_path.startswith(os.path.abspath(SCRIPTS_DIR)) or not os.path.isfile(safe_path):
        return jsonify({"error": "File not found"}), 404
    return send_from_directory(SCRIPTS_DIR, os.path.relpath(safe_path, SCRIPTS_DIR), as_attachment=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Hecate API server")
    parser.add_argument(
        "-b",
        "--background",
        action="store_true",
        help="Run the front end API server in the background",
    )
    args = parser.parse_args()

    if args.background:
        # Relaunch this script detached from the current session
        cmd = [sys.executable, os.path.abspath(__file__)]
        subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
        print("Server started in background")
    else:
        run_server()
