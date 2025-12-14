import streamlit as st
import requests
import pandas as pd
from sqlalchemy import create_engine
import pymysql

# -------------------------------
# Load secrets
# -------------------------------
BACKEND_URL = st.secrets["BACKEND_URL"]      # e.g. "http://<EC2_PUBLIC_IP>:8000"
BACKEND_IP = st.secrets["BACKEND_IP"]        # e.g. "<EC2_PUBLIC_IP>"
MYSQL_PASSWORD = st.secrets["MYSQL_PASSWORD"]
# -------------------------------

st.set_page_config(page_title="SQL Learning Platform", layout="wide")
st.title("🧪 SQL Learning Platform")

# -------------------------------
# Session state
# -------------------------------
if "token" not in st.session_state:
    st.session_state.token = None
if "username" not in st.session_state:
    st.session_state.username = None
if "host_port" not in st.session_state:
    st.session_state.host_port = None

# -------------------------------
# Navigation
# -------------------------------
menu = st.sidebar.radio("Navigation", ["Register", "Login", "SQL Workspace", "Admin Panel"])

# -------------------------------
# REGISTER
# -------------------------------
if menu == "Register":
    st.header("Create a New Account")

    reg_username = st.text_input("Choose a username")
    reg_password = st.text_input("Choose a password", type="password")

    if st.button("Register"):
        if reg_username.strip() == "" or reg_password.strip() == "":
            st.error("Username and password cannot be empty.")
        else:
            try:
                resp = requests.post(
                    f"{BACKEND_URL}/auth/register/",
                    data={"username": reg_username, "password": reg_password}
                )
                if resp.status_code == 200:
                    st.success("Account created successfully! Please login.")
                else:
                    st.error(resp.json())
            except Exception as e:
                st.error(f"Registration failed: {e}")

# -------------------------------
# LOGIN
# -------------------------------
elif menu == "Login":
    st.header("Login to Your Account")

    login_username = st.text_input("Username")
    login_password = st.text_input("Password", type="password")

    if st.button("Login"):
        try:
            resp = requests.post(
                f"{BACKEND_URL}/auth/login/",
                data={"username": login_username, "password": login_password}
            )
            if resp.status_code == 200:
                st.session_state.token = resp.json()["token"]
                st.session_state.username = login_username
                st.success("Login successful!")
            else:
                st.error(resp.json())
        except Exception as e:
            st.error(f"Login failed: {e}")

# -------------------------------
# SQL WORKSPACE
# -------------------------------
elif menu == "SQL Workspace":

    if st.session_state.token is None:
        st.warning("Please login first.")
        st.stop()

    if st.session_state.username == "admin":
        st.info("Admin should use the Admin Panel for management")
        st.stop()

    st.header(f"Welcome, {st.session_state.username} 👋")

    # Start MySQL container
    if st.button("Start MySQL Environment"):
        headers = {"x-token": st.session_state.token}
        try:
            resp = requests.post(f"{BACKEND_URL}/register_user/", headers=headers)
            if resp.status_code == 200:
                st.session_state.host_port = resp.json()["host_port"]
                st.success(f"MySQL container active on port {st.session_state.host_port}")
            else:
                st.error(resp.json())
        except Exception as e:
            st.error(f"Failed to start MySQL container: {e}")

    if st.session_state.host_port is None:
        st.info("Start the MySQL environment to continue.")
        st.stop()

    # Connect to database
    try:
        engine = create_engine(
            f"mysql+pymysql://root:{MYSQL_PASSWORD}@{BACKEND_IP}:{st.session_state.host_port}/{st.session_state.username}_db"
        )
        conn = engine.connect()
    except Exception as e:
        st.error(f"Unable to connect to database: {e}")
        st.stop()

    # SQL Editor
    st.subheader("📝 SQL Editor")
    sql_query = st.text_area("Write SQL here:", height=200)

    if st.button("Run Query"):
        try:
            df = pd.read_sql(sql_query, conn)
            st.success("Query executed successfully!")
            st.dataframe(df)
        except Exception as e:
            st.error(str(e))

    # Schema Explorer
    st.subheader("📊 Database Schema Explorer")
    try:
        # Tables
        st.write("### Tables")
        tables = pd.read_sql("SHOW TABLES", conn)
        st.dataframe(tables)

        # Columns
        if not tables.empty:
            table_list = tables.iloc[:, 0].tolist()
            selected_table = st.selectbox("Select a table", table_list)
            if selected_table:
                st.write(f"### Columns in `{selected_table}`")
                cols = pd.read_sql(f"SHOW COLUMNS FROM {selected_table}", conn)
                st.dataframe(cols)

        # Views
        st.write("### Views")
        views = pd.read_sql("SHOW FULL TABLES WHERE Table_type='VIEW'", conn)
        st.dataframe(views)

        # Stored Procedures
        st.write("### Stored Procedures")
        df_proc = pd.read_sql(f"""
            SELECT routine_name, routine_type 
            FROM information_schema.routines 
            WHERE routine_schema = '{st.session_state.username}_db'
        """, conn)
        st.dataframe(df_proc)

        # Triggers
        st.write("### Triggers")
        df_trig = pd.read_sql(f"""
            SELECT trigger_name, event_manipulation, event_object_table
            FROM information_schema.triggers
            WHERE trigger_schema = '{st.session_state.username}_db'
        """, conn)
        st.dataframe(df_trig)

    except Exception as e:
        st.error(f"Schema explorer error: {e}")

    conn.close()

# -------------------------------
# ADMIN PANEL
# -------------------------------
elif menu == "Admin Panel":
    if st.session_state.token is None:
        st.warning("Please login first.")
        st.stop()

    if st.session_state.username != "admin":
        st.warning("Admin access only")
        st.stop()

    st.header("👑 Admin Panel")

    # Get all users
    try:
        resp = requests.get(f"{BACKEND_URL}/admin/get_users/", headers={"x-token": st.session_state.token})
        if resp.status_code == 200:
            users = resp.json()["users"]
            st.write("### Registered Users")
            st.dataframe(users)
        else:
            st.error(resp.json())
    except Exception as e:
        st.error(f"Failed to get users: {e}")

    st.subheader("Delete a User")
    user_to_delete = st.selectbox("Select user to delete", [u["username"] for u in users if u["username"] != "admin"])

    if st.button("Delete User"):
        try:
            resp = requests.post(f"{BACKEND_URL}/admin/delete_user/", headers={"x-token": st.session_state.token},
                                 data={"username": user_to_delete})
            if resp.status_code == 200:
                st.success(f"User {user_to_delete} deleted successfully")
            else:
                st.error(resp.json())
        except Exception as e:
            st.error(f"Failed to delete user: {e}")
