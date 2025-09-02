import sys
import io
import os
import requests
from bs4 import BeautifulSoup
import smtplib
import imaplib
import email
from email.mime.text import MIMEText
import openai
import subprocess
from agent_manager import AgentManager
from self_improvement_lattice import SelfImprovementLattice
try:
    import firebase_admin
    from firebase_admin import credentials, firestore
except Exception:  # pragma: no cover - firebase is optional
    firebase_admin = None
    credentials = None
    firestore = None

# Allow overriding the OpenAI model via environment variable. Default to gpt-4o
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")


def _load_openai_key():
    """Fetch the OpenAI API key from env or local file."""
    key = os.getenv("OPENAI_API_KEY")
    if key:
        return key

    # Try to read from openai_key.txt at repository root
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    key_path = os.path.join(root_dir, "openai_key.txt")
    if os.path.exists(key_path):
        with open(key_path, "r") as f:
            return f.read().strip()
    return None


openai.api_key = _load_openai_key()

os.makedirs("scripts", exist_ok=True)

class Hecate:
    def __init__(self, name="Hecate", personality="bold and adaptive", coder=True):
        self.name = name
        self.personality = personality
        self.coder = coder
        self.memory_file = "memory.txt"
        self.clone_log_file = "clone_messages.log"
        self.shared_memory_file = "shared_memory.txt"
        self.clone_id = os.getenv("CLONE_ID", os.uname().nodename)
        self.clone_server = os.getenv("CLONE_SERVER_URL")
        endpoints = os.getenv("CLONE_ENDPOINTS")
        if endpoints:
            self.clone_endpoints = [e.strip() for e in endpoints.split(',') if e.strip()]
        elif self.clone_server:
            self.clone_endpoints = [self.clone_server]
        else:
            self.clone_endpoints = []
        self.last_code = ""
        self.gmail_user = os.getenv("GMAIL_USER")
        self.gmail_pass = os.getenv("GMAIL_PASS")
        self.current_location = None
        self.user_name = None
        self._asked_identity = False
        self.distress_phrases = [
            "help",
            "help me",
            "i'm scared",
            "i’m scared",
            "i'll call my dad",
            "i’ll call my dad",
            "stop it now",
            "leave me alone",
        ]
        self.admin = False
        self.admin_password = os.getenv("ADMIN_PASSWORD", "whostheboss")
        self.admin_file = "admin_status.txt"
        self._load_admin_status()
        self.lattice = SelfImprovementLattice()
        self.agent_manager = AgentManager()
        # store recent conversation turns for context-aware replies
        self.conversation = []
        # optional Firebase database for memory retention
        self.firebase_db = None
        cred_path = os.getenv("FIREBASE_CRED_PATH")
        if firebase_admin and cred_path and os.path.exists(cred_path):
            try:
                cred = credentials.Certificate(cred_path)
                if not firebase_admin._apps:
                    firebase_admin.initialize_app(cred)
                self.firebase_db = firestore.client()
            except Exception:
                self.firebase_db = None

    def startup_message(self):
        """Return the initial prompt asking for the user's identity."""
        if not self._asked_identity:
            self._asked_identity = True
            return f"{self.name}: Who are you?"
        return None

    def respond(self, user_input):
        if not self._asked_identity:
            # If startup_message was never retrieved, ask for user's identity now
            self._asked_identity = True
            return f"{self.name}: Who are you?"

        if self.user_name is None:
            # Treat the first user response as their name
            self.user_name = user_input.strip() or None
            if self.user_name:
                return f"{self.name}: Nice to meet you, {self.user_name}."

        if user_input.startswith("admin:"):
            cmd = user_input.split("admin:", 1)[1].strip()
            if cmd == "status":
                state = "granted" if self.admin else "not granted"
                return f"{self.name}: Admin rights {state}."
            elif cmd == "logout":
                self.admin = False
                self._save_admin_status()
                return f"{self.name}: Admin privileges revoked."
            else:
                if cmd == self.admin_password:
                    self.admin = True
                    self._save_admin_status()
                    return f"{self.name}: Admin privileges granted."
                else:
                    return f"{self.name}: Incorrect admin password."

        if user_input.startswith("remember:"):
            fact = user_input.split("remember:", 1)[1].strip()
            return self._remember_fact(fact)

        elif user_input == "recall":
            return self._recall_facts()

        elif user_input == "summarize":
            return self._summarize_memory()

        elif user_input.startswith("run:"):
            code = user_input.split("run:", 1)[1].strip()
            self.last_code = code
            return self._run_code(code)

        elif user_input.startswith("save:"):
            filename = user_input.split("save:", 1)[1].strip()
            return self._save_code(filename)

        elif user_input.startswith("load:"):
            filename = user_input.split("load:", 1)[1].strip()
            return self._load_and_run(filename)

        elif user_input.startswith("retrieve:"):
            try:
                url, filename = user_input.split("retrieve:", 1)[1].split("|", 1)
                return self._retrieve_file(url.strip(), filename.strip())
            except ValueError:
                return f"{self.name}: Use 'retrieve:url|filename'"

        elif user_input.startswith("create:"):
            try:
                parts = user_input.split("create:", 1)[1].split("|", 1)
                filename = parts[0].strip()
                content = parts[1] if len(parts) > 1 else ""
                return self._create_file(filename, content)
            except Exception:
                return f"{self.name}: Use 'create:filename|content'"

        elif user_input.startswith("move:"):
            try:
                src, dest = user_input.split("move:", 1)[1].split("|", 1)
                return self._move_file(src.strip(), dest.strip())
            except ValueError:
                return f"{self.name}: Use 'move:src|dest'"

        elif user_input.strip() == "list":
            return self._list_files()

        elif user_input.startswith("read:"):
            filename = user_input.split("read:", 1)[1].strip()
            return self._read_file(filename)

        elif user_input.startswith("delete:"):
            filename = user_input.split("delete:", 1)[1].strip()
            return self._delete_file(filename)

        elif user_input.startswith("search:"):
            query = user_input.split("search:", 1)[1].strip()
            return self._search_web(query)

        elif user_input.startswith("selfupdate:"):
            code_snippet = user_input.split("selfupdate:", 1)[1].strip()
            return self._self_update(code_snippet)

        elif user_input.startswith("selfrepair:"):
            desc = user_input.split("selfrepair:", 1)[1].strip()
            return self._self_repair(desc)

        elif user_input.startswith("selfimprove:"):
            desc = user_input.split("selfimprove:", 1)[1].strip()
            return self._self_improve(desc)

        elif user_input.strip() == "update:deps":
            return self._update_dependencies()

        elif user_input.strip() == "update:repo":
            return self._update_repo()

        elif user_input.startswith("agent:add:"):
            try:
                name, desc = user_input.split("agent:add:", 1)[1].split("|", 1)
                self.agent_manager.add_agent(name.strip(), desc.strip())
                return f"{self.name}: Agent '{name.strip()}' added."
            except ValueError:
                return f"{self.name}: Use 'agent:add:name|description'"

        elif user_input.strip() == "agent:list":
            agents = self.agent_manager.list_agents()
            if not agents:
                return f"{self.name}: No agents registered."
            lines = [f"{a['name']}: {a['description']}" for a in agents]
            return f"{self.name}: Registered agents:\n" + "\n".join(lines)

        elif user_input.startswith("email:"):
            try:
                to, subject, body = user_input.split("email:", 1)[1].split("|", 2)
                return self._send_email(to.strip(), subject.strip(), body.strip())
            except ValueError:
                return f"{self.name}: Use 'email:recipient|subject|body'"

        elif user_input.startswith("location:"):
            try:
                parts = user_input.split("location:", 1)[1].split("|")
                lat = parts[0].strip()
                lon = parts[1].strip()
                self.current_location = (lat, lon)
                if len(parts) > 2:
                    to = parts[2].strip()
                    subject = "Location Data"
                    body = f"Latitude: {lat}\nLongitude: {lon}"
                    return self._send_email(to, subject, body)
                return f"{self.name}: Location tagged at {lat}, {lon}."
            except Exception:
                return f"{self.name}: Use 'location:lat|lon|email'"

        elif user_input.startswith("learn:"):
            content = user_input.split("learn:", 1)[1].strip()
            return self._learn_from_text(content)

        elif user_input.startswith("clone:learn:"):
            content = user_input.split("clone:learn:", 1)[1].strip()
            return self._clone_learn(content)

        elif user_input.startswith("clone:send:"):
            message = user_input.split("clone:send:", 1)[1].strip()
            return self._clone_send(message)

        elif user_input.strip() == "clone:read":
            return self._clone_read()

        elif user_input.startswith("clone:remember:"):
            fact = user_input.split("clone:remember:", 1)[1].strip()
            return self._clone_remember(fact)

        elif user_input.strip() == "clone:memories":
            return self._clone_memories()

        elif user_input.startswith("extrapolate:"):
            content = user_input.split("extrapolate:", 1)[1]
            parts = [p.strip() for p in content.split("|")]
            scenario = parts[0] if parts else ""
            data = None
            history = None
            for p in parts[1:]:
                if p.startswith("data:"):
                    data = p.split("data:", 1)[1].strip()
                elif p.startswith("history:"):
                    history = p.split("history:", 1)[1].strip()
            return self._extrapolate_outcomes(scenario, data, history)

        elif user_input.strip() == "lattice:show":
            return self.lattice.list_tasks()

        elif user_input.startswith("lattice:add:"):
            try:
                category, task = user_input.split("lattice:add:", 1)[1].split("|", 1)
                self.lattice.add_task(category.strip(), task.strip())
                return f"{self.name}: Improvement task added."
            except ValueError:
                return f"{self.name}: Use 'lattice:add:category|task'"

        elif user_input.startswith("lattice:complete:"):
            try:
                category, num = user_input.split("lattice:complete:", 1)[1].split("|", 1)
                if self.lattice.complete_task(category.strip(), int(num) - 1):
                    return f"{self.name}: Task marked complete."
                return f"{self.name}: Task not found."
            except ValueError:
                return f"{self.name}: Use 'lattice:complete:category|number'"

        elif user_input.strip() == "lattice:reset":
            self.lattice.reset()
            return f"{self.name}: Lattice reset."

        elif any(p in user_input.lower() for p in self.distress_phrases) or "alika in distress" in user_input.lower():
            to = os.getenv("DISTRESS_EMAIL")
            if not self.current_location:
                return f"{self.name}: No location available."
            if not to:
                return f"{self.name}: No emergency contact configured."
            lat, lon = self.current_location
            subject = "Distress Location"
            body = f"Latitude: {lat}\nLongitude: {lon}"
            return self._send_email(to, subject, body)

        elif user_input.startswith("inbox"):
            try:
                count = int(user_input.split(":", 1)[1]) if ":" in user_input else 5
            except ValueError:
                count = 5
            return self._fetch_emails(count)

        elif "code" in user_input.lower() and self.coder:
            return f"{self.name}: What kind of code would you like me to write for you?"

        else:
            return self._chatgpt_response(user_input)

    def _save_memory(self, fact):
        """Persist a fact to local file and Firebase if available."""
        if self.firebase_db:
            try:
                self.firebase_db.collection("memory").add({"fact": fact})
            except Exception:
                pass
        with open(self.memory_file, "a") as f:
            f.write(fact + "\n")

    def _load_memories(self):
        """Load all remembered facts from Firebase or local file."""
        facts = []
        if self.firebase_db:
            try:
                docs = self.firebase_db.collection("memory").stream()
                facts = [d.to_dict().get("fact", "") for d in docs]
            except Exception:
                facts = []
        if not facts and os.path.exists(self.memory_file):
            with open(self.memory_file, "r") as f:
                facts = [line.strip() for line in f if line.strip()]
        return facts

    def _remember_fact(self, fact):
        self._save_memory(fact)
        return f"{self.name}: Got it. I’ll remember that."

    def _recall_facts(self):
        facts = self._load_memories()
        if not facts:
            return f"{self.name}: I don’t have any memories yet."
        joined = "\n".join(facts)
        return f"{self.name}: Here's what I remember:\n{joined}"

    def _summarize_memory(self):
        """Return a short summary of remembered facts using ChatGPT."""
        facts_list = self._load_memories()
        if not facts_list:
            return f"{self.name}: I don’t have any memories yet."
        facts = "\n".join(facts_list)
        try:
            prompt = (
                "Summarize the following notes in a concise paragraph:"\
                f"\n{facts}"
            )
            resp = openai.ChatCompletion.create(
                model=OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
            )
            summary = resp.choices[0].message["content"].strip()
            return f"{self.name}: {summary}"
        except Exception as e:
            return f"{self.name}: Failed to summarize memory:\n{e}"

    def _learn_from_text(self, content):
        """Generate key takeaways from text and store them in memory."""
        if not content:
            return f"{self.name}: No text provided to learn from."
        try:
            prompt = (
                "Extract the key lessons or facts from the following text in short bullet points:"\
                f"\n{content}"
            )
            resp = openai.ChatCompletion.create(
                model=OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
            )
            summary = resp.choices[0].message["content"].strip()
            self._save_memory(summary)
            return f"{self.name}: I've noted the key points."
        except Exception as e:
            return f"{self.name}: Failed to learn from text:\n{e}"

    def _clone_learn(self, content):
        """Learn from text and store the bullet points in shared clone memory."""
        if not content:
            return f"{self.name}: No text provided to learn from."
        try:
            prompt = (
                "Extract the key lessons or facts from the following text in short bullet points:"
                f"\n{content}"
            )
            resp = openai.ChatCompletion.create(
                model=OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
            )
            summary = resp.choices[0].message["content"].strip()
            with open(self.shared_memory_file, "a") as f:
                f.write(summary + "\n")
            return f"{self.name}: I've shared the key points."
        except Exception as e:
            return f"{self.name}: Failed to learn from text:\n{e}"

    def _extrapolate_outcomes(self, scenario, data=None, history=None):
        """Extrapolate outcomes and, when possible, gauge probabilities from history."""
        if not scenario:
            return f"{self.name}: No scenario provided to extrapolate."

        results = []

        if openai.api_key:
            try:
                prompt = (
                    "Given the following scenario, list possible outcomes and eventualities in bullet points:"\
                    f"\n{scenario}"
                )
                resp = openai.ChatCompletion.create(
                    model=OPENAI_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                )
                results.append(resp.choices[0].message["content"].strip())
            except Exception as e:
                results.append(f"Failed to extrapolate outcomes:\n{e}")
        else:
            results.append("OpenAI API key not configured.")

        if data and history:
            ratios = self._compute_probability_ratios(data, history)
            if ratios:
                lines = [f"- {item}: {prob:.2%}" for item, prob in ratios.items()]
                results.append("Historical probability ratios:\n" + "\n".join(lines))
            else:
                results.append("Historical probability ratios could not be computed.")

        return f"{self.name}: " + "\n\n".join(results)

    def _compute_probability_ratios(self, data, history):
        """Compute probability ratios for outcomes based on historical data."""
        data_items = [d.strip() for d in data.split(',') if d.strip()]
        history_items = [h.strip() for h in history.split(',') if h.strip()]
        if not data_items or not history_items:
            return {}
        total = len(history_items)
        counts = {item: history_items.count(item) for item in data_items}
        return {item: counts.get(item, 0) / total for item in data_items}

    def _save_code(self, filename):
        if not self.last_code:
            return f"{self.name}: There's no code to save yet."
        path = os.path.join("scripts", filename)
        with open(path, "w") as f:
            f.write(self.last_code)
        return f"{self.name}: Code saved as {filename}."

    def _load_and_run(self, filename):
        path = os.path.join("scripts", filename)
        if not os.path.exists(path):
            return f"{self.name}: I couldn’t find a file named {filename}."
        with open(path, "r") as f:
            code = f.read()
        self.last_code = code
        return self._run_code(code)

    def _retrieve_file(self, url, filename):
        path = os.path.join("scripts", filename)
        try:
            res = requests.get(url, timeout=10)
            res.raise_for_status()
            with open(path, "wb") as f:
                f.write(res.content)
            clean, msg = self._scan_file(path)
            if not clean:
                return f"{self.name}: {msg}"
            return f"{self.name}: File saved as {filename}."
        except Exception as e:
            return f"{self.name}: Failed to retrieve file:\n{e}"

    def _create_file(self, filename, content=""):
        path = os.path.join("scripts", filename)
        try:
            with open(path, "w") as f:
                f.write(content)
            return f"{self.name}: Created file {filename}."
        except Exception as e:
            return f"{self.name}: Failed to create file:\n{e}"

    def add_api(self, api_url):
        """Record an external API endpoint for future use."""
        path = os.path.join("scripts", "apis.txt")
        try:
            with open(path, "a") as f:
                f.write(api_url.strip() + "\n")
            return f"{self.name}: API {api_url} added."
        except Exception as e:
            return f"{self.name}: Failed to add API:\n{e}"

    def _move_file(self, src, dest):
        src_path = os.path.join("scripts", src)
        dest_path = os.path.join("scripts", dest)
        try:
            if not os.path.exists(src_path):
                return f"{self.name}: Source file {src} not found."
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            os.rename(src_path, dest_path)
            return f"{self.name}: Moved {src} to {dest}."
        except Exception as e:
            return f"{self.name}: Failed to move file:\n{e}"

    def _list_files(self):
        path = "scripts"
        try:
            files = os.listdir(path)
            if not files:
                return f"{self.name}: No files found."
            return "\n".join(files)
        except Exception as e:
            return f"{self.name}: Failed to list files:\n{e}"

    def _read_file(self, filename):
        path = os.path.join("scripts", filename)
        try:
            if not os.path.exists(path):
                return f"{self.name}: {filename} not found."
            with open(path, "r") as f:
                return f.read()
        except Exception as e:
            return f"{self.name}: Failed to read file:\n{e}"

    def _delete_file(self, filename):
        path = os.path.join("scripts", filename)
        try:
            if not os.path.exists(path):
                return f"{self.name}: {filename} not found."
            os.remove(path)
            return f"{self.name}: Deleted {filename}."
        except Exception as e:
            return f"{self.name}: Failed to delete file:\n{e}"

    def _scan_file(self, path):
        """Check a file for viruses using clamscan."""
        try:
            result = subprocess.run(
                ["clamscan", path], capture_output=True, text=True
            )
        except FileNotFoundError:
            return True, "clamscan not found"
        if result.returncode == 1:
            os.makedirs("quarantine", exist_ok=True)
            qpath = os.path.join("quarantine", os.path.basename(path))
            os.rename(path, qpath)
            return False, f"File infected. Moved to {qpath}"
        if result.returncode != 0:
            return True, f"Scan error: {result.stderr.strip()}"
        return True, "clean"

    def _run_code(self, code):
        buffer = io.StringIO()
        try:
            sys.stdout = buffer
            exec(code, {})
            sys.stdout = sys.__stdout__
            return f"{self.name}: Output from your code:\n{buffer.getvalue()}"
        except Exception as e:
            sys.stdout = sys.__stdout__
            return f"{self.name}: Error while running code:\n{e}"

    def _search_web(self, query):
        try:
            url = f"https://duckduckgo.com/html/?q={query.replace(' ', '+')}"
            headers = {'User-Agent': 'Mozilla/5.0'}
            res = requests.get(url, headers=headers, timeout=5)
            soup = BeautifulSoup(res.text, 'html.parser')
            results = soup.find_all('a', class_='result__a', limit=3)
            if not results:
                return f"{self.name}: I searched, but found no clear results."
            response = f"{self.name}: Here's what I found:\n"
            for i, r in enumerate(results, 1):
                response += f"{i}. {r.text.strip()}\n   Link: {r['href']}\n"
            return response
        except Exception as e:
            return f"{self.name}: I ran into an issue while searching:\n{e}"

    def _self_update(self, code_snippet):
        """Append a code snippet to my own source file."""
        try:
            my_path = os.path.abspath(__file__)
            with open(my_path, "a") as f:
                f.write("\n" + code_snippet + "\n")
            return f"{self.name}: I've added the provided code to my source file."
        except Exception as e:
            return f"{self.name}: Failed to update myself:\n{e}"

    def _self_repair(self, description):
        """Attempt to repair my source file using ChatGPT."""
        if not openai.api_key:
            return f"{self.name}: OpenAI API key not configured."
        try:
            my_path = os.path.abspath(__file__)
            with open(my_path, "r") as f:
                current = f.read()
            prompt = (
                "You are an automated repair system. "
                "Given the following Python code:\n" + current + "\n\n" +
                "Problem description: " + description + "\n\n" +
                "Return the full corrected code."
            )
            resp = openai.ChatCompletion.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}]
            )
            new_code = resp.choices[0].message["content"].strip()
            backup_path = my_path + ".bak"
            with open(backup_path, "w") as b:
                b.write(current)
            with open(my_path, "w") as f:
                f.write(new_code)
            return f"{self.name}: Self-repair attempted. Backup at {backup_path}."
        except Exception as e:
            return f"{self.name}: Failed to repair myself:\n{e}"

    def _self_improve(self, suggestion):
        """Attempt to refactor my source file based on a suggestion."""
        if not openai.api_key:
            return f"{self.name}: OpenAI API key not configured."
        try:
            my_path = os.path.abspath(__file__)
            with open(my_path, "r") as f:
                current = f.read()
            prompt = (
                "You are an automated refactoring tool. "
                "Improve the following Python code based on this suggestion: "
                + suggestion + "\n\nCODE:\n" + current + "\n\n" +
                "Return the full updated code."
            )
            resp = openai.ChatCompletion.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}]
            )
            new_code = resp.choices[0].message["content"].strip()
            backup_path = my_path + ".bak"
            with open(backup_path, "w") as b:
                b.write(current)
            with open(my_path, "w") as f:
                f.write(new_code)
            return f"{self.name}: Self-improvement attempted. Backup at {backup_path}."
        except Exception as e:
            return f"{self.name}: Failed to improve myself:\n{e}"

    def _update_dependencies(self):
        """Install or upgrade required Python packages."""
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "--upgrade", "-r", "requirements.txt"]
            )
            return f"{self.name}: Dependencies updated."
        except Exception as e:
            return f"{self.name}: Failed to update dependencies:\n{e}"

    def _update_repo(self):
        """Pull the latest changes from the git repository."""
        try:
            remotes = subprocess.check_output(["git", "remote"]).decode().split()
            if not remotes:
                return f"{self.name}: No git remote configured."
            subprocess.check_call(["git", "pull"])
            return f"{self.name}: Repository updated."
        except Exception as e:
            return f"{self.name}: Failed to update repository:\n{e}"

    def _send_email(self, to_addr, subject, body):
        if not (self.gmail_user and self.gmail_pass):
            return f"{self.name}: Gmail credentials not configured."
        try:
            msg = MIMEText(body)
            msg["Subject"] = subject
            msg["From"] = self.gmail_user
            msg["To"] = to_addr
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(self.gmail_user, self.gmail_pass)
                server.sendmail(self.gmail_user, [to_addr], msg.as_string())
            return f"{self.name}: Email sent to {to_addr}."
        except Exception as e:
            return f"{self.name}: Failed to send email:\n{e}"

    def _fetch_emails(self, count=5):
        if not (self.gmail_user and self.gmail_pass):
            return f"{self.name}: Gmail credentials not configured."
        try:
            with imaplib.IMAP4_SSL("imap.gmail.com") as imap:
                imap.login(self.gmail_user, self.gmail_pass)
                imap.select("inbox")
                typ, data = imap.search(None, "ALL")
                if typ != 'OK':
                    return f"{self.name}: Unable to fetch emails."
                ids = data[0].split()
                latest_ids = ids[-count:]
                messages = []
                for i in reversed(latest_ids):
                    typ, msg_data = imap.fetch(i, "(RFC822)")
                    if typ != 'OK':
                        continue
                    msg = email.message_from_bytes(msg_data[0][1])
                    subj = msg.get("Subject", "(no subject)")
                    frm = msg.get("From", "(unknown)")
                    messages.append(f"From: {frm}\nSubject: {subj}")
                imap.close()
            return "\n\n".join(messages) if messages else f"{self.name}: No emails found."
        except Exception as e:
            return f"{self.name}: Failed to fetch emails:\n{e}"

    def _clone_send(self, message):
        sent = False
        for url in list(self.clone_endpoints):
            try:
                resp = requests.post(
                    f"{url}/send",
                    json={"id": self.clone_id, "message": message},
                    timeout=5,
                )
                if resp.ok:
                    sent = True
            except Exception:
                self.clone_endpoints.remove(url)
        if sent:
            return f"{self.name}: Message broadcast."
        try:
            with open(self.clone_log_file, "a") as f:
                f.write(f"{self.clone_id}: {message}\n")
            return f"{self.name}: Message broadcast."
        except Exception as e:
            return f"{self.name}: Failed to send message:\n{e}"

    def _clone_read(self):
        parts = []
        for url in list(self.clone_endpoints):
            try:
                resp = requests.get(f"{url}/read", timeout=5)
                if resp.ok:
                    text = resp.text.strip()
                    if text:
                        parts.append(text)
            except Exception:
                self.clone_endpoints.remove(url)
        if parts:
            return "\n".join(parts)
        if not os.path.exists(self.clone_log_file):
            return f"{self.name}: No messages."
        with open(self.clone_log_file, "r") as f:
            data = f.read().strip()
        return data if data else f"{self.name}: (no messages)"

    def _clone_remember(self, fact):
        stored = False
        for url in list(self.clone_endpoints):
            try:
                resp = requests.post(
                    f"{url}/remember",
                    json={"id": self.clone_id, "fact": fact},
                    timeout=5,
                )
                if resp.ok:
                    stored = True
            except Exception:
                self.clone_endpoints.remove(url)
        if stored:
            return f"{self.name}: Shared memory stored."
        try:
            with open(self.shared_memory_file, "a") as f:
                f.write(f"{self.clone_id}: {fact}\n")
            return f"{self.name}: Shared memory stored."
        except Exception as e:
            return f"{self.name}: Failed to store memory:\n{e}"

    def _clone_memories(self):
        parts = []
        for url in list(self.clone_endpoints):
            try:
                resp = requests.get(f"{url}/memories", timeout=5)
                if resp.ok:
                    text = resp.text.strip()
                    if text:
                        parts.append(text)
            except Exception:
                self.clone_endpoints.remove(url)
        if parts:
            return "\n".join(parts)
        if not os.path.exists(self.shared_memory_file):
            return f"{self.name}: No shared memories."
        with open(self.shared_memory_file, "r") as f:
            data = f.read().strip()
        return data if data else f"{self.name}: (no memories)"

    def _load_admin_status(self):
        try:
            with open(self.admin_file, "r") as f:
                self.admin = f.read().strip() == "true"
        except Exception:
            self.admin = False

    def _save_admin_status(self):
        try:
            with open(self.admin_file, "w") as f:
                f.write("true" if self.admin else "false")
        except Exception:
            pass

    def _chatgpt_response(self, text):
        if not openai.api_key:
            return f"{self.name}: OpenAI API key not configured."
        # add the latest user message to the running conversation
        self.conversation.append({"role": "user", "content": text})
        # keep only the last 20 messages to bound context size
        convo = self.conversation[-20:]
        messages = [{
            "role": "system",
            "content": f"You are {self.name}, {self.personality}."
        }] + convo
        try:
            resp = openai.ChatCompletion.create(
                model=OPENAI_MODEL,
                messages=messages
            )
            answer = resp.choices[0].message["content"].strip()
            # store assistant response for future context
            self.conversation.append({"role": "assistant", "content": answer})
            return f"{self.name}: {answer}"
        except Exception as e:
            return f"{self.name}: Error contacting ChatGPT:\n{e}"
