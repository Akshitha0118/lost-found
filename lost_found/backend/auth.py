import hashlib
from backend.database import get_connection

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def register_user(name, email, password, phone="", city=""):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute(
            "INSERT INTO users (name, email, password, phone, city) VALUES (?, ?, ?, ?, ?)",
            (name, email, hash_password(password), phone, city)
        )
        conn.commit()
        user = c.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        return dict(user), None
    except Exception as e:
        return None, str(e)
    finally:
        conn.close()

def login_user(email, password):
    conn = get_connection()
    c = conn.cursor()
    user = c.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    if user and user["password"] == hash_password(password):
        return dict(user), None
    return None, "Invalid email or password"

def get_user_by_id(user_id):
    conn = get_connection()
    c = conn.cursor()
    user = c.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(user) if user else None

def update_user_profile(user_id, name, phone, city):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "UPDATE users SET name = ?, phone = ?, city = ? WHERE id = ?",
        (name, phone, city, user_id)
    )
    conn.commit()
    conn.close()
    return get_user_by_id(user_id)

def get_all_users():
    conn = get_connection()
    c = conn.cursor()
    users = c.execute("SELECT id, name, email, phone, city, joined FROM users").fetchall()
    conn.close()
    return [dict(u) for u in users]
