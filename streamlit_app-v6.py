import streamlit as st
import requests
import mysql.connector
import re

# -------------------------------
# Config from secrets.toml
# -------------------------------
BACKEND_URL = st.secrets["BACKEND_URL"]
BACKEND_IP = st.secrets["BACKEND_IP"]
MYSQL_ROOT_PASSWORD = st.secrets["MYSQL_PASSWORD"]
TABLE_PREVIEW_LIMIT = 20      # Number of rows to show by default

# -------------------------------
# Backend API helpers
# -------------------------------
def register_user(username, password):
    try:
        resp = requests.post(
            f"{BACKEND_URL}/auth/register/",
            json={"username": username, "password": password}
        )
        return resp.json()
    except Exception as e:
        return {"error": str(e)}

def login_user(username, password):
    try:
        resp = requests.post(
            f"{BACKEND_URL}/auth/login/",
            json={"username": username, "password": password}
        )
        if resp.status_code == 200:
            return resp.json()["token"]
        else:
            return None
    except:
        return None

def get_user_container(token):
    try:
        resp = requests.post(
            f"{BACKEND_URL}/register_user/",
            headers={"x-token": token}
        )
        return resp.json()
    except:
        return {"error": "Could not connect to backend"}

def admin_list_users(token):
    try:
        resp = requests.get(
            f"{BACKEND_URL}/admin/list_user/",
            headers={"x-token": token}
        )
        return resp.json()
    except:
        return {"error": "Could not connect to backend"}

def admin_list_users_detailed(token):
    try:
        resp = requests.get(
            f"{BACKEND_URL}/admin/list_users_detailed/",
            headers={"x-token": token}
        )
        return resp.json()
    except:
        return {"error": "Could not connect to backend"}

def admin_action(token, action, username):
    try:
        resp = requests.post(
            f"{BACKEND_URL}/admin/{action}/",
            headers={"x-token": token},
            json={"username": username}
        )
        return resp.json()
    except:
        return {"error": "Could not connect to backend"}

def admin_get_logs(token, username):
    try:
        resp = requests.get(
            f"{BACKEND_URL}/admin/container_logs/",
            headers={"x-token": token},
            params={"username": username}
        )
        return resp.json()
    except:
        return {"error": "Could not connect to backend"}

# -------------------------------
# MySQL helpers
# -------------------------------
def run_sql_query(host, port, sql):
    try:
        conn = mysql.connector.connect(
            host=host,
            port=port,
            user="root",
            password=MYSQL_ROOT_PASSWORD
        )
        cursor = conn.cursor()
        cursor.execute(sql)

        if cursor.with_rows:
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            return {"type": "table", "columns": columns, "rows": rows}
        else:
            conn.commit()
            return {"type": "message", "message": f"{cursor.rowcount} rows affected."}
    except Exception as e:
        return {"type": "error", "message": str(e)}

def get_databases(host, port):
    try:
        conn = mysql.connector.connect(
            host=host,
            port=port,
            user="root",
            password=MYSQL_ROOT_PASSWORD
        )
        cursor = conn.cursor()
        cursor.execute("SHOW DATABASES;")
        return [row[0] for row in cursor.fetchall()]
    except:
        return []

def get_tables(host, port, db):
    try:
        conn = mysql.connector.connect(
            host=host,
            port=port,
            user="root",
            password=MYSQL_ROOT_PASSWORD,
            database=db
        )
        cursor = conn.cursor()
        cursor.execute("SHOW TABLES;")
        return [row[0] for row in cursor.fetchall()]
    except:
        return []

def get_columns(host, port, db, table):
    try:
        conn = mysql.connector.connect(
            host=host,
            port=port,
            user="root",
            password=MYSQL_ROOT_PASSWORD,
            database=db
        )
        cursor = conn.cursor()
        cursor.execute(f"DESCRIBE {table};")
        return [row[0] for row in cursor.fetchall()]
    except:
        return []

def preview_table(host, port, db, table, limit=TABLE_PREVIEW_LIMIT):
    try:
        conn = mysql.connector.connect(
            host=host,
            port=port,
            user="root",
            password=MYSQL_ROOT_PASSWORD,
            database=db
        )
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM {table} LIMIT {limit};")
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        return rows, columns
    except Exception as e:
        return None, str(e)

# -------------------------------
# Streamlit UI
# -------------------------------
st.set_page_config(page_title="SQL Lab", layout="wide")
st.title("SQL Lab")

# -------------------------------
# Session state
# -------------------------------
if "token" not in st.session_state:
    st.session_state["token"] = None
if "username" not in st.session_state:
    st.session_state["username"] = None
if "container_info" not in st.session_state:
    st.session_state["container_info"] = None
if "query_history" not in st.session_state:
    st.session_state["query_history"] = []

# -------------------------------
# Login/Register
# -------------------------------
if st.session_state["token"] is None:
    menu = ["Login", "Register"]
    choice = st.sidebar.selectbox("Menu", menu)

    if choice == "Register":
        st.subheader("Register a new user")
        new_user = st.text_input("Username", key="reg_user")
        new_password = st.text_input("Password", type="password", key="reg_pass")
        if st.button("Register"):
            result = register_user(new_user, new_password)
            if "error" in result:
                st.error(result["error"])
            else:
                st.success(result.get("message", "User registered"))
                st.info("You can now login from the sidebar.")

    elif choice == "Login":
        st.subheader("Login")
        username = st.text_input("Username", key="login_user")
        password = st.text_input("Password", type="password", key="login_pass")
        if st.button("Login"):
            token = login_user(username, password)
            if token:
                st.session_state["token"] = token
                st.session_state["username"] = username
                st.success(f"Logged in as {username}")
            else:
                st.error("Invalid credentials")

# -------------------------------
# Dashboard
# -------------------------------
if st.session_state["token"]:
    token = st.session_state["token"]
    username = st.session_state["username"]

    st.sidebar.success(f"Logged in as {username}")
    if st.sidebar.button("Logout"):
        st.session_state["token"] = None
        st.session_state["username"] = None
        st.session_state["container_info"] = None
        st.session_state["query_history"] = []
        st.experimental_rerun()

    is_admin = username == "admin"

    if not is_admin:
        st.subheader("User Dashboard")
        st.write(f"Hello {username}! Manage your MySQL container below:")

        # Fetch container info if not set
        if st.session_state["container_info"] is None:
            st.session_state["container_info"] = get_user_container(token)

        container_info = st.session_state["container_info"]

        # Get host port
        host_port = None
        if "host_port" in container_info:
            host_port = container_info["host_port"]
        elif "message" in container_info:
            m = re.search(r"port (\d+)", container_info["message"])
            if m:
                host_port = int(m.group(1))

        if host_port:
            st.success(f"MySQL container running on port: {host_port}")

            # ---------------- SQL Console ----------------
            st.subheader("SQL Console")
            sql_query = st.text_area("Enter SQL query", height=200)
            if st.button("Run SQL Query"):
                result = run_sql_query(BACKEND_IP, host_port, sql_query)
                st.session_state["query_history"].append(sql_query)
                if result["type"] == "table":
                    st.dataframe(result["rows"], columns=result["columns"])
                elif result["type"] == "message":
                    st.success(result["message"])
                else:
                    st.error(result["message"])

            # ---------------- Query History ----------------
            if st.session_state["query_history"]:
                st.subheader("Query History")
                for i, q in enumerate(reversed(st.session_state["query_history"]), 1):
                    st.code(f"{i}: {q}")

            # ---------------- Database Schema Explorer ----------------
            st.subheader("Database Schema Explorer")
            dbs = get_databases(BACKEND_IP, host_port)
            selected_db = st.selectbox("Select Database", dbs)
            if selected_db:
                tables = get_tables(BACKEND_IP, host_port, selected_db)
                selected_table = st.selectbox("Select Table", tables)
                if selected_table:
                    columns = get_columns(BACKEND_IP, host_port, selected_db, selected_table)
                    st.write(f"Columns in `{selected_table}`:")
                    st.write(columns)

                    # ---------------- Table Preview ----------------
                    st.write(f"Preview of `{selected_table}` (first {TABLE_PREVIEW_LIMIT} rows):")
                    rows, cols = preview_table(BACKEND_IP, host_port, selected_db, selected_table)
                    if rows is not None:
                        st.dataframe(rows, columns=cols)
                    else:
                        st.error(cols)

        else:
            st.info(container_info.get("message", str(container_info)))
            if st.button("Start MySQL Container"):
                st.session_state["container_info"] = get_user_container(token)

    else:
        st.subheader("Admin Dashboard")
        st.write(f"Hello {username}! Manage users and containers.")

        tabs = st.tabs(["List Users", "User Details", "Manage Containers", "View Logs"])

        with tabs[0]:
            st.write("List of all users:")
            users = admin_list_users(token).get("users", [])
            st.write(users)

        with tabs[1]:
            st.write("Detailed info for all users:")
            details = admin_list_users_detailed(token)
            st.json(details)

        with tabs[2]:
            st.write("Manage user containers")
            target_user = st.selectbox("Select user", [u for u in users if u != "admin"])
            actions = ["start_user", "stop_user", "restart_user", "suspend_user", "unsuspend_user", "delete_user"]
            action = st.selectbox("Action", actions)
            if st.button("Execute"):
                result = admin_action(token, action, target_user)
                st.write(result)

        with tabs[3]:
            st.write("View container logs")
            log_user = st.selectbox("Select user for logs", [u for u in users if u != "admin"], key="loguser")
            if st.button("Show Logs"):
                logs = admin_get_logs(token, log_user)
                if "logs" in logs:
                    st.code(logs["logs"])
                else:
                    st.write(logs)
