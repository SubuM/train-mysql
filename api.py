from fastapi import FastAPI, HTTPException, Header, Depends
from pydantic import BaseModel
from pathlib import Path
import docker
import os
import random
import string
import hashlib
import json
import logging
from typing import Dict, Optional


# -------------------------------
# Config
# -------------------------------
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "supersecretadmintoken")
MYSQL_IMAGE = "mysql:8.0"
MYSQL_ROOT_PASSWORD = os.getenv("MYSQL_ROOT_PASSWORD", "rootpassword")
PORT_RANGE_START = 33070
PORT_RANGE_END = 33100
DATA_FILE = Path("users_db.json")


# -------------------------------
# Initialize app and docker
# -------------------------------
app = FastAPI(title="MySQL Docker Manager")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_docker_client():
    try:
        return docker.from_env()
    except Exception as e:
        logger.warning("Docker client not available: %s", e)
        return None


client = get_docker_client()


# -------------------------------
# In-memory user db (persisted)
# -------------------------------
users_db: Dict[str, Dict] = {}


# -------------------------------
# Persistence helpers
# -------------------------------
def save_users_db() -> None:
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(users_db, f, indent=2)
    except Exception as e:
        logger.error("Failed to save users DB: %s", e)


def load_users_db() -> None:
    global users_db
    try:
        if DATA_FILE.exists():
            with open(DATA_FILE, "r") as f:
                users_db = json.load(f)
        else:
            users_db = {}
    except Exception as e:
        logger.error("Failed to load users DB: %s", e)
        users_db = {}


# -------------------------------
# Helper Functions
# -------------------------------
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, hashed: str) -> bool:
    return hash_password(password) == hashed


def random_string(n: int = 6) -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=n))


def get_user(username: str) -> Optional[Dict]:
    return users_db.get(username)


def require_admin(x_token: str = Header(...)) -> Dict:
    user = get_user(x_token)
    if not user or not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return user


def require_auth(x_token: str = Header(...)) -> Dict:
    user = get_user(x_token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    if user.get("suspended", False):
        raise HTTPException(status_code=403, detail="User suspended")
    return {"username": x_token, **user}


def assign_port() -> int:
    used_ports = [u.get("host_port") for u in users_db.values() if u.get("host_port")]
    for port in range(PORT_RANGE_START, PORT_RANGE_END):
        if port not in used_ports:
            return port
    raise HTTPException(status_code=500, detail="No available port")


def start_mysql_container(username: str) -> int:
    if client is None:
        raise HTTPException(status_code=500, detail="Docker not available")
    port = assign_port()
    container_name = f"mysql_{username}"
    try:
        client.containers.run(
            MYSQL_IMAGE,
            name=container_name,
            environment={
                "MYSQL_ROOT_PASSWORD": MYSQL_ROOT_PASSWORD,
                "MYSQL_ROOT_HOST": "%",
            },
            ports={"3306/tcp": port},
            detach=True,
        )
    except Exception as e:
        logger.error("Failed to start container for %s: %s", username, e)
        raise HTTPException(status_code=500, detail="Failed to start container")

    users_db[username]["container_name"] = container_name
    users_db[username]["host_port"] = port
    save_users_db()
    return port


# -------------------------------
# Models
# -------------------------------
class AuthModel(BaseModel):
    username: str
    password: str


class UserActionModel(BaseModel):
    username: str


# -------------------------------
# Startup
# -------------------------------
@app.on_event("startup")
def startup() -> None:
    load_users_db()
    if ADMIN_USERNAME not in users_db:
        users_db[ADMIN_USERNAME] = {
            "password_hash": hash_password(ADMIN_PASSWORD),
            "is_admin": True,
            "container_name": None,
            "host_port": None,
            "suspended": False,
        }
        save_users_db()
    logger.info("Loaded users: %s", list(users_db.keys()))


# -------------------------------
# Auth endpoints
# -------------------------------
@app.post("/auth/register/")
def register_user(auth: AuthModel):
    if auth.username in users_db:
        raise HTTPException(status_code=400, detail="Username already exists")
    users_db[auth.username] = {
        "password_hash": hash_password(auth.password),
        "is_admin": False,
        "container_name": None,
        "host_port": None,
        "suspended": False,
    }
    save_users_db()
    return {"message": f"User {auth.username} registered successfully"}


@app.post("/auth/login/")
def login_user(auth: AuthModel):
    user = users_db.get(auth.username)
    if not user or not verify_password(auth.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"token": auth.username}


# -------------------------------
# User endpoint
# -------------------------------
@app.post("/register_user/")
def create_user_container(user: Dict = Depends(require_auth)):
    username = user["username"]
    # If already has a container, return current port
    if user.get("container_name") and user.get("host_port"):
        return {"message": f"MySQL container already exists on port {user['host_port']}"}

    port = start_mysql_container(username)
    return {
        "message": "Container started",
        "host": "13.61.141.60",
        "port": port,
        "user": "root",
        "password": MYSQL_ROOT_PASSWORD,
    }


# -------------------------------
# Admin endpoints
# -------------------------------
@app.get("/admin/list_user/")
def list_users(admin: Dict = Depends(require_admin)):
    return {"users": list(users_db.keys())}


@app.get("/admin/list_users_detailed/")
def list_users_detailed(admin: Dict = Depends(require_admin)):
    return users_db


@app.post("/admin/delete_user/")
def delete_user(data: UserActionModel, admin: Dict = Depends(require_admin)):
    u = users_db.get(data.username)
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    if u.get("container_name") and client:
        try:
            c = client.containers.get(u["container_name"])
            c.stop()
            c.remove()
        except Exception:
            logger.debug("Failed to remove container for %s", data.username)
    del users_db[data.username]
    save_users_db()
    return {"message": f"User {data.username} deleted"}


@app.post("/admin/restart_user/")
def restart_user(data: UserActionModel, admin: Dict = Depends(require_admin)):
    u = users_db.get(data.username)
    if not u or not u.get("container_name"):
        raise HTTPException(status_code=404, detail="Container not found")
    if not client:
        raise HTTPException(status_code=500, detail="Docker not available")
    client.containers.get(u["container_name"]).restart()
    return {"message": f"Container for {data.username} restarted"}


@app.post("/admin/start_user/")
def start_user(data: UserActionModel, admin: Dict = Depends(require_admin)):
    u = users_db.get(data.username)
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    if not u.get("container_name"):
        port = start_mysql_container(data.username)
        return {"message": f"Container started on port {port}"}
    if not client:
        raise HTTPException(status_code=500, detail="Docker not available")
    client.containers.get(u["container_name"]).start()
    return {"message": f"Container for {data.username} started"}


@app.post("/admin/stop_user/")
def stop_user(data: UserActionModel, admin: Dict = Depends(require_admin)):
    u = users_db.get(data.username)
    if not u or not u.get("container_name"):
        raise HTTPException(status_code=404, detail="Container not found")
    if not client:
        raise HTTPException(status_code=500, detail="Docker not available")
    client.containers.get(u["container_name"]).stop()
    return {"message": f"Container for {data.username} stopped"}


@app.post("/admin/suspend_user/")
def suspend_user(data: UserActionModel, admin: Dict = Depends(require_admin)):
    u = users_db.get(data.username)
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    u["suspended"] = True
    save_users_db()
    return {"message": f"User {data.username} suspended"}


@app.post("/admin/unsuspend_user/")
def unsuspend_user(data: UserActionModel, admin: Dict = Depends(require_admin)):
    u = users_db.get(data.username)
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    u["suspended"] = False
    save_users_db()
    return {"message": f"User {data.username} unsuspended"}


@app.get("/admin/container_logs/")
def container_logs(username: str, admin: Dict = Depends(require_admin)):
    u = users_db.get(username)
    if not u or not u.get("container_name"):
        raise HTTPException(status_code=404, detail="Container not found")
    if not client:
        raise HTTPException(status_code=500, detail="Docker not available")
    logs = client.containers.get(u["container_name"]).logs(tail=100)
    # logs may be bytes
    if isinstance(logs, bytes):
        logs = logs.decode(errors="ignore")
    return {"logs": logs}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8000)
