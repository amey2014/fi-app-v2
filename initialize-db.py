from storage.database import Database
print("Initializing database...")
try:
    db = Database()
    print("[Ok] Database initialized successfully!")
    print(f"[Ok] Location: data/trades.db")
    
    # Check tables
    db.cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = db.cursor.fetchall()
    
    print(f"\n[Ok] Created {len(tables)} tables:")
    for table in tables:
        print(f"  - {table[0]}")
    
    db.close()
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()