"""
agent.py — Mars Rover Goal-Directed KB Agent (Control Loop)

Implements the classic KB-agent cycle:
    Percept → TELL(KB, percept) → ASK(KB, best action) → Execute → repeat

Goal-Directed Navigation:
  - Target: extraction Goal cell (default: N-1, N-1).
  - Movement policy: prioritizes KB-inferred safe cells that reduce Manhattan
    distance to Goal.
  - Backtracking: when immediate paths are blocked by hazards or radiation,
    the agent backtracks along known visited safe cells to the best frontier cell
    closest to the Goal.
  - Clean State Reset: Supports full reset for new mission map generation.
"""

from collections import deque
from grid import MarsGrid
from kb_engine import KnowledgeBase, encode_percept_rules, make_clause, negate
from logger import RoverLogger


class MarsRoverAgent:
    """Goal-Directed Knowledge-Based Agent for Mars Navigation."""

    def __init__(self, grid, logger=None, max_steps=300):
        """
        Args:
            grid: MarsGrid instance (agent only interacts via get_percepts).
            logger: RoverLogger instance for console output.
            max_steps: Safety limit to prevent runaway loops.
        """
        self.grid = grid
        self.logger = logger or RoverLogger()
        self.max_steps = max_steps
        self.goal_pos = grid.goal_pos

        self.reset_with_grid(grid)

    def reset_with_grid(self, new_grid):
        """
        Completely reset all internal agent state with a fresh grid world.
        Wipes KB clauses, facts, path history, step counter, and telemetry.
        """
        self.grid = new_grid
        self.goal_pos = new_grid.goal_pos
        self.kb = KnowledgeBase()

        # Rover position & exploration state
        self.x, self.y = new_grid.start_pos
        self.step = 0
        self.visited = set()
        self.path_history = [(self.x, self.y)]
        self.is_done = False
        self.completion_reason = ""
        self.reached_goal = False

        # Visualizer / display sets
        self.known_safe = set()
        self.known_hazard = set()
        self.known_radiation = set()
        self.sensed_cells = set()
        self.hazard_avoidance_events = []

        self._rules_added = set()
        self._reported_hazards = set()

        # Initial axioms
        self._tell_initial_facts()
        self._update_display_sets()

    def run_step_by_step(self):
        """
        Generator for step-by-step goal-directed execution.
        Used by both the Pygame visualizer and CLI runner.
        """
        while self.step < self.max_steps and not self.is_done:
            # Check if Goal reached at start of step
            if (self.x, self.y) == self.goal_pos:
                self.is_done = True
                self.reached_goal = True
                self.completion_reason = f"MISSION COMPLETE: Goal ({self.goal_pos[0]},{self.goal_pos[1]}) Reached Successfully!"
                yield {
                    "step": self.step,
                    "rover_pos": (self.x, self.y),
                    "prev_pos": (self.x, self.y),
                    "percepts": {},
                    "tell_log": [],
                    "ask_log": [],
                    "action_type": "GOAL_REACHED",
                    "decision_text": self.completion_reason,
                    "path": None,
                    "visited": set(self.visited),
                    "known_safe": set(self.known_safe),
                    "known_hazard": set(self.known_hazard),
                    "known_radiation": set(self.known_radiation),
                    "sensed_cells": set(self.sensed_cells),
                    "kb_clause_count": self.kb.clause_count,
                    "known_facts_count": len(self.kb.facts),
                    "is_done": True,
                    "reached_goal": True,
                    "completion_reason": self.completion_reason,
                    "hazard_avoidance_events": list(self.hazard_avoidance_events),
                }
                return

            self.step += 1
            prev_pos = (self.x, self.y)

            # 1. PERCEIVE — get percepts from current position
            percepts = self.grid.get_percepts(self.x, self.y)

            # 2. TELL — update KB with percepts
            self._process_percepts(percepts)
            tell_log = self.kb.consume_tell_log()

            # Mark current cell as visited
            self.visited.add((self.x, self.y))
            self.kb.tell(
                make_clause(f"Visited_({self.x},{self.y})"),
                source=f"Visited_({self.x},{self.y})"
            )
            self.kb.consume_tell_log()

            # Check if goal reached after perceiving
            if (self.x, self.y) == self.goal_pos:
                self.is_done = True
                self.reached_goal = True
                self.completion_reason = f"MISSION COMPLETE: Extraction Goal ({self.goal_pos[0]},{self.goal_pos[1]}) Reached!"

            # 3. ASK — evaluate unvisited safe neighbors
            safe_neighbors = self._find_safe_neighbors()
            ask_log = self.kb.consume_ask_log()

            # 4. DECIDE — pick goal-directed move or backtrack
            next_cell = self._decide_goal_directed_move(safe_neighbors)
            self._update_display_sets()

            action_type = "MOVE"
            decision_text = ""
            path = None

            if self.is_done:
                action_type = "GOAL_REACHED"
                decision_text = self.completion_reason
            elif next_cell is not None:
                nx, ny = next_cell
                dist = abs(nx - self.goal_pos[0]) + abs(ny - self.goal_pos[1])
                action_type = "MOVE"
                decision_text = f"Move to ({nx},{ny}) toward Goal [dist={dist}] — inferred Safe by KB"
                path = [(self.x, self.y), (nx, ny)]
                self.x, self.y = nx, ny
                self.path_history.append((nx, ny))

                if (self.x, self.y) == self.goal_pos:
                    self.is_done = True
                    self.reached_goal = True
                    self.completion_reason = f"MISSION COMPLETE: Goal ({self.goal_pos[0]},{self.goal_pos[1]}) Reached Successfully!"
            else:
                backtrack_target = self._find_best_frontier_cell()
                if backtrack_target is not None:
                    path = self._plan_path_to(backtrack_target)
                    if path and len(path) > 1:
                        action_type = "BACKTRACK"
                        dist = abs(backtrack_target[0] - self.goal_pos[0]) + abs(backtrack_target[1] - self.goal_pos[1])
                        decision_text = f"Local path blocked. Backtracking to frontier ({backtrack_target[0]},{backtrack_target[1]}) [dist={dist}] via visited safe route"
                        for px, py in path[1:]:
                            self.x, self.y = px, py
                            self.path_history.append((px, py))
                            if (self.x, self.y) == self.goal_pos:
                                self.is_done = True
                                self.reached_goal = True
                                self.completion_reason = f"MISSION COMPLETE: Goal ({self.goal_pos[0]},{self.goal_pos[1]}) Reached!"
                                break
                    else:
                        self.is_done = True
                        self.completion_reason = "Exploration halted: No further safe paths to goal."
                        action_type = "HALT"
                        decision_text = "Halt: Backtrack path unavailable."
                else:
                    self.is_done = True
                    self.completion_reason = "Exploration halted: All reachable safe cells exhausted."
                    action_type = "HALT"
                    decision_text = "Halt: No unvisited safe cells remaining."

            if self.step >= self.max_steps and not self.is_done:
                self.is_done = True
                self.completion_reason = f"Maximum step limit ({self.max_steps}) reached."

            yield {
                "step": self.step,
                "rover_pos": (self.x, self.y),
                "prev_pos": prev_pos,
                "percepts": percepts,
                "tell_log": tell_log,
                "ask_log": ask_log,
                "action_type": action_type,
                "decision_text": decision_text,
                "path": path,
                "visited": set(self.visited),
                "known_safe": set(self.known_safe),
                "known_hazard": set(self.known_hazard),
                "known_radiation": set(self.known_radiation),
                "sensed_cells": set(self.sensed_cells),
                "kb_clause_count": self.kb.clause_count,
                "known_facts_count": len(self.kb.facts),
                "is_done": self.is_done,
                "reached_goal": self.reached_goal,
                "completion_reason": self.completion_reason,
                "hazard_avoidance_events": list(self.hazard_avoidance_events),
            }

    def run(self):
        """Execute the full agent loop with console logging."""
        self.logger.print_header(self.grid)

        for step_data in self.run_step_by_step():
            step = step_data["step"]
            prev_x, prev_y = step_data["prev_pos"]

            self.logger.print_step_header(
                step, prev_x, prev_y, step_data["kb_clause_count"]
            )
            self.logger.print_percepts(step, step_data["percepts"])
            self.logger.print_tell_log(step, step_data["tell_log"])
            self.logger.print_ask_log(step, step_data["ask_log"])

            self.logger.print_grid(
                self.grid.n,
                (self.x, self.y),
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

        self.logger.print_exploration_complete(
            self.step,
            len(self.visited),
            self.grid.n * self.grid.n,
            self.completion_reason
        )
        return self._build_result()

    def _tell_initial_facts(self):
        """Axioms: Start position is known safe."""
        sx, sy = self.grid.start_pos
        self.kb.tell(
            make_clause(f"Safe_({sx},{sy})"),
            source=f"Axiom: start cell ({sx},{sy}) is safe"
        )
        self.kb.tell(
            make_clause(f"~HazardSignal_({sx},{sy})"),
            source=f"Axiom: no hazard at start"
        )
        self.kb.tell(
            make_clause(f"~RadiationSignal_({sx},{sy})"),
            source=f"Axiom: no radiation at start"
        )
        self.kb.consume_tell_log()

    def _process_percepts(self, percepts):
        """Translate sensor percepts into CNF clauses and assert to KB."""
        for (cx, cy), ptype in percepts.items():
            self.sensed_cells.add((cx, cy))

            if (cx, cy) not in self._rules_added:
                rules = encode_percept_rules(cx, cy)
                self.kb.tell(rules, source=f"Rules for cell ({cx},{cy})")
                self._rules_added.add((cx, cy))

            if ptype == "HazardSignal":
                self.kb.tell(
                    make_clause(f"HazardSignal_({cx},{cy})"),
                    source=f"Perceive: HazardSignal at ({cx},{cy})"
                )
                if (cx, cy) not in self._reported_hazards:
                    self._reported_hazards.add((cx, cy))
                    self.hazard_avoidance_events.append((self.step, cx, cy, "Hazard"))
                    self.logger.print_hazard_avoidance(self.step, cx, cy, "HAZARD (Warning)")

            elif ptype == "RadiationSignal":
                self.kb.tell(
                    make_clause(f"RadiationSignal_({cx},{cy})"),
                    source=f"Perceive: RadiationSignal at ({cx},{cy})"
                )
                if (cx, cy) not in self._reported_hazards:
                    self._reported_hazards.add((cx, cy))
                    self.hazard_avoidance_events.append((self.step, cx, cy, "Radiation"))
                    self.logger.print_hazard_avoidance(self.step, cx, cy, "RADIATION (Zone)")

            elif ptype == "NoSignal":
                self.kb.tell(
                    make_clause(f"~HazardSignal_({cx},{cy})"),
                    source=f"Perceive: no hazard at ({cx},{cy})"
                )
                self.kb.tell(
                    make_clause(f"~RadiationSignal_({cx},{cy})"),
                    source=f"Perceive: no radiation at ({cx},{cy})"
                )

    def _find_safe_neighbors(self):
        """ASK the KB about each neighbor's safety."""
        safe = []
        for nx, ny in self.grid.get_neighbors(self.x, self.y):
            if (nx, ny) in self.visited:
                continue
            if self.kb.ask_is_safe(nx, ny):
                safe.append((nx, ny))
        return safe

    def _decide_goal_directed_move(self, safe_neighbors):
        """Pick the unvisited safe neighbor closest to Goal."""
        if not safe_neighbors:
            return None

        gx, gy = self.goal_pos

        def goal_score(pos):
            nx, ny = pos
            manhattan = abs(nx - gx) + abs(ny - gy)
            unknowns = sum(
                1 for nnx, nny in self.grid.get_neighbors(nx, ny)
                if (nnx, nny) not in self.visited and (nnx, nny) not in self.known_hazard and (nnx, nny) not in self.known_radiation
            )
            return (manhattan, -unknowns)

        safe_neighbors.sort(key=goal_score)
        return safe_neighbors[0]

    def _find_best_frontier_cell(self):
        """Global frontier search: Find closest visited safe cell with explorable neighbors."""
        gx, gy = self.goal_pos
        candidates = []

        for vx, vy in self.visited:
            for nx, ny in self.grid.get_neighbors(vx, vy):
                if (nx, ny) not in self.visited and (nx, ny) not in self.known_hazard and (nx, ny) not in self.known_radiation:
                    path = self._plan_path_to((vx, vy))
                    if path:
                        path_len = len(path)
                        dist_to_goal = abs(nx - gx) + abs(ny - gy)
                        total_cost = path_len + dist_to_goal
                        candidates.append((total_cost, (vx, vy)))

        if not candidates:
            return None

        candidates.sort(key=lambda item: item[0])
        return candidates[0][1]

    def _plan_path_to(self, target):
        """BFS pathfinding over known visited safe cells only."""
        start = (self.x, self.y)
        if start == target:
            return [start]

        queue = deque([(start, [start])])
        seen = {start}

        while queue:
            (cx, cy), path = queue.popleft()
            for nx, ny in self.grid.get_neighbors(cx, cy):
                if (nx, ny) in seen:
                    continue
                if (nx, ny) not in self.visited:
                    continue
                seen.add((nx, ny))
                new_path = path + [(nx, ny)]
                if (nx, ny) == target:
                    return new_path
                queue.append(((nx, ny), new_path))

        return None

    def _update_display_sets(self):
        """Synchronize visualizer sets with KB facts."""
        facts = self.kb.get_known_facts_summary()
        for symbol, value in facts.items():
            if symbol.startswith("Safe_(") and value:
                coords = self._parse_coords(symbol)
                if coords:
                    self.known_safe.add(coords)
            elif symbol.startswith("Blocked_(") and value:
                coords = self._parse_coords(symbol)
                if coords:
                    cx, cy = coords
                    if facts.get(f"HazardSignal_({cx},{cy})", False):
                        self.known_hazard.add(coords)
                    elif facts.get(f"RadiationSignal_({cx},{cy})", False):
                        self.known_radiation.add(coords)
                    else:
                        self.known_hazard.add(coords)

    def _parse_coords(self, symbol):
        """Extract (x, y) from 'Symbol_(x,y)'."""
        try:
            inside = symbol.split("(", 1)[1].rstrip(")")
            parts = inside.split(",")
            return (int(parts[0]), int(parts[1]))
        except (IndexError, ValueError):
            return None

    def _build_result(self):
        """Build summary telemetry dict."""
        return {
            "steps": self.step,
            "visited": set(self.visited),
            "visited_count": len(self.visited),
            "total_cells": self.grid.n * self.grid.n,
            "path_history": list(self.path_history),
            "hazard_avoidance_events": list(self.hazard_avoidance_events),
            "kb_clause_count": self.kb.clause_count,
            "known_facts_count": len(self.kb.facts),
            "reached_goal": self.reached_goal,
            "goal_pos": self.goal_pos,
            "completion_reason": self.completion_reason,
        }
