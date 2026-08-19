"""
logger.py — Live KB Logging & ASCII Map Renderer

Provides step-by-step console output showing:
  - TELL operations with newly added clauses and inferred facts
  - ASK operations with query results and resolution details
  - ASCII grid visualization synchronized with KB state
  - KB clause count delta per step
"""


def format_clause(clause):
    """Format a frozenset clause as a readable string like {A, ~B, C}."""
    if not clause:
        return "{}"
    sorted_lits = sorted(clause, key=lambda x: x.lstrip("~"))
    return "{" + ", ".join(sorted_lits) + "}"


def format_literal_friendly(literal):
    """Format a literal in a human-friendly way."""
    return literal


class RoverLogger:
    """Handles all console output for the rover simulation."""

    # ANSI color codes for terminal output
    COLORS = {
        "reset":    "\033[0m",
        "bold":     "\033[1m",
        "red":      "\033[91m",
        "green":    "\033[92m",
        "yellow":   "\033[93m",
        "blue":     "\033[94m",
        "magenta":  "\033[95m",
        "cyan":     "\033[96m",
        "gray":     "\033[90m",
    }

    def __init__(self, use_color=True):
        self.use_color = use_color

    def _c(self, color, text):
        """Apply color to text if color output is enabled."""
        if self.use_color and color in self.COLORS:
            return f"{self.COLORS[color]}{text}{self.COLORS['reset']}"
        return text

    def print_header(self, grid):
        """Print simulation header with true grid (for reference)."""
        print(self._c("bold", "=" * 60))
        print(self._c("bold", "   AUTONOMOUS MARS ROVER -- KB Agent Simulation"))
        print(self._c("bold", "=" * 60))
        print(f"\nGrid size: {grid.n}x{grid.n} | Seed: {grid.seed}")
        print(self._c("gray", "\nTrue grid layout (god-vision -- NOT available to rover):"))
        print(self._c("gray", str(grid)))
        print(self._c("bold", "\n" + "-" * 60))
        print()

    def print_step_header(self, step, rover_x, rover_y, kb_clause_count):
        """Print the header for a new step."""
        print(self._c("bold", f"\n{'='*60}"))
        print(self._c("bold", f"  Step {step}  |  Rover at ({rover_x},{rover_y})  |  KB: {kb_clause_count} clauses"))
        print(self._c("bold", f"{'='*60}"))

    def print_percepts(self, step, percepts):
        """Print what the rover perceives at this step."""
        print(self._c("cyan", f"\n  [Step {step}] PERCEIVE:"))
        if not percepts:
            print(self._c("gray", "    No new percepts."))
            return
        for (x, y), ptype in sorted(percepts.items()):
            if ptype == "HazardSignal":
                print(self._c("red", f"    [!] HazardSignal at ({x},{y})"))
            elif ptype == "RadiationSignal":
                print(self._c("red", f"    [*] RadiationSignal at ({x},{y})"))
            else:
                print(self._c("green", f"    [+] NoSignal at ({x},{y}) -- clear"))

    def print_tell_log(self, step, tell_entries):
        """Print TELL operations from this step."""
        for entry in tell_entries:
            source = entry["source"]
            new_clauses = entry["new_clauses"]
            inferred = entry["inferred"]
            total = entry["total_clauses"]

            if new_clauses:
                clause_strs = [format_clause(c) for c in new_clauses[:5]]
                clause_display = ", ".join(clause_strs)
                if len(new_clauses) > 5:
                    clause_display += f" ... (+{len(new_clauses)-5} more)"
                print(self._c("yellow", f"  [Step {step}] TELL: {source}"))
                print(self._c("gray", f"    Added {len(new_clauses)} clause(s): {clause_display}"))
                print(self._c("gray", f"    KB total: {total} clauses"))

            if inferred:
                for symbol, value in inferred:
                    val_str = "TRUE" if value else "FALSE"
                    color = "green" if value and "Safe" in symbol else "red" if not value else "blue"
                    print(self._c(color, f"    -> Inferred: {symbol} = {val_str} (unit propagation)"))

    def print_ask_log(self, step, ask_entries):
        """Print ASK queries and results from this step."""
        for entry in ask_entries:
            query = entry["query"]
            positive = entry["positive"]
            result = entry["result"]
            method = entry["method"]

            query_str = query if positive else f"~{query}"
            result_str = "TRUE" if result else "FALSE"
            result_color = "green" if result else "red"

            print(self._c("magenta",
                f"  [Step {step}] ASK: {query_str}? -> "
                f"{self._c(result_color, result_str)} ({method})"))

    def print_decision(self, step, decision_text):
        """Print the agent's movement decision."""
        print(self._c("blue", f"  [Step {step}] DECIDE: {decision_text}"))

    def print_grid(self, grid_n, rover_pos, visited, known_safe, known_hazard, known_radiation, sensed_cells):
        """
        Print ASCII grid showing the rover's knowledge state.

        Symbols:
          R  = Rover current position
          S  = Confirmed safe (visited)
          s  = Inferred safe (not yet visited)
          H  = Known hazard
          X  = Known radiation zone
          .  = Unknown / not yet sensed
          ?  = Sensed but status uncertain
        """
        print()
        header = "    " + "  ".join(f"{i}" for i in range(grid_n))
        print(self._c("gray", header))
        print(self._c("gray", "  +" + "---" * grid_n + "+"))

        for y in range(grid_n):
            row_parts = []
            for x in range(grid_n):
                pos = (x, y)
                if pos == rover_pos:
                    row_parts.append(self._c("bold", " R "))
                elif pos in known_hazard:
                    row_parts.append(self._c("red", " H "))
                elif pos in known_radiation:
                    row_parts.append(self._c("red", " X "))
                elif pos in visited:
                    row_parts.append(self._c("green", " S "))
                elif pos in known_safe:
                    row_parts.append(self._c("cyan", " s "))
                elif pos in sensed_cells:
                    row_parts.append(self._c("yellow", " ? "))
                else:
                    row_parts.append(" . ")
            print(f"  {self._c('gray', '|')}{''.join(row_parts)}{self._c('gray', '|')}  {y}")

        print(self._c("gray", "  +" + "---" * grid_n + "+"))
        print(self._c("gray", "  Legend: R=Rover  S=Safe(visited)  s=safe(inferred)  H=Hazard  X=Radiation  .=Unknown"))

    def print_exploration_complete(self, step, visited_count, total_cells, reason):
        """Print exploration summary."""
        print(self._c("bold", f"\n{'='*60}"))
        print(self._c("bold", "  EXPLORATION COMPLETE"))
        print(self._c("bold", f"{'='*60}"))
        print(f"  Total steps: {step}")
        print(f"  Cells visited: {visited_count} / {total_cells}")
        print(f"  Reason: {reason}")
        print(self._c("bold", f"{'='*60}\n"))

    def print_hazard_avoidance(self, step, x, y, hazard_type):
        """Highlight a hazard avoidance event."""
        print(self._c("red", f"\n  +--------------------------------------------+"))
        print(self._c("red", f"  |  HAZARD AVOIDANCE EVENT at Step {step:<9}  |"))
        print(self._c("red", f"  |  {hazard_type} detected at ({x},{y}){' '*(26-len(hazard_type))}|"))
        print(self._c("red", f"  |  KB inference: cell is BLOCKED -> skip     |"))
        print(self._c("red", f"  +--------------------------------------------+\n"))

    def print_backtrack(self, step, reason):
        """Log a backtrack event."""
        print(self._c("yellow", f"  [Step {step}] BACKTRACK: {reason}"))

    def print_path(self, step, path):
        """Log the planned path."""
        if path:
            path_str = " -> ".join(f"({x},{y})" for x, y in path)
            print(self._c("gray", f"  [Step {step}] PATH: {path_str}"))
