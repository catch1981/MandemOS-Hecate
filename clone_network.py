import os
import threading
import time
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from firewall import sanitize_text
import sqlite3

DB_NAME = 'mandemos.db'


def _ensure_db():
    """Create the keyword_usage table if it doesn't exist."""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        "CREATE TABLE IF NOT EXISTS keyword_usage ("
        "clone_id TEXT NOT NULL, "
        "keyword TEXT NOT NULL, "
        "count INTEGER NOT NULL DEFAULT 0, "
        "PRIMARY KEY (clone_id, keyword)"
        ")"
    )
    conn.commit()
    conn.close()

# Track keyword usage across clones
KEYWORDS = {"glitch", "frequency", "vibration", "null"}
keyword_stats = {}

# Persisted storage files
MESSAGES_FILE = "clone_messages.log"
MEMORIES_FILE = "shared_memory.txt"
TASKS_FILE = "tasks.log"
RESULTS_FILE = "task_results.log"


def _load_endpoints():
    env = os.getenv("SERVER_ENDPOINTS")
    if env:
        return [u.strip() for u in env.split(',') if u.strip()]
    return []


SERVER_ENDPOINTS = _load_endpoints()
SYNC_INTERVAL = float(os.getenv("SERVER_SYNC_INTERVAL", "10"))


def _load_lines(path):
    """Return list of non-empty lines from a file."""
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                return [line.strip() for line in f if line.strip()]
        except Exception:
            pass
    return []


def _append_line(path, line):
    """Append a single line to a file, ignore errors."""
    try:
        with open(path, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass


def _broadcast(path, payload):
    """Send a POST request with payload to all known endpoints."""
    for url in list(SERVER_ENDPOINTS):
        try:
            requests.post(f"{url}{path}?forwarded=1", json=payload, timeout=5)
        except Exception:
            if url in SERVER_ENDPOINTS:
                SERVER_ENDPOINTS.remove(url)


def _sync_from_servers():
    """Merge updates from peer servers and drop unreachable ones."""
    for url in list(SERVER_ENDPOINTS):
        try:
            resp = requests.get(f"{url}/updates", timeout=5)
            if not resp.ok:
                continue
            data = resp.json()
            for entry in data.get('messages', []):
                if entry not in messages:
                    messages.append(entry)
                    _append_line(MESSAGES_FILE, entry)
            for entry in data.get('memories', []):
                if entry not in memories:
                    memories.append(entry)
                    _append_line(MEMORIES_FILE, entry)
            for entry in data.get('tasks', []):
                if entry not in tasks:
                    tasks.append(entry)
                    _append_line(TASKS_FILE, entry)
            for entry in data.get('results', []):
                if entry not in results:
                    results.append(entry)
                    _append_line(RESULTS_FILE, entry)
        except Exception:
            if url in SERVER_ENDPOINTS:
                SERVER_ENDPOINTS.remove(url)


def _sync_loop():
    while True:
        _sync_from_servers()
        time.sleep(SYNC_INTERVAL)


def _update_keyword_stats(clone_id, text):
    """Increment keyword counts for the given clone based on text."""
    words = text.lower().split()
    stats = keyword_stats.setdefault(clone_id, {k: 0 for k in KEYWORDS})
    updates = {}
    for kw in KEYWORDS:
        inc = sum(1 for w in words if kw in w)
        if inc:
            stats[kw] += inc
            updates[kw] = stats[kw]

    if updates:
        try:
            _ensure_db()
            conn = sqlite3.connect(DB_NAME)
            cur = conn.cursor()
            for kw, count in updates.items():
                cur.execute(
                    "INSERT INTO keyword_usage (clone_id, keyword, count) "
                    "VALUES (?, ?, ?) "
                    "ON CONFLICT(clone_id, keyword) DO UPDATE SET count=excluded.count",
                    (clone_id, kw, count),
                )
            conn.commit()
        except Exception:
            pass
        finally:
            try:
                conn.close()
            except Exception:
                pass

app = Flask(__name__)
CORS(app)

# Load persisted data
messages = _load_lines(MESSAGES_FILE)
memories = _load_lines(MEMORIES_FILE)
tasks = _load_lines(TASKS_FILE)
results = _load_lines(RESULTS_FILE)

@app.route('/health', methods=['GET'])
def health():
    """Simple health check endpoint."""
    return jsonify({'status': 'ok'})

@app.route('/send', methods=['POST'])
def send_message():
    data = request.get_json(force=True)
    clone_id = data.get('id', 'unknown')
    msg = data.get('message', '')
    if msg:
        msg = sanitize_text(msg)
        entry = f"{clone_id}: {msg}"
        messages.append(entry)
        _append_line(MESSAGES_FILE, entry)
        _update_keyword_stats(clone_id, msg)
        if not request.args.get('forwarded'):
            _broadcast('/send', {'id': clone_id, 'message': msg})
        return jsonify({'status': 'ok'})
    return jsonify({'error': 'missing message'}), 400

@app.route('/read', methods=['GET'])
def read_messages():
    return '\n'.join(messages)

@app.route('/remember', methods=['POST'])
def remember_fact():
    data = request.get_json(force=True)
    clone_id = data.get('id', 'unknown')
    fact = data.get('fact', '')
    if fact:
        fact = sanitize_text(fact)
        entry = f"{clone_id}: {fact}"
        memories.append(entry)
        _append_line(MEMORIES_FILE, entry)
        _update_keyword_stats(clone_id, fact)
        if not request.args.get('forwarded'):
            _broadcast('/remember', {'id': clone_id, 'fact': fact})
        return jsonify({'status': 'ok'})
    return jsonify({'error': 'missing fact'}), 400

@app.route('/memories', methods=['GET'])
def get_memories():
    return '\n'.join(memories)


@app.route('/keywords', methods=['GET'])
def get_keyword_stats():
    """Return keyword usage statistics."""
    return jsonify(keyword_stats)

@app.route('/task', methods=['POST'])
def add_task():
    data = request.get_json(force=True)
    task = data.get('task')
    if task:
        task = sanitize_text(task)
        tasks.append(task)
        _append_line(TASKS_FILE, task)
        if not request.args.get('forwarded'):
            _broadcast('/task', {'task': task})
        return jsonify({'status': 'queued'})
    return jsonify({'error': 'missing task'}), 400

@app.route('/task/assign', methods=['GET'])
def assign_task():
    if tasks:
        task = tasks.pop(0)
        return jsonify({'task': task})
    return jsonify({'task': None})

@app.route('/task/result', methods=['POST'])
def store_result():
    data = request.get_json(force=True)
    result = data.get('result')
    clone_id = data.get('id', 'unknown')
    if result is not None:
        result = sanitize_text(str(result))
        entry = f"{clone_id}: {result}"
        results.append(entry)
        _append_line(RESULTS_FILE, entry)
        if not request.args.get('forwarded'):
            _broadcast('/task/result', {'id': clone_id, 'result': result})
        return jsonify({'status': 'stored'})
    return jsonify({'error': 'missing result'}), 400


@app.route('/updates', methods=['GET'])
def all_updates():
    """Return all stored messages, memories, tasks and results."""
    return jsonify({
        'messages': messages,
        'memories': memories,
        'tasks': tasks,
        'results': results,
    })

if __name__ == '__main__':
    if SERVER_ENDPOINTS:
        threading.Thread(target=_sync_loop, daemon=True).start()
    port = int(os.getenv('CLONE_PORT', '5000'))
    app.run(host='0.0.0.0', port=port)
