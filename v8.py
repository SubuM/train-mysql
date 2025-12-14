import streamlit as st
import requests
import mysql.connector

# -------------------------------
# Config
# -------------------------------
BACKEND_URL = st.secrets["BACKEND_URL"]
TABLE_PREVIEW_LIMIT = 20

# -------------------------------
# Backend API helpers
# -------------------------------
def register_user(username, password):
    r = requests.post(
        f"{BACKEND_URL}/auth/register/",
        json={"username": username, "password": password}
    )
    return r.json()

def login_user(username, password):
    r = requests.post(
        f"{BACKEND_URL}/auth/login/",
        json={"username": username, "password": password}
    )
    if r.status_code == 200:
        return r.json()["token"]
    return None

def get_container_info(token):
    r = requests.post(
        f"{BACKEND_URL}/register_user/",
        headers={"x-token": token}
    )
    return r.json()

# -------------------------------
# MySQL helpers (IMPORTANT FIXES)
# -------------------------------
def mysql_connect(info, database=None):
    return mysql.connector.connect(
        host=info["host"],
        port=info["port"],
        user=info["user"],
        password=info["password"],
        database=database or info["database"],
        autocommit=True
    )

def run_sql(info, sql):
    try:
        conn = mysql_connect(info)
        cur = conn.cursor()
        cur.execute(sql)

        if cur.with_rows:
            rows = cur.fetchall()
            cols = [c[0] for c in cur.description]
            return {"type": "table", "rows": rows, "columns": cols}
        else:
            return {"type": "message", "message": f"{cur.rowcount} rows affected"}
    except Exception as e:
        return {"type": "error", "message": str(e)}

def list_databases(info):
    conn = mysql_connect(info)
    cur = conn.cursor()
    cur.execute("SHOW DATABASES")
    return [r[0] for r in cur.fetchall()]

def list_tables(info, db):
    conn = mysql_connect(info, db)
    cur = conn.cursor()
    cur.execute("SHOW TABLES")
    return [r[0] for r in cur.fetchall()]

def describe_table(info, db, table):
    conn = mysql_connect(info, db)
    cur = conn.cursor()
    cur.execute(f"DESCRIBE `{table}`")
    return cur.fetchall()

def preview_table(info, db, table):
    conn = mysql_connect(info, db)
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM `{table}` LIMIT {TABLE_PREVIEW_LIMIT}")
    rows = cur.fetchall()
    cols = [c[0] for c in cur.description]
    return rows, cols

# -------------------------------
# UI Setup
# -------------------------------
st.set_page_config("SQL Lab", layout="wide")
st.title("🧪 SQL Lab")

# -------------------------------
# Session State
# -------------------------------
for key in ["token", "username", "container"]:
    st.session_state.setdefault(key, None)

# -------------------------------
# Login / Register
# -------------------------------
if not st.session_state.token:
    choice = st.sidebar.selectbox("Menu", ["Login", "Register"])

    if choice == "Register":
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.button("Register"):
            res = register_user(u, p)
            st.success(res.get("message", res))

    if choice == "Login":
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.button("Login"):
            token = login_user(u, p)
            if token:
                st.session_state.token = token
                st.session_state.username = u
                st.experimental_rerun()
            else:
                st.error("Invalid credentials")

# -------------------------------
# Dashboard
# -------------------------------
if st.session_state.token:
    st.sidebar.success(f"Logged in as {st.session_state.username}")
    if st.sidebar.button("Logout"):
        st.session_state.token = None
        st.session_state.container = None
        st.experimental_rerun()

    # Load container info ONCE
    if not st.session_state.container:
        st.session_state.container = get_container_info(st.session_state.token)

    info = st.session_state.container

    st.success(
        f"Connected to MySQL at `{info['host']}:{info['port']}`\n\n"
        f"User: `{info['user']}` | DB: `{info['database']}`"
    )

    # ---------------- SQL Console ----------------
    st.subheader("🧠 SQL Console")
    sql = st.text_area("Enter SQL", height=200)
    if st.button("Run"):
        res = run_sql(info, sql)
        if res["type"] == "table":
            st.dataframe(res["rows"], columns=res["columns"])
        elif res["type"] == "message":
            st.success(res["message"])
        else:
            st.error(res["message"])

    # ---------------- Schema Explorer ----------------
    st.subheader("📂 Schema Explorer")
    dbs = list_databases(info)
    db = st.selectbox("Database", dbs, index=dbs.index(info["database"]))

    tables = list_tables(info, db)
    table = st.selectbox("Table", tables)

    if table:
        st.write("Columns:")
        st.table(describe_table(info, db, table))

        st.write("Preview:")
        rows, cols = preview_table(info, db, table)
        st.dataframe(rows, columns=cols)
