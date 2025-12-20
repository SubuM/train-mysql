import streamlit as st
from streamlit_ace import st_ace
import pandas as pd
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
def run_sql_query(host, port, sql, database=None):
    try:
        conn = mysql.connector.connect(
            host=host,
            port=port,
            user="root",
            password=MYSQL_ROOT_PASSWORD,
            database=database if database else None
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
st.set_page_config(page_title="SQL Lab", page_icon="🔬", layout="wide")
st.title("🧪 SQL Lab")

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
        # Clear session state fully
        for key in [
            "token", "username", "container_info",
            "query_history", "selected_db",
            "login_user", "login_pass",
            "reg_user", "reg_pass",
        ]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

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

            # Ensure user database exists and is used
            user_db = username
            create_db_query = f"CREATE DATABASE IF NOT EXISTS `{user_db}`;"
            run_sql_query(BACKEND_IP, host_port, create_db_query)
            st.session_state["selected_db"] = user_db

            # Initialize query history if not exists
            if "query_history" not in st.session_state:
                st.session_state["query_history"] = []

            # ------------------ ACE Editor Theme Selector ------------------
            # List of popular Ace editor themes
            ace_themes = [
                "dracula",
                "monokai",
                "github",
                "tomorrow",
                "twilight",
                "xcode",
                "solarized_dark",
                "solarized_light",
                "terminal"
            ]

            # Dropdown to let user pick theme
            selected_theme = st.selectbox("Select ACE Editor Theme", ace_themes, index=0)

            # ACE editor for SQL queries
            sql_query = st_ace(
                value="",
                language="sql",
                theme=selected_theme,
                height=300,
                key="sql_editor",
                font_size=14,
                tab_size=4,
                show_gutter=True,
                show_print_margin=False,
                wrap=True,
                placeholder="Write your SQL query here...",
            )

            # Protected databases
            protected_dbs = ["mysql", "information_schema", "performance_schema", "sys", username]

            # Execute query only if new
            if sql_query.strip() and sql_query != st.session_state.get("last_executed_sql"):

                # Protect DROP DATABASE
                drop_db_match = re.match(r"^\s*DROP\s+DATABASE\s+`?(\w+)`?\s*;?\s*$", sql_query, re.IGNORECASE)
                if drop_db_match and drop_db_match.group(1) in protected_dbs:
                    st.error(f"Cannot drop protected database: `{drop_db_match.group(1)}`")
                else:
                    result = run_sql_query(
                        BACKEND_IP,
                        host_port,
                        sql_query,
                        st.session_state.get("selected_db")
                    )

                    # Append to query history
                    st.session_state["query_history"].append(sql_query)
                    st.session_state["last_executed_sql"] = sql_query

                    # Display results
                    if result["type"] == "table":
                        df = pd.DataFrame(result["rows"], columns=result["columns"])
                        st.dataframe(df, use_container_width=True)
                    elif result["type"] == "message":
                        st.success(result["message"])
                    else:
                        st.error(result["message"])

            # ---------------- Query History ----------------
            if st.session_state.get("query_history"):
                st.subheader("Query History")
                for i, q in enumerate(reversed(st.session_state["query_history"]), 1):
                    st.code(f"{i}: {q}", language="sql")



            # ---------------- Database Schema Explorer ----------------
            st.subheader("Database Schema Explorer")
            dbs = get_databases(BACKEND_IP, host_port)
            st.session_state["selected_db"] = st.selectbox(
                "Select Database",
                dbs,
                index=0 if dbs else None
            )

            if st.session_state["selected_db"]:
                selected_db = st.session_state["selected_db"]
                tables = get_tables(BACKEND_IP, host_port, selected_db)
                selected_table = st.selectbox("Select Table", tables)
                if selected_table:
                    columns = get_columns(BACKEND_IP, host_port, selected_db, selected_table)
                    st.write(f"Columns in `{selected_table}`:")
                    st.write(columns)
                    # Table preview
                    st.write(f"Preview of `{selected_table}` (first {TABLE_PREVIEW_LIMIT} rows):")
                    rows, cols = preview_table(BACKEND_IP, host_port, selected_db, selected_table)
                    if rows is not None:
                        df = pd.DataFrame(rows, columns=cols)
                        st.dataframe(df, use_container_width=True)
                    else:
                        st.error(cols)

        else:
            st.info(container_info.get("message", str(container_info)))
            if st.button("Start MySQL Container"):
                st.session_state["container_info"] = get_user_container(token)

    else:
        # ---------------- Admin Dashboard ----------------
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
