import math
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from backend.database import get_connection

# ── Helpers ─────────────────────────────────────────────────────────────────

def _haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
         * math.sin(dlon / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def _text_similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    try:
        v = TfidfVectorizer().fit([a, b])
        t = v.transform([a, b])
        return float(cosine_similarity(t[0], t[1])[0][0])
    except Exception:
        return 0.0

# ── CRUD ─────────────────────────────────────────────────────────────────────

def post_item(title, category, description, status, image_url, lat, lng, user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO items (title, category, description, status, imageUrl, lat, lng, userId) VALUES (?,?,?,?,?,?,?,?)",
        (title, category, description, status, image_url, lat, lng, user_id)
    )
    conn.commit()
    item_id = c.lastrowid
    conn.close()
    return item_id

def get_all_items(status_filter=None, category_filter=None):
    conn = get_connection()
    c = conn.cursor()
    query = "SELECT i.*, u.name as ownerName, u.email as ownerEmail FROM items i JOIN users u ON i.userId = u.id WHERE 1=1"
    params = []
    if status_filter:
        query += " AND i.status = ?"
        params.append(status_filter)
    if category_filter and category_filter != "All":
        query += " AND i.category = ?"
        params.append(category_filter)
    query += " ORDER BY i.id DESC"
    rows = c.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_items_by_user(user_id):
    conn = get_connection()
    c = conn.cursor()
    rows = c.execute(
        "SELECT * FROM items WHERE userId = ? ORDER BY id DESC", (user_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_item_by_id(item_id):
    conn = get_connection()
    c = conn.cursor()
    row = c.execute(
        "SELECT i.*, u.name as ownerName, u.email as ownerEmail, u.phone as ownerPhone "
        "FROM items i JOIN users u ON i.userId = u.id WHERE i.id = ?",
        (item_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None

def mark_resolved(item_id, user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "UPDATE items SET resolved = 1 WHERE id = ? AND userId = ?",
        (item_id, user_id)
    )
    conn.commit()
    conn.close()

def delete_item(item_id, user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM items WHERE id = ? AND userId = ?", (item_id, user_id))
    conn.commit()
    conn.close()

# ── AI Matching ───────────────────────────────────────────────────────────────

def find_matches(query_item: dict, threshold: float = 0.25):
    """
    Given a lost item, find found items with similar descriptions (and vice versa).
    Returns list of (item, similarity_score) sorted by score desc.
    """
    opposite_status = "found" if query_item["status"] == "lost" else "lost"
    candidates = get_all_items(status_filter=opposite_status)

    results = []
    query_text = f"{query_item['title']} {query_item['description']} {query_item['category']}"

    for c in candidates:
        if c["resolved"]:
            continue
        cand_text = f"{c['title']} {c['description']} {c['category']}"
        score = _text_similarity(query_text, cand_text)

        # Boost score if locations are close (within 10 km)
        if query_item.get("lat") and query_item.get("lng") and c.get("lat") and c.get("lng"):
            dist = _haversine(query_item["lat"], query_item["lng"], c["lat"], c["lng"])
            if dist < 10:
                score += 0.2

        if score >= threshold:
            results.append((c, round(score, 3)))

    return sorted(results, key=lambda x: x[1], reverse=True)

# ── Messages ──────────────────────────────────────────────────────────────────

def send_message(sender_id, receiver_id, item_id, message):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO messages (senderId, receiverId, itemId, message) VALUES (?,?,?,?)",
        (sender_id, receiver_id, item_id, message)
    )
    conn.commit()
    conn.close()

def get_messages_for_user(user_id):
    conn = get_connection()
    c = conn.cursor()
    rows = c.execute(
        """SELECT m.*, 
                  s.name as senderName, 
                  r.name as receiverName,
                  i.title as itemTitle
           FROM messages m
           JOIN users s ON m.senderId   = s.id
           JOIN users r ON m.receiverId = r.id
           LEFT JOIN items i ON m.itemId = i.id
           WHERE m.senderId = ? OR m.receiverId = ?
           ORDER BY m.timestamp DESC""",
        (user_id, user_id)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_nearby_items(lat, lng, radius_km=5):
    all_items = get_all_items()
    results = []
    for item in all_items:
        if item.get("lat") and item.get("lng"):
            dist = _haversine(lat, lng, item["lat"], item["lng"])
            if dist <= radius_km:
                item["distance_km"] = round(dist, 2)
                results.append(item)
    return sorted(results, key=lambda x: x["distance_km"])
