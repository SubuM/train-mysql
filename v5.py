import streamlit as st
import requests
import mysql.connector
import re

# -------------------------------
# Config
# -------------------------------
BACKEND_URL = st.secrets["BACKEND_URL"]

# -------------------------------
# Helper functions: Backend API
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
# Helper function: SQL console
# -------------------------------
def run_sql_query(host, port, sql):
    try:
        conn = mysql.connector.connect(
            host=host,
            port=port,
            user="root",
            password="rootpassword"
        )
        cursor = conn.cursor()
        cursor.execute(sql)

        if cursor.with_rows:
            rows = cursor.fetchall()
            cols = [desc[0] for desc in cursor.description]
            return {"type": "table", "columns": cols, "rows": rows}
        else:
            conn.commit()
            return {"type": "message", "message": f"{cursor.rowcount} rows affected."}
    except Exception as e:
        return {"type": "error", "message": str(e)}

# -------------------------------
# Streamlit UI
# -------------------------------
st.set_page_config(page_title="SQL Lab", layout="wide")
st.title("SQL Lab")

# -------------------------------
# Session state initialization
# -------------------------------
if "token" not in st.session_state:
    st.session_state["token"] = None
if "username" not in st.session_state:
    st.session_state["username"] = None
if "container_info" not in st.session_state:
    st.session_state["container_info"] = None

# -------------------------------
# Login / Register Menu
# -------------------------------
if st.session_state["token"] is None:
    menu = ["Login", "Register"]
    choice = st.sidebar.selectbox("Menu", menu)

    if choice == "Register":
        st.subheader("Create a new user")
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
# Logged-in dashboard
# -------------------------------
if st.session_state["token"]:
    token = st.session_state["token"]
    username = st.session_state["username"]

    st.sidebar.success(f"Logged in as {username}")
    if st.sidebar.button("Logout"):
        st.session_state["token"] = None
        st.session_state["username"] = None
        st.session_state["container_info"] = None
        st.info("Logged out successfully")
        st.experimental_rerun()  # this still works for navigation; otherwise refresh page manually

    is_admin = username == "admin"

    # -------------------------------
    # User dashboard (non-admin)
    # -------------------------------
    if not is_admin:
        st.subheader("User Dashboard")
        st.write(f"Hello {username}! Manage your MySQL container below:")

        # Fetch container info if not already fetched
        if st.session_state["container_info"] is None:
            st.session_state["container_info"] = get_user_container(token)

        container_info = st.session_state["container_info"]

        # Determine host port
        host_port = None
        if "host_port" in container_info:
            host_port = container_info["host_port"]
        elif "message" in container_info:
            m = re.search(r"port (\d+)", container_info["message"])
            if m:
                host_port = int(m.group(1))

        if host_port:
            st.success(f"MySQL container running on port: {host_port}")

            # SQL Console
            st.subheader("SQL Console")
            sql_query = st.text_area("Enter SQL query", height=200)
            if st.button("Run SQL Query"):
                result = run_sql_query(
                    host="51.20.117.249",  # Replace with your host if needed
                    port=host_port,
                    sql=sql_query
                )
                if result["type"] == "table":
                    st.dataframe(result["rows"], columns=result["columns"])
                elif result["type"] == "message":
                    st.success(result["message"])
                else:
                    st.error(result["message"])
        else:
            st.info(container_info.get("message", str(container_info)))
            if st.button("Start MySQL Container"):
                st.session_state["container_info"] = get_user_container(token)

    # -------------------------------
    # Admin dashboard
    # -------------------------------
    else:
        st.subheader("Admin Dashboard")
        st.write(f"Hello {username}! Manage users and containers.")

        tabs = st.tabs(["List Users", "User Details", "Manage Containers", "View Logs"])

        # ---------------- List Users ----------------
        with tabs[0]:
            st.write("List of all users:")
            users = admin_list_users(token).get("users", [])
            st.write(users)

        # ---------------- User Details ----------------
        with tabs[1]:
            st.write("Detailed info for all users:")
            details = admin_list_users_detailed(token)
            st.json(details)

        # ---------------- Manage Containers ----------------
        with tabs[2]:
            st.write("Manage user containers")
            target_user = st.selectbox("Select user", [u for u in users if u != "admin"])
            actions = ["start_user", "stop_user", "restart_user", "suspend_user", "unsuspend_user", "delete_user"]
            action = st.selectbox("Action", actions)
            if st.button("Execute"):
                result = admin_action(token, action, target_user)
                st.write(result)

        # ---------------- View Logs ----------------
        with tabs[3]:
            st.write("View container logs")
            log_user = st.selectbox("Select user for logs", [u for u in users if u != "admin"], key="loguser")
            if st.button("Show Logs"):
                logs = admin_get_logs(token, log_user)
                if "logs" in logs:
                    st.code(logs["logs"])
                else:
                    st.write(logs)
