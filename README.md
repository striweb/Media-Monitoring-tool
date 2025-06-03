# Media Monitoring Tool

**Media Monitoring Tool** is a full-stack web application designed to monitor, analyze, and manage media data. It features a Flask-based backend, a modern React frontend, and is fully containerized with Docker for seamless deployment.

---

## 🚀 Features

- 🔍 Real-time media content monitoring and display  
- 🧠 Backend API built with Python & Flask  
- 💡 Responsive UI built with React  
- 👨‍💼 Admin user setup via script  
- 🌐 Internet connectivity checks  
- 🐳 Docker and Docker Compose support for production and development  
- 🗃️ MongoDB integration for data persistence  
- 🖥️ Mongo Express UI for database inspection  
- 🔧 Utility scripts for setup and maintenance

---

## 🛠️ Tech Stack

| Layer     | Technology       |
|-----------|------------------|
| Backend   | Python, Flask    |
| Frontend  | React (CRA)      |
| Database  | MongoDB + Mongo Express |
| DevOps    | Docker, Docker Compose |
| Scripts   | Bash (for setup and automation) |

---

## 📁 Project Structure

```
Media-Monitoring-tool-main/
├── app.py                  # Flask application entry point
├── bc.py                   # Additional backend logic
├── insert_admin.py         # Script to insert admin user
├── check_internet.py       # Internet connectivity checker
├── requirements.txt        # Python dependencies
├── Dockerfile              # Dockerfile for backend
├── docker-compose.yml      # Multi-container orchestration
├── mm3/                    # React frontend app
│   ├── public/
│   └── src/
├── *.sh                    # Shell scripts for automation
```

---

## ⚙️ Installation & Usage

### 🔧 Prerequisites

- Python 3.7+
- Node.js and npm (for frontend, optional if using Docker)
- Docker and Docker Compose (recommended)

---

### 🐳 Run with Docker

```bash
git clone https://github.com/your-username/media-monitoring-tool.git
cd media-monitoring-tool
docker-compose up --build
```

- Flask backend: [http://localhost:5000](http://localhost:5000)  
- React frontend: [http://localhost:3000](http://localhost:3000)  
- Mongo Express UI: [http://localhost:8081](http://localhost:8081)

---

### 🧪 Run Locally (Manual Setup)

#### Backend (Flask)

```bash
pip install -r requirements.txt
python app.py
```

Ensure MongoDB is running at `mongodb://localhost:27017/`.

#### Frontend (React)

```bash
cd mm3
npm install
npm start
```

Open in browser: [http://localhost:3000](http://localhost:3000)

---

## 🗃️ MongoDB Details

This project uses **MongoDB** as its primary database. By default, it is included in `docker-compose.yml` and runs locally on:

```
mongodb://localhost:27017/
```

### 🖥️ Mongo Express

A lightweight web UI is available via **Mongo Express** at:  
[http://localhost:8081](http://localhost:8081)

Use it to inspect collections, documents, and indexes directly in your browser.

### Sample Collections (depends on your setup):

- `users` – Admin and user data
- `sources` – Media source definitions
- `logs` – Monitoring logs or extracted entries

You can access the database via:

```bash
docker exec -it <mongo_container_name> mongosh
```

Or using MongoDB Compass for GUI inspection.

---

## 🧰 Useful Scripts

- `insert_admin.py` — Adds an administrator user to the system  
- `check_internet.py` — Verifies network connectivity  
- `13.sh`, `eflask.sh`, `pullgit.sh` — Various automation tasks

---

## 📄 License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for more details.

---

## 👤 Author

Developed by **Simeon Bakalov**  
For inquiries or contributions, please contact: 📧 bakalov@striweb.com
