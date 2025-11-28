# inspect_graph.py
import sqlite3
import os

DB_PATH = os.path.join('sns2f_framework', 'data', 'sns2f_memory.sqlite')

def view_graph():
    if not os.path.exists(DB_PATH):
        print("No database found.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("\n--- 🕸️ SNS²F KNOWLEDGE GRAPH (Symbolic Logic) ---")
    print(f"{'SUBJECT':<30} | {'PREDICATE':<20} | {'OBJECT'}")
    print("-" * 80)

    try:
        cursor.execute("SELECT subject, predicate, object FROM symbolic_knowledge ORDER BY id DESC LIMIT 20")
        rows = cursor.fetchall()
        
        if not rows:
            print("[Empty] No logic facts extracted yet.")
        
        for r in rows:
            # Truncate for clean printing
            s = (r[0][:28] + '..') if len(r[0]) > 28 else r[0]
            p = (r[1][:18] + '..') if len(r[1]) > 18 else r[1]
            o = (r[2][:30] + '..') if len(r[2]) > 30 else r[2]
            print(f"{s:<30} | {p:<20} | {o}")

    except Exception as e:
        print(f"Error reading DB: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    view_graph()