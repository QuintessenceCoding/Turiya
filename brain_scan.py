# brain_scan.py
import sqlite3
import os

DB_PATH = os.path.join('sns2f_framework', 'data', 'sns2f_memory.sqlite')

def scan():
    if not os.path.exists(DB_PATH):
        print("No Brain Found.")
        return

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 1. Total Volume
    count = c.execute("SELECT COUNT(*) FROM symbolic_knowledge").fetchone()[0]
    
    # 2. Concept Density (How connected are the nodes?)
    # We count how many subjects have more than 5 facts
    density = c.execute("""
        SELECT COUNT(*) FROM (
            SELECT subject, COUNT(*) as cnt 
            FROM symbolic_knowledge 
            GROUP BY subject 
            HAVING cnt >= 5
        )
    """).fetchone()[0]

    print(f"\n🧠 TURIYA BRAIN SCAN")
    print(f"====================")
    print(f"Total Facts (Synapses):  {count}")
    print(f"Dense Concepts (Nodes):  {density}")
    print(f"====================")

    if count < 5000:
        print("❌ STATUS: INFANT. Keep crawling. Too sparse for evolution.")
    elif count < 10000:
        print("⚠️ STATUS: TODDLER. Capable of simple logic, but weak abstraction.")
    else:
        if density > 500:
            print("✅ STATUS: CHILD. Ready for Cognitive Evolution.")
        else:
            print("⚠️ STATUS: FRAGMENTED. Lots of data, but not enough connections.")
            print("   Tip: Stop random crawling. Pick specific topics and dive deep.")

    conn.close()

if __name__ == "__main__":
    scan()