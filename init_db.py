import sqlite3

def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # Create Users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT DEFAULT 'STUDENT'
    )
    ''')

    # Create Reports table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        type TEXT NOT NULL, -- 'LOST' or 'FOUND'
        item_name TEXT NOT NULL,
        category TEXT NOT NULL,
        description TEXT NOT NULL,
        location TEXT NOT NULL,
        date_item TEXT NOT NULL,
        image_path TEXT NOT NULL,
        status TEXT DEFAULT 'PENDING',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES Users(id)
    )
    ''')

    # Create MatchResults table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS MatchResults (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lost_report_id INTEGER NOT NULL,
        found_report_id INTEGER NOT NULL,
        score REAL NOT NULL,
        FOREIGN KEY (lost_report_id) REFERENCES Reports(id),
        FOREIGN KEY (found_report_id) REFERENCES Reports(id)
    )
    ''')

    # Insert initial hardcoded users
    users = [
        ('BIT2025077', '12122007', 'STUDENT'),
        ('BIT2025075', '25042008', 'STUDENT'),
        ('MCET', 'MCET12345', 'ADMIN')
    ]
    
    for username, password, role in users:
        try:
            cursor.execute('INSERT INTO Users (username, password, role) VALUES (?, ?, ?)', (username, password, role))
        except sqlite3.IntegrityError:
            pass # User already exists

    conn.commit()
    conn.close()
    print("Database initialized successfully.")

if __name__ == '__main__':
    init_db()
