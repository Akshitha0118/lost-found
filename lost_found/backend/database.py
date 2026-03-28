import sqlite3
import os

DB_PATH = os.getenv("DB_PATH", "lost_found.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row  # allows dict-like access
    return conn

def init_db():
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            name     TEXT    NOT NULL,
            email    TEXT    NOT NULL UNIQUE,
            password TEXT    NOT NULL,
            phone    TEXT,
            city     TEXT,
            joined   TEXT    DEFAULT (datetime('now'))
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT    NOT NULL,
            category    TEXT,
            description TEXT,
            status      TEXT    CHECK(status IN ('lost','found')),
            imageUrl    TEXT,
            lat         REAL,
            lng         REAL,
            userId      INTEGER NOT NULL,
            createdAt   TEXT    DEFAULT (datetime('now')),
            resolved    INTEGER DEFAULT 0,
            FOREIGN KEY (userId) REFERENCES users(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            senderId   INTEGER NOT NULL,
            receiverId INTEGER NOT NULL,
            itemId     INTEGER,
            message    TEXT    NOT NULL,
            timestamp  TEXT    DEFAULT (datetime('now')),
            FOREIGN KEY (senderId)   REFERENCES users(id),
            FOREIGN KEY (receiverId) REFERENCES users(id),
            FOREIGN KEY (itemId)     REFERENCES items(id)
        )
    """)

    conn.commit()
    conn.close()
