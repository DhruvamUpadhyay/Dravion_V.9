"""
DRAVION v.9 — Working Memory

Ephemeral in-process dict. Fastest tier. Lost on restart.
"""


class WorkingMemory:
    def __init__(self):
        self._state = {}

    def set(self, key: str, value):
        self._state[key] = value

    def get(self, key: str, default=None):
        return self._state.get(key, default)

    def clear(self):
        self._state.clear()


working_memory = WorkingMemory()
