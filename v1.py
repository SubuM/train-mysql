import streamlit as st
import requests

# -------------------------------
# Config
# -------------------------------
BACKEND_URL = st.secrets["BACKEND_URL"]  # Set backend URL as secret in Streamlit

# -------------------------------
# Session State
# -------------------------------
if "token" not in st.session_state:
    st.session_state["token"] = None
if "username" not in st.session_state:
    st.session_state["username"] = None
if "is_admin" not in st.session_state:
    st.session_state["is_admin"] = False

# -------------------------------
# Helper functions
# -------------------------------
def register_user(username, password):
    try:
        r = requests.post(f"{BACKEND_URL}/auth/register/", data={"username": username, "password": password})
        if r.status_code == 200:
            st.success(r.json().get("message", "Registered"))
        else:
            st.error(r.json().get("detail", "Registration failed"))
    except Exception as e:
        st.error(f"Error: {e}")

def login_user(username, password):
    try:
        r = requests.post(f"{BACKEND_URL}/auth/login/", data={"username": username, "password": password})
        if r.status_code == 200:
            st.session_state.token = r.json()["token"]
            st.session_state.username = username
            st.session_state.is_admin = username == "admin"
            st.success("Logged in successfully")
        else:
            st.error(r.json().get("detail", "Login failed"))
    except Exception as e:
        st.error(f"Error: {e}")

def create_mysql_container():
    try:
        headers = {"x-token": st.session_state.token}
        r = requests.post(f"{BACKEND_URL}/register_user/", headers=headers)
        if r.status_code == 200:
            st.success(f"MySQL container ready! Connect on port {r.json().get('host_port')}")
        else:
            st.error(r.json().get("detail", "Failed to create container"))
    except Exception as e:
        st.error(f"Error: {e}")

def admin_action(endpoint, data=None, params=None):
    headers = {"x-token": st.session_state.token}
    try:
        if data:
            r = requests.post(f"{BACKEND_URL}/{endpoint}", headers=headers, data=data)
        else:
            r = requests.get(f"{BACKEND_URL}/{endpoint}", headers=headers, params=params)
        return r
    except Exception as e:
        st.error(f"Error: {e}")
        return None

# -------------------------------
# Layout
# -------------------------------
st.title("SQL Learning Platform")

# -------------------------------
# LOGIN / REGISTER
# -------------------------------
if st.session_state.token is None:
    st.subheader("Register")
    reg_user = st.text_input("Username", key="reg_user")
    reg_pass = st.text_input("Password", key="reg_pass", type="password")
    if st.button("Register"):
        register_user(reg_user, reg_pass)

    st.subheader("Login")
    login_user_input = st.text_input("Username", key="login_user")
    login_pass_input = st.text_input("Password", key="login_pass", type="password")
    if st.button("Login"):
        login_user(login_user_input, login_pass_input)

else:
    st.write(f"Logged in as: **{st.session_state.username}**")

    # -------------------------------
    # USER PANEL
    # -------------------------------
    if not st.session_state.is_admin:
        st.subheader("User Actions")
        if st.button("Create / Start MySQL Container"):
            create_mysql_container()

    # -------------------------------
    # ADMIN PANEL
    # -------------------------------
    if st.session_state.is_admin:
        st.subheader("Admin Panel")

        # List all users
        if st.button("List Users"):
            r = admin_action("admin/list_user/")
            if r:
                st.write(r.json())

        # List users detailed
        if st.button("List Users Detailed"):
            r = admin_action("admin/list_users_detailed/")
            if r:
                st.json(r.json())

        # Select user for actions
        r = admin_action("admin/list_user/")
        user_options = r.json().get("users", []) if r else []
        selected_user = st.selectbox("Select User", user_options)

        if selected_user:
            st.markdown(f"### Manage user: {selected_user}")

            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("Start Container"):
                    r = admin_action("admin/start_user/", data={"username": selected_user})
                    if r: st.success(r.json())

            with col2:
                if st.button("Stop Container"):
                    r = admin_action("admin/stop_user/", data={"username": selected_user})
                    if r: st.success(r.json())

            with col3:
                if st.button("Restart Container"):
                    r = admin_action("admin/restart_user/", data={"username": selected_user})
                    if r: st.success(r.json())

            col4, col5 = st.columns(2)
            with col4:
                if st.button("Suspend User"):
                    r = admin_action("admin/suspend_user/", data={"username": selected_user})
                    if r: st.success(r.json())

            with col5:
                if st.button("Unsuspend User"):
                    r = admin_action("admin/unsuspend_user/", data={"username": selected_user})
                    if r: st.success(r.json())

            if st.button("Delete User"):
                r = admin_action("admin/delete_user/", data={"username": selected_user})
                if r: st.success(r.json())

            if st.button("Show Container Logs"):
                r = admin_action("admin/container_logs/", params={"username": selected_user})
                if r:
                    st.text_area("Logs", value=r.json().get("logs", ""), height=300)

    if st.button("Logout"):
        st.session_state.token = None
        st.session_state.username = None
        st.session_state.is_admin = False
        st.experimental_rerun()
