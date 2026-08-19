"""
server.py — Python HTTP & REST API Server for 3D Mars Rover Simulation

Serves the 3D WebGL Three.js client and bridges the Python Propositional Logic
Knowledge-Based Agent (Resolution & Model Checking) with the 3D interactive viewport.
"""

import http.server
import json
import os
import sys
import urllib.parse
from grid import MarsGrid, CellType
from agent import MarsRoverAgent
from logger import RoverLogger


class RoverSimulationState:
    """Manages active simulation instances and logical step progression."""

    def __init__(self, size=6, seed=None, hazard_density=0.20, radiation_density=0.15):
        self.size = size
        self.hazard_density = hazard_density
        self.radiation_density = radiation_density
        self.logger = RoverLogger(use_color=True)
        self.reset(seed=seed)

    def reset(self, seed=None):
        """Generate a fresh guaranteed-solvable grid and reset agent."""
        self.grid, self.attempts, self.true_path = MarsGrid.create_solvable_grid(
            n=self.size,
            seed=seed,
            start_pos=(0, 0),
            goal_pos=(self.size - 1, self.size - 1),
            hazard_density=self.hazard_density,
            radiation_density=self.radiation_density,
        )
        self.agent = MarsRoverAgent(self.grid, logger=self.logger, max_steps=300)
        self.step_generator = self.agent.run_step_by_step()
        self.last_step_data = None

        print("\n" + "=" * 65)
        print("  [3D MISSION INITIALIZED] ARES-1 MARS ROVER KB-AGENT")
        print("=" * 65)
        print(f"  Seed: {self.grid.seed} | Grid: {self.size}x{self.size} | Solvable Path: {len(self.true_path)} cells")
        print("=" * 65 + "\n")
        self.logger.print_header(self.grid)

        return self.get_init_payload()

    def get_init_payload(self):
        """Return full initialization payload for 3D web scene setup."""
        stats = self.grid.get_stats()
        # Return cell types (for ground truth reveal on perception)
        cells_data = {}
        for (x, y), ctype in self.grid.cells.items():
            cells_data[f"{x},{y}"] = ctype.value

        return {
            "size": self.grid.n,
            "seed": self.grid.seed,
            "start_pos": list(self.grid.start_pos),
            "goal_pos": list(self.grid.goal_pos),
            "stats": stats,
            "cells": cells_data,
            "attempts": self.attempts,
            "path_length": len(self.true_path) if self.true_path else 0,
            "kb_clauses": self.agent.kb.clause_count,
            "known_facts": len(self.agent.kb.facts),
        }

    def step(self):
        """Execute one KB-agent step and return telemetry."""
        if self.agent.is_done:
            return {
                "is_done": True,
                "reached_goal": self.agent.reached_goal,
                "completion_reason": self.agent.completion_reason,
                "rover_pos": [self.agent.x, self.agent.y],
                "prev_pos": [self.agent.x, self.agent.y],
                "step": self.agent.step,
                "kb_clause_count": self.agent.kb.clause_count,
                "known_facts_count": len(self.agent.kb.facts),
                "visited": [list(pos) for pos in self.agent.visited],
                "known_safe": [list(pos) for pos in self.agent.known_safe],
                "known_hazard": [list(pos) for pos in self.agent.known_hazard],
                "known_radiation": [list(pos) for pos in self.agent.known_radiation],
                "sensed_cells": [list(pos) for pos in self.agent.sensed_cells],
                "hazard_avoidance_events": self.agent.hazard_avoidance_events,
            }

        try:
            step_data = next(self.step_generator)
            self.last_step_data = step_data

            # Print synchronized console logs
            step = step_data["step"]
            prev_x, prev_y = step_data["prev_pos"]
            cur_x, cur_y = step_data["rover_pos"]

            self.logger.print_step_header(
                step, prev_x, prev_y, step_data["kb_clause_count"]
            )
            self.logger.print_percepts(step, step_data["percepts"])
            self.logger.print_tell_log(step, step_data["tell_log"])
            self.logger.print_ask_log(step, step_data["ask_log"])
            self.logger.print_grid(
                self.grid.n,
                (cur_x, cur_y),
                step_data["visited"],
                step_data["known_safe"],
                step_data["known_hazard"],
                step_data["known_radiation"],
                step_data["sensed_cells"],
            )

            if step_data["action_type"] == "BACKTRACK":
                self.logger.print_backtrack(step, step_data["decision_text"])
                if step_data["path"]:
                    self.logger.print_path(step, step_data["path"])
            elif step_data["action_type"] in ("MOVE", "GOAL_REACHED"):
                self.logger.print_decision(step, step_data["decision_text"])

            if step_data["is_done"]:
                self.logger.print_exploration_complete(
                    step,
                    len(step_data["visited"]),
                    self.grid.n * self.grid.n,
                    step_data["completion_reason"]
                )

            # Format json-serializable payload
            percepts_serializable = {f"{k[0]},{k[1]}": v for k, v in step_data["percepts"].items()}
            path_serializable = [list(p) for p in step_data["path"]] if step_data["path"] else None

            # Format tell/ask log descriptions
            tell_log_summary = []
            for t in step_data["tell_log"]:
                tell_log_summary.append({
                    "source": t["source"],
                    "new_count": len(t["new_clauses"]),
                    "inferred": [[s, val] for s, val in t["inferred"]],
                    "total": t["total_clauses"],
                })

            ask_log_summary = []
            for a in step_data["ask_log"]:
                ask_log_summary.append({
                    "query": a["query"],
                    "result": a["result"],
                    "method": a["method"],
                    "steps": a["steps"],
                })

            return {
                "step": step,
                "rover_pos": list(step_data["rover_pos"]),
                "prev_pos": list(step_data["prev_pos"]),
                "action_type": step_data["action_type"],
                "decision_text": step_data["decision_text"],
                "path": path_serializable,
                "percepts": percepts_serializable,
                "tell_log": tell_log_summary,
                "ask_log": ask_log_summary,
                "visited": [list(pos) for pos in step_data["visited"]],
                "known_safe": [list(pos) for pos in step_data["known_safe"]],
                "known_hazard": [list(pos) for pos in step_data["known_hazard"]],
                "known_radiation": [list(pos) for pos in step_data["known_radiation"]],
                "sensed_cells": [list(pos) for pos in step_data["sensed_cells"]],
                "kb_clause_count": step_data["kb_clause_count"],
                "known_facts_count": step_data["known_facts_count"],
                "is_done": step_data["is_done"],
                "reached_goal": step_data["reached_goal"],
                "completion_reason": step_data["completion_reason"],
                "hazard_avoidance_events": step_data["hazard_avoidance_events"],
            }

        except StopIteration:
            return {"is_done": True, "reached_goal": self.agent.reached_goal}


# Global state
sim_state = RoverSimulationState()


class Rover3DRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Custom HTTP handler serving web assets and REST API endpoints."""

    def __init__(self, *args, **kwargs):
        # Base directory is d:\Ai_rover\web
        self.web_dir = os.path.join(os.path.dirname(__file__), "web")
        super().__init__(*args, directory=self.web_dir, **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)

        if parsed.path == "/api/init":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(sim_state.get_init_payload()).encode("utf-8"))
            return

        elif parsed.path == "/api/step":
            result = sim_state.step()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(result).encode("utf-8"))
            return

        elif parsed.path == "/api/reset":
            query_params = urllib.parse.parse_qs(parsed.query)
            seed = int(query_params["seed"][0]) if "seed" in query_params else None
            result = sim_state.reset(seed=seed)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(result).encode("utf-8"))
            return

        # Serve static assets from web directory
        return super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path in ("/api/step", "/api/reset"):
            return self.do_GET()
        self.send_error(404, "Endpoint not found")


def start_server(port=8000, size=6, seed=None):
    """Start local 3D simulation HTTP server."""
    global sim_state
    sim_state = RoverSimulationState(size=size, seed=seed)

    server_address = ("", port)
    httpd = http.server.HTTPServer(server_address, Rover3DRequestHandler)
    print(f"[3D Server] Live on http://localhost:{port}")
    return httpd
