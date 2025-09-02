import json
import os
from typing import List, Dict

class AgentManager:
    """Simple manager for storing lightweight agent descriptions.

    Agents are persisted to a JSON file so they survive restarts. Each
    agent has a ``name`` and ``description``. This class provides
    minimal functionality required by the user request.
    """

    def __init__(self, path: str = "agents.json") -> None:
        self.path = path
        self._agents: List[Dict[str, str]] = []
        self._load()

    def _load(self) -> None:
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    self._agents = json.load(f)
            except Exception:
                self._agents = []
        else:
            self._agents = []

    def _save(self) -> None:
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self._agents, f, indent=2)

    # Public API -------------------------------------------------------------
    def add_agent(self, name: str, description: str) -> None:
        """Add a new agent description and persist it."""
        self._agents.append({"name": name, "description": description})
        self._save()

    def list_agents(self) -> List[Dict[str, str]]:
        """Return the list of known agents."""
        return list(self._agents)
