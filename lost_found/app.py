import os
import streamlit as st
import folium
from streamlit_folium import st_folium
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv

from backend.database import init_db
from backend.auth import (
    register_user, login_user, update_user_profile, get_all_users
)
from backend.items import (
    post_item, get_all_items, get_items_by_user,
    get_item_by_id, mark_resolved, delete_item,
    find_matches, send_message, get_messages_for_user,
    get_nearby_items
)

# ── Bootstrap ─────────────────────────────────────────────────────────────────
load_dotenv()
init_db()

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME", ""),
    api_key=os.getenv("CLOUDINARY_API_KEY", ""),
    api_secret=os.getenv("CLOUDINARY_API_SECRET", "")
)

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="Lost & Found AI", page_icon="🔍", layout="wide")

st.markdown("""
<style>
.main { background: linear-gradient(135deg, #f0f9ff, #e0f2fe, #f8fafc); }
.stButton>button { border-radius: 8px; font-weight: 600; }
.item-card {
    background: white;
    border-radius: 12px;
    padding: 1rem;
    margin-bottom: 1rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}
</style>
""", unsafe_allow_html=True)

# ── Session defaults ──────────────────────────────────────────────────────────
for key, val in {"user": None, "page": "home", "selected_item_id": None}.items():
    if key not in st.session_state:
        st.session_state[key] = val

# ── Helpers ───────────────────────────────────────────────────────────────────
CATEGORIES = ["Electronics", "Wallet", "Bag", "Keys", "Documents", "Jewellery", "Pet", "Other"]

def upload_image(file):
    if file and os.getenv("CLOUDINARY_CLOUD_NAME"):
        result = cloudinary.uploader.upload(file)
        return result.get("secure_url", "")
    return ""

# ═══════════════════════════════════════════════════════════════════════════════
# AUTH PAGES
# ═══════════════════════════════════════════════════════════════════════════════

def page_register():
    st.subheader("📝 Create Account")

    name     = st.text_input("Full Name")
    email    = st.text_input("Email")
    phone    = st.text_input("Phone (optional)")
    city     = st.text_input("City (optional)")
    password = st.text_input("Password", type="password")
    confirm  = st.text_input("Confirm Password", type="password")

    if st.button("Register", use_container_width=True):
        if not name or not email or not password:
            st.error("Name, email and password are required.")
        elif password != confirm:
            st.error("Passwords do not match.")
        else:
            user, err = register_user(name, email, password, phone, city)
            if err:
                st.error(f"Registration failed: {err}")
            else:
                st.session_state.user = user
                st.success("Account created! Welcome 🎉")
                st.rerun()

def page_login():
    st.subheader("🔐 Login")
    email    = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Login", use_container_width=True):
        user, err = login_user(email, password)
        if err:
            st.error(err)
        else:
            st.session_state.user = user
            st.success(f"Welcome back, {user['name']}!")
            st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN PAGES (authenticated)
# ═══════════════════════════════════════════════════════════════════════════════

def page_post():
    st.subheader("📤 Post a Lost / Found Item")
    col1, col2 = st.columns(2)
    with col1:
        title       = st.text_input("Item Title")
        category    = st.selectbox("Category", CATEGORIES)
        status      = st.radio("Status", ["lost", "found"], horizontal=True)
    with col2:
        description = st.text_area("Description", height=120)
        image       = st.file_uploader("Upload Photo", type=["jpg", "jpeg", "png"])

    st.markdown("**📍 Click map to set location**")
    m    = folium.Map(location=[20, 78], zoom_start=5)
    data = st_folium(m, height=300, use_container_width=True)

    lat = lng = None
    if data and data.get("last_clicked"):
        lat = data["last_clicked"]["lat"]
        lng = data["last_clicked"]["lng"]
        st.success(f"Location set: {lat:.4f}, {lng:.4f}")

    if st.button("Submit Item", use_container_width=True, type="primary"):
        if not title:
            st.error("Title is required.")
        else:
            img_url  = upload_image(image)
            item_id  = post_item(title, category, description, status, img_url, lat, lng,
                                 st.session_state.user["id"])
            st.success(f"✅ Item posted! ID: #{item_id}")

            # AI match suggestions
            new_item = get_item_by_id(item_id)
            matches  = find_matches(new_item)
            if matches:
                st.info(f"🤖 AI found {len(matches)} potential match(es):")
                for m_item, score in matches[:3]:
                    with st.expander(f"🔗 {m_item['title']} — score {score}"):
                        st.write(m_item.get("description", ""))
                        if m_item.get("imageUrl"):
                            st.image(m_item["imageUrl"], width=200)
                        st.caption(f"Posted by: {m_item.get('ownerName')} | {m_item.get('ownerEmail')}")


def page_browse():
    st.subheader("🔎 Browse All Items")

    col1, col2, col3 = st.columns(3)
    with col1:
        status_f   = st.selectbox("Status", ["All", "lost", "found"])
    with col2:
        cat_f      = st.selectbox("Category", ["All"] + CATEGORIES)
    with col3:
        search_q   = st.text_input("Search keyword")

    status_filter = None if status_f == "All" else status_f
    items = get_all_items(status_filter=status_filter, category_filter=cat_f)

    if search_q:
        items = [i for i in items
                 if search_q.lower() in i["title"].lower()
                 or search_q.lower() in (i.get("description") or "").lower()]

    st.caption(f"{len(items)} item(s) found")

    for item in items:
        resolved_tag = "✅ Resolved" if item["resolved"] else ""
        status_color = "🔴" if item["status"] == "lost" else "🟢"

        with st.container():
            st.markdown(f"<div class='item-card'>", unsafe_allow_html=True)
            c1, c2 = st.columns([1, 3])
            with c1:
                if item.get("imageUrl"):
                    st.image(item["imageUrl"], width=140)
                else:
                    st.markdown("🖼️ No image")
            with c2:
                st.markdown(f"### {status_color} {item['title']} {resolved_tag}")
                st.caption(f"📁 {item['category']} | 🕐 {item['createdAt'][:10]}")
                st.write(item.get("description", ""))
                st.caption(f"👤 {item['ownerName']} · {item['ownerEmail']}")

                col_a, col_b = st.columns(2)
                with col_a:
                    if st.button("📨 Contact", key=f"contact_{item['id']}"):
                        st.session_state.selected_item_id = item["id"]
                        st.session_state.page = "message"
                        st.rerun()
                with col_b:
                    if st.button("🔍 AI Matches", key=f"match_{item['id']}"):
                        st.session_state.selected_item_id = item["id"]
                        st.session_state.page = "matches"
                        st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)


def page_map():
    st.subheader("🗺️ Items on Map")
    m = folium.Map(location=[20, 78], zoom_start=5)
    items = get_all_items()

    for item in items:
        if item.get("lat") and item.get("lng"):
            color = "red" if item["status"] == "lost" else "green"
            folium.Marker(
                [item["lat"], item["lng"]],
                popup=f"<b>{item['title']}</b><br>{item['status'].upper()}<br>{item['ownerName']}",
                icon=folium.Icon(color=color, icon="search", prefix="fa")
            ).add_to(m)

    st_folium(m, height=550, use_container_width=True)
    st.caption("🔴 Lost  |  🟢 Found")


def page_nearby():
    st.subheader("📍 Items Near You")
    radius = st.slider("Search radius (km)", 1, 50, 5)

    m    = folium.Map(location=[20, 78], zoom_start=5)
    data = st_folium(m, height=300, use_container_width=True)

    if data and data.get("last_clicked"):
        ulat = data["last_clicked"]["lat"]
        ulng = data["last_clicked"]["lng"]
        st.info(f"Searching around: {ulat:.4f}, {ulng:.4f}")

        nearby = get_nearby_items(ulat, ulng, radius)
        st.caption(f"Found {len(nearby)} item(s) within {radius} km")
        for item in nearby:
            st.markdown(f"**{item['title']}** — {item['status']} — 📏 {item['distance_km']} km")
    else:
        st.info("Click on the map to set your location.")


def page_my_items():
    st.subheader("📋 My Posted Items")
    items = get_items_by_user(st.session_state.user["id"])

    if not items:
        st.info("You haven't posted any items yet.")
        return

    for item in items:
        with st.expander(f"{'✅' if item['resolved'] else '🔄'} {item['title']} [{item['status']}]"):
            st.write(item.get("description", ""))
            st.caption(f"Posted: {item['createdAt'][:10]}")
            if item.get("imageUrl"):
                st.image(item["imageUrl"], width=200)

            col1, col2 = st.columns(2)
            with col1:
                if not item["resolved"]:
                    if st.button("Mark Resolved ✅", key=f"res_{item['id']}"):
                        mark_resolved(item["id"], st.session_state.user["id"])
                        st.rerun()
            with col2:
                if st.button("Delete 🗑️", key=f"del_{item['id']}"):
                    delete_item(item["id"], st.session_state.user["id"])
                    st.rerun()


def page_messages():
    st.subheader("💬 Messages")
    selected_id = st.session_state.selected_item_id

    if selected_id:
        item = get_item_by_id(selected_id)
        if item:
            st.info(f"Contacting about: **{item['title']}** (owner: {item['ownerName']})")
            msg = st.text_area("Your message")
            if st.button("Send Message 📤"):
                send_message(st.session_state.user["id"], item["userId"], selected_id, msg)
                st.success("Message sent!")
                st.session_state.selected_item_id = None

    st.divider()
    st.markdown("**Inbox / Sent**")
    msgs = get_messages_for_user(st.session_state.user["id"])
    if not msgs:
        st.info("No messages yet.")
    for m in msgs:
        direction = "📤 Sent" if m["senderId"] == st.session_state.user["id"] else "📥 Received"
        st.markdown(f"**{direction}** | 🕐 {m['timestamp'][:16]} | Item: *{m.get('itemTitle', 'N/A')}*")
        st.write(m["message"])
        st.divider()


def page_ai_matches():
    item_id = st.session_state.selected_item_id
    if not item_id:
        st.warning("No item selected.")
        return

    item = get_item_by_id(item_id)
    st.subheader(f"🤖 AI Matches for: {item['title']}")
    matches = find_matches(item)

    if not matches:
        st.info("No similar items found yet.")
        return

    for m_item, score in matches:
        with st.expander(f"🔗 {m_item['title']} — Similarity: {score}"):
            c1, c2 = st.columns([1, 2])
            with c1:
                if m_item.get("imageUrl"):
                    st.image(m_item["imageUrl"], width=150)
            with c2:
                st.write(m_item.get("description", ""))
                st.caption(f"Owner: {m_item['ownerName']} | {m_item['ownerEmail']}")
                if st.button("Contact Owner", key=f"cm_{m_item['id']}"):
                    st.session_state.selected_item_id = m_item["id"]
                    st.session_state.page = "message"
                    st.rerun()


def page_profile():
    st.subheader("👤 My Profile")
    user = st.session_state.user

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Email:** {user['email']}")
        st.markdown(f"**Joined:** {user.get('joined', 'N/A')[:10]}")
    with col2:
        name  = st.text_input("Name",  value=user.get("name", ""))
        phone = st.text_input("Phone", value=user.get("phone", ""))
        city  = st.text_input("City",  value=user.get("city", ""))

    if st.button("Save Changes", type="primary"):
        updated = update_user_profile(user["id"], name, phone, city)
        st.session_state.user = updated
        st.success("Profile updated!")
        st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
# ROUTING
# ═══════════════════════════════════════════════════════════════════════════════

st.title("🔍 Lost & Found AI")

if st.session_state.user is None:
    # ── Guest sidebar ────────────────────────────────────────────────────────
    choice = st.sidebar.selectbox("Menu", ["Login", "Register"])
    if choice == "Login":
        page_login()
    else:
        page_register()

else:
    # ── Authenticated sidebar ─────────────────────────────────────────────────
    st.sidebar.success(f"👤 {st.session_state.user['name']}")
    st.sidebar.caption(st.session_state.user["email"])

    nav = st.sidebar.radio("Navigate", [
        "🏠 Home / Browse",
        "📤 Post Item",
        "🗺️ Map",
        "📍 Nearby",
        "📋 My Items",
        "💬 Messages",
        "👤 Profile"
    ])

    if st.sidebar.button("🚪 Logout"):
        st.session_state.user = None
        st.session_state.page = "home"
        st.rerun()

    # Override nav from internal page transitions
    if st.session_state.page == "message":
        page_messages()
        if st.button("← Back"):
            st.session_state.page = "home"
            st.rerun()
    elif st.session_state.page == "matches":
        page_ai_matches()
        if st.button("← Back"):
            st.session_state.page = "home"
            st.rerun()
    elif "Browse" in nav:
        page_browse()
    elif "Post" in nav:
        page_post()
    elif "Map" in nav:
        page_map()
    elif "Nearby" in nav:
        page_nearby()
    elif "My Items" in nav:
        page_my_items()
    elif "Messages" in nav:
        page_messages()
    elif "Profile" in nav:
        page_profile()