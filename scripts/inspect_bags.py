import sqlite3
import os
from pathlib import Path

def inspect(bag_root):
    bag_path = Path(bag_root)
    for db_file in bag_path.rglob("*.db3"):
        print("=" * 60)
        print(f"Bag file: {db_file}")
        print(f"Size: {db_file.stat().st_size / (1024*1024):.2f} MB")
        
        conn = sqlite3.connect(str(db_file))
        c = conn.cursor()
        
        c.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [r[0] for r in c.fetchall()]
        print(f"Tables: {tables}")
        
        if "topics" in tables:
            c.execute("SELECT id, name, type, serialization_format FROM topics;")
            print("Topics:")
            for tid, name, ttype, sformat in c.fetchall():
                c.execute("SELECT count(*) FROM messages WHERE topic_id = ?", (tid,))
                cnt = c.fetchone()[0]
                print(f"  [id={tid}] {name} | type={ttype} | format={sformat} | msgs={cnt}")
                
        conn.close()

if __name__ == "__main__":
    base = Path(r"c:\Users\GANGARI DHRUVAVEER\Downloads\prozect")
    inspect(base / "camera_bag")
    inspect(base / "pose_bag")

