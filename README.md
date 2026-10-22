<img width="1069" height="493" alt="image" src="https://github.com/user-attachments/assets/fbc47c0a-254d-40f5-9daa-d10b55464c7a" /># FlowBoard – Task Manager

A simple task manager I built with **Meu Labs**. It has a Flask + SQLite backend and a one-page HTML front end. Users can register, log in, create tasks, and sort them into boards.

## Features

- **User accounts:** register, log in, log out, and check the current session. Passwords are hashed with Werkzeug.
- **Tasks:** create, view, search by name, edit, and delete tasks. Each task has:
  - name, description, and time requirement
  - priority: `high`, `medium`, `low`
  - status: `pending`, `in-progress`, `done`
  - creation date
- **Boards:** create, list, search, and delete boards, like "Project Alpha" or "Work Tasks".
- **Board–task links:** a task can belong to several boards and a board can hold many tasks. Removing a task from a board doesn't delete the task, and deleting a board keeps its tasks.
- **Protected routes:** every task and board route needs a logged-in session through a `login_required` decorator.
- **Web UI:** a single page (`ui_complete.html`) served at `/` with login, add task, edit task, new group and add-to-group views.

## Screenshots

> Replace each placeholder with a real screenshot saved in a `screenshots/` folder.

### Login
![Login screen](screenshots/login.png)
<img width="1069" height="493" alt="image" src="https://github.com/user-attachments/assets/5979d80e-89d7-4092-844a-049c3a5d13b1" />

*Log in or register a new account.*

### Task List
![Task list](screenshots/task-list.png)
*All tasks with their priority and status.*
<img width="1271" height="870" alt="image" src="https://github.com/user-attachments/assets/a011e6df-b54c-4d3c-8d9a-42fd48d0ef10" />


### Add a New Task
![Add task form](screenshots/add-task.png)
*Create a task with a name, description, time requirement, priority and status.*
<img width="1274" height="870" alt="image" src="https://github.com/user-attachments/assets/f360da0a-6acf-43eb-a619-583095934634" />

### Edit Task
![Edit task modal](screenshots/edit-task.png)
*Update an existing task's details.*
<img width="1273" height="870" alt="image" src="https://github.com/user-attachments/assets/28bd5c43-a528-4e6e-a660-6f63c3ad27ea" />

### New board
![New group form](screenshots/new-group.png)
*Create a board to organise tasks.*
<img width="1270" height="866" alt="image" src="https://github.com/user-attachments/assets/11e3bed1-c36e-482f-8c3b-c45615b71e5c" />


### Add to Group
![Add task to group](screenshots/add-to-group.png)
*Link an existing task to a board.*
<img width="1276" height="868" alt="image" src="https://github.com/user-attachments/assets/49747ec1-a991-480f-a84c-36078c6b8afb" />


## Tech Stack

| Layer    | Technology                       |
| -------- | -------------------------------- |
| Backend  | Python, Flask, Flask-CORS        |
| Auth     | Flask sessions, Werkzeug hashing |
| Database | SQLite                           |
| Frontend | HTML, CSS, JavaScript            |

## Project Structure

```
├── backend_complete.py   # Flask API server (runs on port 5555)
├── ui_complete.html      # Front end, served at "/"
├── T_Todo.db             # SQLite database used by the backend
├── Flowboard.db          # Additional SQLite database
├── FlowBoard2.sqbpro     # DB Browser for SQLite project file
├── screenshots/          # README screenshots
├── LICENSE               # GPL-3.0
└── README.md
```

## Getting Started

### Prerequisites
- Python 3.8+
- pip

### Installation

```bash
git clone https://github.com/aathiffaizal-gif/Flowboard---Meu-Labs.git
cd Flowboard---Meu-Labs
pip install flask flask-cors werkzeug
```

### Run

```bash
python backend_complete.py
```

Then open **http://localhost:5555** in your browser. Missing database tables are created automatically when the app starts.

## Database Schema

- **User:** `username` (PK), `password` (hashed)
- **Task:** `Task_ID` (PK, auto-increment), `Task_Name`, `Task_Description`, `Task_TimeRequirement`, `Priority`, `Creation_Date`, `Task_Status`, `Board_ID`, `User_ID`
- **Group** (boards): `Board_ID` (PK, auto-increment), `Board_name`, `created_by`
- **BoardTask:** `Board_ID`, `Task_ID` (composite PK), a join table linking tasks to boards

## API Reference

### Auth
| Method | Endpoint    | Description                     |
| ------ | ----------- | ------------------------------- |
| POST   | `/register` | Register `{username, password}` |
| POST   | `/login`    | Log in `{username, password}`   |
| POST   | `/logout`   | Log out (requires login)        |
| GET    | `/me`       | Check the current session       |

### Tasks (login required)
| Method | Endpoint                   | Description                       |
| ------ | -------------------------- | --------------------------------- |
| GET    | `/tasks`                   | Get a random task                 |
| GET    | `/tasks/<id>`              | Get a task by ID                  |
| GET    | `/tasks/search?Task_Name=` | Search tasks by name              |
| POST   | `/addtasks`                | Create a task (returns its ID)    |
| PUT    | `/updatetasks/<id>`        | Update a task                     |
| DELETE | `/tasks/<id>`              | Delete a task and its board links |

### Boards (login required)
| Method | Endpoint                       | Description                        |
| ------ | ------------------------------ | ---------------------------------- |
| POST   | `/Boards`                      | Create a board `{Board_name}`      |
| GET    | `/Boards`                      | List all boards                    |
| GET    | `/Boards/search?board_name=`   | Search boards by name              |
| DELETE | `/Boards/<id>`                 | Delete a board (keeps its tasks)   |
| POST   | `/Boards/<id>/tasks`           | Add an existing task `{task_id}`   |
| GET    | `/groups/<id>/tasks`           | List the tasks in a board          |
| DELETE | `/groups/<id>/tasks/<task_id>` | Remove a task from a board         |
| GET    | `/my-tasks`                    | Boards created by the current user |

The `/examples/*` routes are worked examples from the course (a demo "club" with activities). They show the same register, login and linking patterns used above.

## Notes

- This is a learning project. The Flask `secret_key` is hardcoded and debug mode is on, so move the key to an environment variable and turn off debug before deploying anywhere.

## Acknowledgements

Built as part of a project with **Meu Labs**.

## License

Licensed under the **GPL-3.0 License**. See [LICENSE](LICENSE) for details.
