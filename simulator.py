
import json
import random
import yaml
class Service:
    def __init__(self, name, health):
        self.name = name
        self.health = health
        self.depends_on = []
        self.dependents = []
        self.check_failed = False
        self.failed_tick = None
        self.has_ever_failed = False
        self.total_failures = 0

"""
data is a python list of dictionaries
i -> a dictionary 
services_map is a dictionary which stores service name as key and object as value
"""


def build_services(services_file: str, config_file: str):
    with open(services_file) as file:
        data = json.load(file)

    with open(config_file) as f:
        config = yaml.safe_load(f)

    services_map = {}
    for i in data:
        service_obj = Service(i["name"], i["health"])
        services_map[service_obj.name] = service_obj
    for i in data:
        service_obj = services_map[i["name"]]
        for depends in i["depends_on"]:
            service_obj.depends_on.append(depends)
            services_map[depends].dependents.append(service_obj.name)
    return services_map, config

def glitch(services_map):
    service = random.choice(list(services_map.values()))    
    delta = random.uniform(0.2, 0.5)
    service.health = max(0, service.health - delta)
    return service

def propagate_failure(service, services_map, current_tick, config):
    threshold = config["threshold"]
    alpha = config["alpha"]
    if(service.health < threshold):
        
        service.has_ever_failed = True
        #only set when it is failing for the first time
        if not service.check_failed:
            service.failed_tick = current_tick
            service.total_failures += 1
        service.check_failed = True
        
        for dep_name in service.dependents:
            dep = services_map[dep_name]
            dep.health = max(0, dep.health - alpha*(threshold - service.health))
            propagate_failure(dep, services_map, current_tick, config)

#for blast radius i'll just write the dfs function and later using loop i'll check for the failed ones and apply calc blast radius to those nodes only
def calc_blast_radius(service, services_map):
    blast_services = []
    visited = {}
    for service_name in services_map:
        visited[service_name] = False
    def dfs(cur_service):
        for dep_name in cur_service.dependents:
            if(visited[dep_name] == False):
                visited[dep_name] = True
                blast_services.append(dep_name)
                dfs(services_map[dep_name])
    dfs(service)
    return blast_services

def heal_services(services_map, current_tick, config):
    cooldown = config["cooldown"]
    threshold = config["threshold"]
    heal_to = config["heal_to"]
    for service in services_map.values():
        if service.check_failed and service.failed_tick is not None:
            # Heal only if failed for at least K ticks
            if current_tick - service.failed_tick >= cooldown:
                old_health = service.health
                service.health = min(heal_to, service.health + 0.1)
                if service.health >= threshold:
                    service.check_failed = False
                    service.failed_tick = None  
                propagate_heal(service, services_map, old_health, config)

def propagate_heal(service, services_map, old_health, config):
    threshold = config["threshold"]
    alpha = config["alpha"]
    for dep_name in service.dependents:
        dep = services_map[dep_name]
        delta = alpha * max(0, service.health - old_health)
        new_health = min(1.0, dep.health + delta)
        if new_health > dep.health:
            dep.health = new_health
            if(new_health >= threshold):
                dep.check_failed = False
            propagate_heal(dep, services_map, old_health, config)



def get_blast_services_and_radius(services_map, config):
    threshold = config["threshold"]
    blasts = {}
    for service in services_map.values():
        if(service.health < threshold):
            blast_list = calc_blast_radius(service, services_map)
            blasts[service.name] =  {"blast_list": blast_list, "blast_radius": len(blast_list)}
    return blasts

def find_rca(failed_service, services_map, root_causes=None):
    if root_causes is None:
        root_causes = set()
    if check_loop(services_map):

        root_causes.add(failed_service.name)
        return root_causes
    has_failed_upstream = False
    

    for super_dep_name in failed_service.depends_on:
        super_dep = services_map[super_dep_name]
        if super_dep.check_failed == True:
            has_failed_upstream = True
            find_rca(super_dep, services_map, root_causes)
    if not has_failed_upstream:
        root_causes.add(failed_service.name)
    
    return root_causes

def dfsCheck(node, visited, pathVis, services_map, path):
    visited[node] = True
    pathVis[node] = True
    path.append(node)
    
    for depends_name in services_map[node].depends_on:
        if(visited[depends_name] == False):
            if(dfsCheck(depends_name, visited, pathVis, services_map, path) == True):
                return True
        elif(pathVis[depends_name] == True):
            cycle_start = path.index(depends_name)
            cycle_path = path[cycle_start:] + [depends_name]
            print(f"[WARN] Cycle detected: {' -> '.join(cycle_path)} (RCA may be approximate)")
            return True
    pathVis[node] = False
    path.pop()
    return False

def check_loop(services_map):
    visited = {name: False for name in services_map}
    pathVis = {name: False for name in services_map}
    path = []
    for service_name in services_map:
        if(visited[service_name] == False):
            if(dfsCheck(service_name, visited, pathVis, services_map, path) ==True):
                return True
    return False




def simulate(services_map, config):
    ticks = config["ticks"]
    seed = config["seed"]
    threshold = config["threshold"]
    random.seed(seed)
    log_lines = []
    tick_history = []
 
    tick_history.append(capture_tick_state(services_map, 0))
    
    for t in range(1, ticks+1):
        log_lines.append(f"--- Tick {t} ---")

        print(f"\n--- Tick {t} ---")

        glitched = glitch(services_map)
        line = f"[ALERT] {glitched.name} fell below threshold ({glitched.health:.2f} < {threshold}) at T={t}"
        print(line)
        log_lines.append(line)

        propagate_failure(glitched, services_map, t, config)
        heal_services(services_map, t, config)
        
        tick_history.append(capture_tick_state(services_map, t))
        
        failed_services = []
        for s in services_map.values():
            if(s.check_failed == True):
                failed_services.append(s.name)
        print(f"[FAILED SERVICES] {', '.join(failed_services)}")
        log_lines.append(f"[FAILED SERVICES] {', '.join(failed_services)}\n")

        blasts = get_blast_services_and_radius(services_map, config)
        for sv, info in blasts.items():
            line = f"[BLAST] {sv}: radius={info['blast_radius']}, affected={info['blast_list']}"
            log_lines.append(line + "\n")
        for service_name in failed_services:
            service = services_map[service_name]
            root_causes = find_rca(service, services_map)
            line = f"[RCA] {service_name}: root causes = {', '.join(root_causes)}"
            log_lines.append(line + "\n")
    return log_lines, tick_history


def capture_tick_state(services_map, tick):
    """Capture the complete state of all services at a given tick"""
    nodes = []
    links = []
    
    for name, s in services_map.items():
        nodes.append({
            "id": name,
            "health": s.health,
            "check_failed": s.check_failed,
            "failed_tick": s.failed_tick,
            "has_ever_failed": s.has_ever_failed,
            "total_failures": s.total_failures
        })
        
        for dep in s.depends_on:
            links.append({"source": dep, "target": name})
    
    return {
        "tick": tick,
        "nodes": nodes,
        "links": links
    }


def query_why_failing(service_name, services_map):
    if service_name not in services_map:
        return f"Service '{service_name}' not found."
    s = services_map[service_name]
    if not s.check_failed:
        return f"Service '{service_name}' is not currently failing."
    causes = find_rca(s, services_map)
    return f"Service '{service_name}' is failing. Root cause(s): {', '.join(causes)}."

def query_why_failing_with_chain(service_name, services_map):
    if service_name not in services_map:
        return f"Service '{service_name}' not found."
    service = services_map[service_name]
    if not service.check_failed and not service.has_ever_failed:
        return f"Service '{service_name}' has never failed during this simulation."
    if service.check_failed:
        status = "is currently failing"
    else:
        status = f"failed {service.total_failures} time(s) but has since recovered"
    paths = find_rca_paths(service, services_map)
    if not paths:
        return f"Service '{service_name}' {status}. Root cause: independent failure."
    
    result_lines = [f"Service '{service_name}' {status}.\nFailure chain(s):"]
    for path in paths:
        chain = " -> ".join(reversed(path))
        result_lines.append("  " + chain)
    
    return "\n".join(result_lines)


def find_rca_paths(service, services_map, path=None, all_paths=None):
    if path is None:
        path = []
    if all_paths is None:
        all_paths = []
    
    path.append(service.name)
    
    # Check BOTH currently failing AND historically failed dependencies
    failed_upstreams = [
        services_map[dep] for dep in service.depends_on 
        if services_map[dep].check_failed or services_map[dep].has_ever_failed
    ]
    
    if not failed_upstreams:
        all_paths.append(path.copy())
    else:
        for upstream in failed_upstreams:
            find_rca_paths(upstream, services_map, path, all_paths)
    
    path.pop()
    return all_paths


def query_last_ticks(log_lines, N):
    lines = []
    count = 0
    for line in reversed(log_lines):
        if line.startswith('--- Tick'):
            count += 1
            if count > N:
                break
        lines.insert(0, line)
    return "\n".join(lines)

def query_top_impacted(services_map, initial_health_map):
    lst = []
    for name, s in services_map.items():
        before = initial_health_map.get(name, 1.0)
        degrade = max(0, before - s.health)
        lst.append((name, degrade))
    lst.sort(key=lambda x: x[1], reverse=True)
    return "\n".join(
        [f"{n}: cumulative degradation = {d:.3f}" for (n, d) in lst]
    )

def handle_query(query, services_map, log_lines, initial_health_map):
    if query.startswith("why is"):
        service_name = query.split("why is ")[1].split()[0]
        return query_why_failing_with_chain(service_name, services_map)
    elif query.startswith("list"):  # NEW
        return query_list_all_failed(services_map)
    elif query.startswith("last"):
        try:
            N = int(query.split("last ")[1].split()[0])
        except:
            N = 5
        return query_last_ticks(log_lines, N)
    elif query.startswith("top impacted"):
        return query_top_impacted(services_map, initial_health_map)
    else:
        return "Unknown query."


def query_list_all_failed(services_map):
    """List all services that failed (current or recovered)"""
    currently_failed = []
    recovered = []
    
    for name, s in services_map.items():
        if s.check_failed:
            currently_failed.append((name, s.health, s.failed_tick))
        elif s.has_ever_failed:
            recovered.append((name, s.health, s.total_failures))
    
    lines = []
    if currently_failed:
        lines.append(f"CURRENTLY FAILING ({len(currently_failed)}):")
        for name, health, tick in currently_failed:
            lines.append(f"  {name}: health={health:.2f}, failed at tick {tick}")
    
    if recovered:
        lines.append(f"\nRECOVERED ({len(recovered)}):")
        for name, health, failures in recovered:
            lines.append(f"  {name}: health={health:.2f}, failed {failures} time(s)")
    
    return "\n".join(lines) if lines else "No failures detected."

