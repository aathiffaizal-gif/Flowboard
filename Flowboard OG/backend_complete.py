"""
=============================================================
TASK MANAGER BACKEND - TEACHING TEMPLATE
=============================================================
Database: Flowboard.db

  Users  (User_ID, UserName, Password)
  Boards (Board_ID, Board_Name, Board_Description)
  Tasks  (Task_ID, Due_Date, Priority, Task_Name,
          Task_Description, Creation_Date, User_ID, Board_ID)

A task belongs to one board via Tasks.Board_ID (no join table).

What this file provides:
  - GET  /tasks              → random task
  - GET  /tasks/<id>         → task by ID
  - GET  /tasks/search       → search tasks by name
  - POST /addtasks           → add a task
  - PUT  /updatetasks/<id>   → update a task
  - DELETE /tasks/<id>       → delete a task
  - POST /groups  and /Boards             → create a board
  - GET  /groups  and /Boards             → list boards
  - GET  /groups/search and /Boards/search
  - POST /groups/<id>/tasks and /Boards/<id>/tasks → assign task to board
  - GET  /groups/<id>/tasks and /Boards/<id>/tasks → tasks on a board
  - DELETE /groups/<id>/tasks/<task_id>            → unassign from board
  - POST /register, /login, /logout
  - GET  /me
=============================================================
"""

from flask import Flask, jsonify, request, session
from flask_cors import CORS
from functools import wraps
import random
import sqlite3
import os

app = Flask(__name__)
CORS(app, supports_credentials=True)   # supports_credentials is needed for sessions with CORS

# ---------------------------------------------------------------
# SECRET KEY — Flask uses this to sign the session cookie.
# In a real project, store this in an environment variable,
# never hardcode it. But for learning, this is fine.
# ---------------------------------------------------------------
app.secret_key = "super_secret_key_change_this_in_production"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, 'Flowboard.db')

DEFAULT_BOARD_ID = 1   # "Default" board already in Flowboard.db


# ---------------------------------------------------------------
# DB HELPER
# ---------------------------------------------------------------
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row   # lets us access columns by name: row["Task_Name"]
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def pick(data, *keys, default=None):
    """Read the first present JSON key (UI and DB names both work)."""
    if not data:
        return default
    for key in keys:
        if key in data and data[key] is not None:
            return data[key]
    return default


def serialize_task(row):
    """Return DB column names plus aliases the teaching UI expects."""
    d = dict(row)
    d["Task_id"] = d.get("Task_ID")
    d["task_name"] = d.get("Task_Name")
    d["task_description"] = d.get("Task_Description")
    d["Date_created"] = d.get("Creation_Date")
    # Flowboard.db has no status / time-requirement columns
    d.setdefault("task_status", "pending")
    d.setdefault("task_TimeRequirement", d.get("Due_Date") or "")
    return d


def serialize_board(row):
    """Return DB column names plus aliases the teaching UI uses for 'groups'."""
    d = dict(row)
    d["group_id"] = d.get("Board_ID")
    d["group_name"] = d.get("Board_Name")
    d["board_name"] = d.get("Board_Name")
    d["created_by"] = d.get("Board_Description")
    return d


def current_user_id(conn):
    """Look up Users.User_ID from the session username, if logged in."""
    username = session.get("username")
    if not username:
        return None
    row = conn.execute(
        'SELECT "User_ID" FROM "Users" WHERE "UserName" = ?',
        (username,)
    ).fetchone()
    return row["User_ID"] if row else None


# ---------------------------------------------------------------
# DB SETUP — creates tables if they don't exist yet
# Matches Flowboard.db. Existing tables are left unchanged.
# ---------------------------------------------------------------
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS "Users" (
            "User_ID"   INTEGER PRIMARY KEY AUTOINCREMENT,
            "UserName"  TEXT,
            "Password"  TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS "Boards" (
            "Board_ID"          INTEGER PRIMARY KEY AUTOINCREMENT,
            "Board_Name"        TEXT,
            "Board_Description" TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS "Tasks" (
            "Task_ID"           INTEGER PRIMARY KEY AUTOINCREMENT,
            "Due_Date"          TEXT,
            "Priority"          TEXT,
            "Task_Name"         TEXT,
            "Task_Description"  TEXT,
            "Creation_Date"     TEXT,
            "User_ID"           INTEGER,
            "Board_ID"          INTEGER
        )
    """)

    conn.commit()
    conn.close()


# ---------------------------------------------------------------
# TASKS
# ---------------------------------------------------------------

@app.route('/tasks', methods=['GET'])
def get_random_task():
    conn = get_db_connection()
    tasks_list = conn.execute('SELECT * FROM "Tasks"').fetchall()
    conn.close()
    if tasks_list:
        task = random.choice(tasks_list)
        return jsonify([serialize_task(task)])
    return jsonify({"error": "No tasks found."}), 404


@app.route('/tasks/<int:Task_ID>', methods=['GET'])
def get_task_by_id(Task_ID):
    conn = get_db_connection()
    task = conn.execute(
        'SELECT * FROM "Tasks" WHERE "Task_ID" = ?', (Task_ID,)
    ).fetchone()
    conn.close()
    if task:
        return jsonify([serialize_task(task)])
    return jsonify({"error": f"Task '{Task_ID}' not found."}), 404


@app.route('/tasks/search', methods=['GET'])
def search_tasks():
    query = request.args.get("task_name") or request.args.get("Task_Name") or request.args.get("name") or ""
    conn = get_db_connection()
    tasks = conn.execute(
        'SELECT * FROM "Tasks" WHERE "Task_Name" LIKE ?', (f"%{query}%",)
    ).fetchall()
    conn.close()
    return jsonify([serialize_task(t) for t in tasks])


@app.route('/addtasks', methods=['POST'])
def add_task():
    data = request.get_json()
    task_name = pick(data, "Task_Name", "task_name")
    if not data or not task_name:
        return jsonify({"error": "Missing required field: Task_Name."}), 400

    due_date = pick(data, "Due_Date", "due_date", default="")
    priority = pick(data, "Priority", "priority", default="medium")
    description = pick(data, "Task_Description", "task_description", default="")
    creation_date = pick(data, "Creation_Date", "Creation Date", "Date_created", default="")
    board_id = pick(data, "Board_ID", "board_id", "group_id", default=DEFAULT_BOARD_ID)

    conn = get_db_connection()
    user_id = pick(data, "User_ID", "user_id", default=current_user_id(conn))

    cursor = conn.execute(
        """INSERT INTO "Tasks"
           ("Due_Date", "Priority", "Task_Name", "Task_Description",
            "Creation_Date", "User_ID", "Board_ID")
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (due_date, priority, task_name, description, creation_date, user_id, board_id)
    )
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return jsonify({"message": "Task added!", "Task_ID": new_id, "Task_id": new_id}), 201


@app.route('/updatetasks/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    data = request.get_json()
    if not data:
        return jsonify({"error": "JSON body is required."}), 400

    conn = get_db_connection()
    existing = conn.execute(
        'SELECT * FROM "Tasks" WHERE "Task_ID" = ?', (task_id,)
    ).fetchone()
    if not existing:
        conn.close()
        return jsonify({"error": "Task not found."}), 404

    task_name = pick(data, "Task_Name", "task_name", default=existing["Task_Name"])
    description = pick(data, "Task_Description", "task_description", default=existing["Task_Description"])
    due_date = pick(data, "Due_Date", "due_date", "task_TimeRequirement", default=existing["Due_Date"])
    priority = pick(data, "Priority", "priority", default=existing["Priority"])
    creation_date = pick(data, "Creation_Date", "Date_created", default=existing["Creation_Date"])
    user_id = pick(data, "User_ID", "user_id", default=existing["User_ID"])
    board_id = pick(data, "Board_ID", "board_id", "group_id", default=existing["Board_ID"])

    conn.execute(
        """UPDATE "Tasks"
           SET "Due_Date"=?, "Priority"=?, "Task_Name"=?, "Task_Description"=?,
               "Creation_Date"=?, "User_ID"=?, "Board_ID"=?
           WHERE "Task_ID"=?""",
        (due_date, priority, task_name, description, creation_date, user_id, board_id, task_id)
    )
    conn.commit()
    conn.close()
    return jsonify({"message": f"Task '{task_id}' updated."})


@app.route('/tasks/<int:Task_ID>', methods=['DELETE'])
def delete_task(Task_ID):
    conn = get_db_connection()
    result = conn.execute('DELETE FROM "Tasks" WHERE "Task_ID" = ?', (Task_ID,))
    conn.commit()
    conn.close()

    if result.rowcount > 0:
        return jsonify({"message": f"Task '{Task_ID}' deleted."})
    return jsonify({"error": "Task not found."}), 404


# ---------------------------------------------------------------
# BOARDS  (also exposed as /groups so the teaching UI still works)
# ---------------------------------------------------------------

def _create_board():
    data = request.get_json()
    board_name = pick(data, "Board_Name", "Board_name", "board_name", "group_name")
    if not data or not board_name:
        return jsonify({"error": "'Board_Name' is required."}), 400

    description = pick(
        data, "Board_Description", "board_description",
        default=session.get("username", "anonymous")
    )

    conn = get_db_connection()
    cursor = conn.execute(
        'INSERT INTO "Boards" ("Board_Name", "Board_Description") VALUES (?, ?)',
        (board_name, description)
    )
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return jsonify({
        "message": "Board created!",
        "Board_ID": new_id,
        "group_id": new_id
    }), 201


def _list_boards():
    conn = get_db_connection()
    boards = conn.execute('SELECT * FROM "Boards"').fetchall()
    conn.close()
    return jsonify([serialize_board(b) for b in boards])


def _search_boards():
    query = (
        request.args.get("board_name")
        or request.args.get("Board_Name")
        or request.args.get("name")
        or request.args.get("group_name")
        or ""
    )
    conn = get_db_connection()
    boards = conn.execute(
        'SELECT * FROM "Boards" WHERE "Board_Name" LIKE ?', (f"%{query}%",)
    ).fetchall()
    conn.close()
    return jsonify([serialize_board(b) for b in boards])


def _assign_task_to_board(board_id):
    data = request.get_json()
    task_id = pick(data, "task_id", "Task_ID", "Task_id")
    if not data or task_id is None:
        return jsonify({"error": "'task_id' is required."}), 400

    conn = get_db_connection()
    board = conn.execute(
        'SELECT * FROM "Boards" WHERE "Board_ID" = ?', (board_id,)
    ).fetchone()
    if not board:
        conn.close()
        return jsonify({"error": "Board not found."}), 404

    task = conn.execute(
        'SELECT * FROM "Tasks" WHERE "Task_ID" = ?', (task_id,)
    ).fetchone()
    if not task:
        conn.close()
        return jsonify({"error": "Task not found."}), 404

    conn.execute(
        'UPDATE "Tasks" SET "Board_ID" = ? WHERE "Task_ID" = ?',
        (board_id, task_id)
    )
    conn.commit()
    conn.close()
    return jsonify({"message": "Task added to board."})


def _get_tasks_on_board(board_id):
    conn = get_db_connection()
    board = conn.execute(
        'SELECT * FROM "Boards" WHERE "Board_ID" = ?', (board_id,)
    ).fetchone()
    if not board:
        conn.close()
        return jsonify({"error": "Board not found."}), 404

    tasks = conn.execute(
        'SELECT * FROM "Tasks" WHERE "Board_ID" = ?', (board_id,)
    ).fetchall()
    conn.close()
    return jsonify([serialize_task(t) for t in tasks])


def _unassign_task_from_board(board_id, task_id):
    """Clear the board link by moving the task back to the Default board."""
    conn = get_db_connection()
    result = conn.execute(
        """UPDATE "Tasks"
           SET "Board_ID" = ?
           WHERE "Task_ID" = ? AND "Board_ID" = ?""",
        (DEFAULT_BOARD_ID, task_id, board_id)
    )
    conn.commit()
    conn.close()
    if result.rowcount > 0:
        return jsonify({"message": "Task removed from board."})
    return jsonify({"error": "That task is not on that board."}), 404


@app.route('/Boards', methods=['POST'])
@app.route('/groups', methods=['POST'])
def create_board():
    return _create_board()


@app.route('/Boards', methods=['GET'])
@app.route('/groups', methods=['GET'])
def get_all_boards():
    return _list_boards()


@app.route('/Boards/search', methods=['GET'])
@app.route('/groups/search', methods=['GET'])
def search_boards():
    return _search_boards()


@app.route('/Boards/<int:board_id>/tasks', methods=['POST'])
@app.route('/groups/<int:board_id>/tasks', methods=['POST'])
def add_task_to_board(board_id):
    return _assign_task_to_board(board_id)


@app.route('/Boards/<int:board_id>/tasks', methods=['GET'])
@app.route('/groups/<int:board_id>/tasks', methods=['GET'])
def get_tasks_on_board(board_id):
    return _get_tasks_on_board(board_id)


@app.route('/Boards/<int:board_id>/tasks/<int:task_id>', methods=['DELETE'])
@app.route('/groups/<int:board_id>/tasks/<int:task_id>', methods=['DELETE'])
def remove_task_from_board(board_id, task_id):
    return _unassign_task_from_board(board_id, task_id)


# ---------------------------------------------------------------
# AUTH
# Users table: User_ID (auto), UserName, Password
# Session still stores the username string for /me and the UI.
# ---------------------------------------------------------------

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = pick(data, "username", "UserName")
    password = pick(data, "password", "Password")
    if not data or not username or not password:
        return jsonify({"error": "Username and password are required."}), 400

    conn = get_db_connection()
    existing = conn.execute(
        'SELECT "UserName" FROM "Users" WHERE "UserName" = ?', (username,)
    ).fetchone()
    if existing:
        conn.close()
        return jsonify({"error": "Username already taken."}), 409

    conn.execute(
        'INSERT INTO "Users" ("UserName", "Password") VALUES (?, ?)',
        (username, password)   # plain text — for demo only
    )
    conn.commit()
    conn.close()
    return jsonify({"message": "Account created! You can now log in."}), 201


@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = pick(data, "username", "UserName")
    password = pick(data, "password", "Password")
    if not data or not username or not password:
        return jsonify({"error": "Username and password are required."}), 400

    conn = get_db_connection()
    user = conn.execute(
        'SELECT * FROM "Users" WHERE "UserName" = ? AND "Password" = ?',
        (username, password)
    ).fetchone()
    conn.close()

    if not user:
        return jsonify({"error": "Invalid username or password."}), 401

    session["username"] = user["UserName"]
    session["user_id"] = user["User_ID"]

    return jsonify({
        "message": f"Welcome, {user['UserName']}!",
        "username": user["UserName"],
        "User_ID": user["User_ID"]
    })


@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"message": "Logged out."})


@app.route('/me', methods=['GET'])
def me():
    username = session.get("username")
    if username:
        return jsonify({
            "logged_in": True,
            "username": username,
            "User_ID": session.get("user_id")
        })
    return jsonify({"logged_in": False}), 401


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "username" not in session:
            return jsonify({"error": "You must be logged in."}), 401
        return f(*args, **kwargs)
    return decorated


@app.route('/my-tasks', methods=['GET'])
@login_required
def my_tasks():
    username = session["username"]
    conn = get_db_connection()
    tasks = conn.execute(
        """SELECT "Tasks".*
           FROM "Tasks"
           JOIN "Users" ON "Tasks"."User_ID" = "Users"."User_ID"
           WHERE "Users"."UserName" = ?""",
        (username,)
    ).fetchall()
    conn.close()
    return jsonify({
        "username": username,
        "my_tasks": [serialize_task(t) for t in tasks]
    })


# ---------------------------------------------------------------
if __name__ == '__main__':
    init_db()    # create tables on startup if the file is empty
    app.run(host='0.0.0.0', port=5555, debug=True)
