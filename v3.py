import streamlit as st
import requests
import os

# -------------------------------
# Config
# -------------------------------
BACKEND_URL = st.secrets["BACKEND_URL"]  # Set in Streamlit secrets
# Example in secrets:
# BACKEND_URL="http://<EC2_PUBLIC_IP>:8000"

# -------------------------------
# Helper functions
# -------------------------------
def register_user(username, password):
    try:
        resp = requests.post(f"{BACKEND_URL}/auth/register/", json={"username": username, "password": password})
        return resp.json()
    except Exception as e:
        return {"error": str(e)}

def login_user(username, password):
    try:
        resp = requests.post(f"{BACKEND_URL}/auth/login/", json={"username": username, "password": password})
        if resp.status_code == 200:
            return resp.json()["token"]
        else:
            return None
    except:
        return None

def get_user_container(token):
    try:
        resp = requests.post(f"{BACKEND_URL}/register_user/", headers={"x-token": token})
        return resp.json()
    except:
        return {"error": "Could not connect to backend"}

# -------------------------------
# Admin endpoints
# -------------------------------
def admin_list_users(token):
    try:
        resp = requests.get(f"{BACKEND_URL}/admin/list_user/", headers={"x-token": token})
        return resp.json()
    except:
        return {"error": "Could not connect to backend"}

def admin_list_users_detailed(token):
    try:
        resp = requests.get(f"{BACKEND_URL}/admin/list_users_detailed/", headers={"x-token": token})
        return resp.json()
    except:
        return {"error": "Could not connect to backend"}

def admin_action(token, action, username):
    try:
        resp = requests.post(f"{BACKEND_URL}/admin/{action}/", headers={"x-token": token}, json={"username": username})
        return resp.json()
    except:
        return {"error": "Could not connect to backend"}

def admin_get_logs(token, username):
    try:
        resp = requests.get(f"{BACKEND_URL}/admin/container_logs/", headers={"x-token": token}, params={"username": username})
        return resp.json()
    except:
        return {"error": "Could not connect to backend"}

# -------------------------------
# Streamlit UI
# -------------------------------
st.set_page_config(page_title="SQL Lab", layout="wide")
st.title("SQL Lab")

# -------------------------------
# Menu: Login / Register
# -------------------------------
menu = ["Login", "Register"]
if "token" not in st.session_state:
    choice = st.sidebar.selectbox("Menu", menu)

    if choice == "Register":
        st.subheader("Create a new user")
        new_user = st.text_input("Username")
        new_password = st.text_input("Password", type="password")
        if st.button("Register"):
            result = register_user(new_user, new_password)
            if "error" in result:
                st.error(result["error"])
            else:
                st.success(result.get("message", "User registered"))

    elif choice == "Login":
        st.subheader("Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            token = login_user(username, password)
            if token:
                st.session_state["token"] = token
                st.session_state["username"] = username
                st.success(f"Logged in as {username}")
                st.experimental_rerun()
            else:
                st.error("Invalid credentials")

# -------------------------------
# After login
# -------------------------------
if "token" in st.session_state:
    token = st.session_state["token"]
    username = st.session_state["username"]

    st.sidebar.success(f"Logged in as {username}")

    # ---------------- Logout Button ----------------
    if st.sidebar.button("Logout"):
        st.session_state.pop("token")
        st.session_state.pop("username")
        st.success("Logged out successfully")
        st.experimental_rerun()

    # Detect admin
    is_admin = username == "admin"

    if not is_admin:
        st.subheader("User Dashboard")
        st.write(f"Hello {username}! Manage your MySQL container below:")

        if st.button("Start / Get MySQL Container"):
            result = get_user_container(token)
            if "host_port" in result:
                st.success(f"MySQL container running on port: {result['host_port']}")
            else:
                st.info(result.get("message", str(result)))

    else:
        st.subheader("Admin Dashboard")
        st.write(f"Hello {username}! You have full control over users and containers.")

        # Tabs for admin actions
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
