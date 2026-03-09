"""
PPAI — inicializador de base de datos
Ejecutar una vez desde la raíz del proyecto:
    python3 db/init_db.py

Crea ppai.db con el schema completo definido en db/schema.sql
"""
import sqlite3
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA_PATH = os.path.join(BASE_DIR, "db", "schema.sql")
DB_PATH = os.path.join(BASE_DIR, "ppai.db")

def init():
    if os.path.exists(DB_PATH) and os.path.getsize(DB_PATH) > 0:
        print(f"ℹ️  La base de datos ya existe: {DB_PATH}")
        print("   Usá --force para recrearla desde cero.")
        return

    with open(SCHEMA_PATH, "r") as f:
        schema = f.read()

    conn = sqlite3.connect(DB_PATH)
    conn.executescript(schema)
    conn.commit()

    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()]
    conn.close()

    print(f"✅ Base de datos creada: {DB_PATH}")
    print("📋 Tablas:")
    for t in tables:
        if t != "sqlite_sequence":
            conn2 = sqlite3.connect(DB_PATH)
            cols = [r[1] for r in conn2.execute(f"PRAGMA table_info({t})").fetchall()]
            conn2.close()
            print(f"   {t:25s} → {len(cols)} columnas")

if __name__ == "__main__":
    force = "--force" in sys.argv
    if force and os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print("⚠️  Base de datos anterior eliminada.")
    init()
