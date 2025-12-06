import sqlite3

conn = sqlite3.connect("stfoom.db")
cur = conn.cursor()

cur.execute("PRAGMA table_info(ventes)")
columns = cur.fetchall()

for col in columns:
    print(col)

conn.close()
