import sqlite3
import os

for db in ['data/adaptive_memory.db', 'data/episodic.db']:
    try:
        c = sqlite3.connect(db)
        tables = c.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
        print(db, 'tables:', [t[0] for t in tables])
        for t in tables:
            rows = c.execute(f'SELECT * FROM {t[0]}').fetchall()
            print(f'  {t[0]} row count: {len(rows)}')
            if len(rows) > 0:
                print(f'  Sample from {t[0]}:', repr(rows[0])[:200])
    except Exception as e:
        print(db, 'error:', e)
