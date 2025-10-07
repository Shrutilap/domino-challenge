
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from simulator import build_services, simulate, handle_query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

services_map = None
log_lines = None
initial_health_map = None
config = None
tick_history = []


class SimulationRequest(BaseModel):
    services_file: str
    config_file: str


class QueryRequest(BaseModel):
    query: str


# Serve the frontend
@app.get("/")
async def read_root():
    return FileResponse("index.html")


@app.post("/run")
def run_simulation(req: SimulationRequest):
    global services_map, log_lines, initial_health_map, config, tick_history
    services_map, config = build_services(req.services_file, req.config_file)
    initial_health_map = {name: s.health for name, s in services_map.items()}
    log_lines, tick_history = simulate(services_map, config)

    return JSONResponse(content={"logs": log_lines})


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/query")
async def query_endpoint(req: QueryRequest):
    global services_map, log_lines, initial_health_map, config
    if services_map is None or log_lines is None or initial_health_map is None:
        return JSONResponse(content={"error": "Run /run first."}, status_code=400)

    result = handle_query(req.query, services_map, log_lines, initial_health_map)
    return {"result": result}


@app.get("/services")
def get_services():
    global services_map
    if services_map is None:
        return JSONResponse(content={"error": "No simulation running"}, status_code=400)

    nodes = [
        {"id": name, "health": s.health, "check_failed": s.check_failed}
        for name, s in services_map.items()
    ]
    links = [
        {"source": dep, "target": name}
        for name, s in services_map.items()
        for dep in s.depends_on
    ]

    return {"nodes": nodes, "links": links}


@app.get("/ticks")
def get_ticks():
    """Return all historical tick states (nodes + links)"""
    global tick_history
    if not tick_history:
        return JSONResponse(content={"error": "No simulation data available"}, status_code=400)
    return JSONResponse(content={"ticks": tick_history})
