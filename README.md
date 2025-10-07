# Domino-Challenge
A powerful visualization tool for simulating and analyzing cascading service failures in distributed systems. Watch how failures propagate through your service dependency graph in real-time with an interactive graph interface.

Test : (https://domino-challenge.onrender.com/)

Note: The backend is hosted on Render's free tier, so the first request may take 30-60 seconds to wake up the server.

1) ### Clone the repository
```
git clone https://github.com/Shrutilap/domino-challenge.git
cd domino-challenge
```
2) ### Create a virtual environment
```
python -m venv .venv

# On Windows
.venv\Scripts\activate

# On macOS/Linux
source .venv/bin/activate
```
3) ### Install dependencies
```
pip install -r requirements.txt
```
5) ### Run the backend server
```
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
Your backend will be available at: (http://localhost:8000)

7) ### Test the backend
```
curl http://localhost:8000/health
```

## Frontend Setup

1) Update the API endpoint in frontend/index.html

Find this line (around line 390):
```
javascriptconst API_BASE = 'https://domino-challenge.onrender.com';
```
Change it to:
```
javascriptconst API_BASE = 'http://localhost:8000';
```

Serve the frontend using Python HTTP Server
```
cd frontend
python -m http.server 3000
```
Open your browser

Visit: (http://localhost:3000)


### 📁 Project Structure
```
├── frontend/
│   └── index.html          # Frontend application
├── main.py                 # FastAPI backend server
├── simulator.py            # Core simulation engine
├── services.json           # Service dependency configuration
├── config.yaml            # Simulation parameters
├── requirements.txt        # Python dependencies
└── README.md              # This file
```
