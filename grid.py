"""
grid.py — Mars Grid World Model with Start/Goal Solvability Guarantee

Cell types: SAFE, HAZARD (Acid Pool), RADIATION (Gas Cloud)
Percepts are only revealed within sensing range (partial observability).

Assumptions:
  - Hazards are sensed at Manhattan distance <= 1 (adjacent cells + current cell).
  - Radiation is sensed at Manhattan distance <= 2 (gives rover more warning).
  - The start cell (0,0) and its immediate neighbors are always SAFE (Landing Pad).
  - The goal cell (N-1, N-1) is always SAFE (Extraction Beacon).
  - Solvability guarantee: Every generated map is validated via BFS pathfinding
    to ensure at least one fully connected safe path exists from Start to Goal.
    If random placement fails after retry threshold, a safe corridor is injected.
"""

from collections import deque
from enum import Enum
import random


class CellType(Enum):
    SAFE = "SAFE"
    HAZARD = "HAZARD"       # Rendered as Acid Pool
    RADIATION = "RADIATION" # Rendered as Gas Cloud


class MarsGrid:
    """N x N grid with Start, Goal, and guaranteed-solvable hazard/radiation placement."""

    def __init__(self, n=6, seed=None, start_pos=(0, 0), goal_pos=None,
                 hazard_density=0.20, radiation_density=0.15):
        """
        Args:
            n: Grid dimension (n x n).
            seed: Random seed for reproducibility. If None, uses random entropy.
            start_pos: (sx, sy) tuple for rover spawn. Default (0,0).
            goal_pos: (gx, gy) tuple for extraction target. Default (n-1, n-1).
            hazard_density: Fraction of cells that are hazards (~20%).
            radiation_density: Fraction of cells that are radiation zones (~15%).
        """
        self.n = n
        self.start_pos = start_pos
        self.goal_pos = goal_pos if goal_pos is not None else (n - 1, n - 1)

        if seed is None:
            self.seed = random.randint(1, 10_000_000)
            self.is_randomized = True
        else:
            self.seed = int(seed)
            self.is_randomized = False

        self.hazard_density = hazard_density
        self.radiation_density = radiation_density
        self.rng = random.Random(self.seed)
        self.cells = {}

        # Protected cells: Start zone and Goal zone are guaranteed SAFE
        self.protected = set()
        # Start region
        for dx in range(-1, 2):
            for dy in range(-1, 2):
                nx, ny = self.start_pos[0] + dx, self.start_pos[1] + dy
                if self.in_bounds(nx, ny):
                    self.protected.add((nx, ny))
        # Goal cell
        self.protected.add(self.goal_pos)

        # Place cells
        for x in range(n):
            for y in range(n):
                if (x, y) in self.protected:
                    self.cells[(x, y)] = CellType.SAFE
                else:
                    roll = self.rng.random()
                    if roll < hazard_density:
                        self.cells[(x, y)] = CellType.HAZARD
                    elif roll < hazard_density + radiation_density:
                        self.cells[(x, y)] = CellType.RADIATION
                    else:
                        self.cells[(x, y)] = CellType.SAFE

    def in_bounds(self, x, y):
        """Check if (x, y) is within grid boundaries."""
        return 0 <= x < self.n and 0 <= y < self.n

    def get_neighbors(self, x, y):
        """Return list of valid (nx, ny) neighbors (4-directional)."""
        neighbors = []
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = x + dx, y + dy
            if self.in_bounds(nx, ny):
                neighbors.append((nx, ny))
        return neighbors

    def get_percepts(self, x, y):
        """
        Return percepts visible from position (x, y).

        Partial observability:
          - The rover senses its own cell directly.
          - Hazard signals (acid pools) detected at Manhattan distance <= 1.
          - Radiation signals (gas clouds) detected at Manhattan distance <= 2.
          - Cells beyond sensing range return no percept.

        Returns:
            dict mapping (cx, cy) -> percept_type string:
              'HazardSignal'    -- hazard detected at that cell
              'RadiationSignal' -- radiation detected at that cell
              'NoSignal'        -- cell sensed and found clear
        """
        percepts = {}

        # Cells within Manhattan distance 2 (radiation sensing range)
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                dist = abs(dx) + abs(dy)
                if dist > 2:
                    continue
                cx, cy = x + dx, y + dy
                if not self.in_bounds(cx, cy):
                    continue

                cell_type = self.cells[(cx, cy)]

                if cell_type == CellType.RADIATION and dist <= 2:
                    percepts[(cx, cy)] = "RadiationSignal"
                elif cell_type == CellType.HAZARD and dist <= 1:
                    percepts[(cx, cy)] = "HazardSignal"
                elif dist <= 1:
                    # Within hazard sensing range and no threat detected
                    if (cx, cy) not in percepts:
                        percepts[(cx, cy)] = "NoSignal"

        return percepts

    def find_safe_path(self, start=None, goal=None):
        """
        BFS pathfinder checking for a continuous SAFE path between start and goal.
        Returns:
            list of (x, y) coordinates if path exists, or None.
        """
        s = start if start is not None else self.start_pos
        g = goal if goal is not None else self.goal_pos

        if self.cells.get(s) != CellType.SAFE or self.cells.get(g) != CellType.SAFE:
            return None

        queue = deque([(s, [s])])
        seen = {s}

        while queue:
            (cx, cy), path = queue.popleft()
            if (cx, cy) == g:
                return path

            for nx, ny in self.get_neighbors(cx, cy):
                if (nx, ny) not in seen and self.cells.get((nx, ny)) == CellType.SAFE:
                    seen.add((nx, ny))
                    queue.append(((nx, ny), path + [(nx, ny)]))

        return None

    def inject_safe_corridor(self, start=None, goal=None):
        """
        Fallback guarantee: Carves a randomized connected safe corridor from start to goal.
        Ensures the map is 100% solvable without hanging or failing.
        """
        s = start if start is not None else self.start_pos
        g = goal if goal is not None else self.goal_pos

        cx, cy = s
        self.cells[(cx, cy)] = CellType.SAFE

        # Random walk biased toward goal
        while (cx, cy) != g:
            dx = 1 if g[0] > cx else (-1 if g[0] < cx else 0)
            dy = 1 if g[1] > cy else (-1 if g[1] < cy else 0)

            # Move horizontally or vertically toward goal
            if dx != 0 and dy != 0:
                if self.rng.random() < 0.5:
                    cx += dx
                else:
                    cy += dy
            elif dx != 0:
                cx += dx
            elif dy != 0:
                cy += dy

            self.cells[(cx, cy)] = CellType.SAFE

    @classmethod
    def create_solvable_grid(cls, n=6, seed=None, start_pos=(0, 0), goal_pos=None,
                             hazard_density=0.20, radiation_density=0.15, max_attempts=200):
        """
        Factory method: Generates grids until a full safe path from Start to Goal exists.
        If random layout generation does not find a path within max_attempts,
        a safe corridor is injected into the last attempt, guaranteeing 100% solvability.

        Returns:
            (MarsGrid instance, attempts_taken: int, safe_path: list)
        """
        g_pos = goal_pos if goal_pos is not None else (n - 1, n - 1)

        for attempt in range(1, max_attempts + 1):
            cur_seed = None if seed is None else (seed + attempt - 1)
            grid = cls(n=n, seed=cur_seed, start_pos=start_pos, goal_pos=g_pos,
                       hazard_density=hazard_density, radiation_density=radiation_density)

            path = grid.find_safe_path()
            if path is not None:
                return grid, attempt, path

        # Fallback corridor injection
        grid.inject_safe_corridor()
        path = grid.find_safe_path()
        return grid, max_attempts, path

    def get_true_cell(self, x, y):
        """Debug/test helper -- returns the true cell type. NOT used by agent."""
        return self.cells.get((x, y))

    def get_stats(self):
        """Return counts of cell types on the grid."""
        safe_cnt = sum(1 for c in self.cells.values() if c == CellType.SAFE)
        hazard_cnt = sum(1 for c in self.cells.values() if c == CellType.HAZARD)
        rad_cnt = sum(1 for c in self.cells.values() if c == CellType.RADIATION)
        total = self.n * self.n
        return {
            "total": total,
            "safe": safe_cnt,
            "hazard": hazard_cnt,
            "radiation": rad_cnt,
            "safe_pct": (safe_cnt / total) * 100,
            "hazard_pct": (hazard_cnt / total) * 100,
            "rad_pct": (rad_cnt / total) * 100,
        }

    def __str__(self):
        """Debug view showing the true grid (god-vision). Not shown to agent."""
        symbols = {CellType.SAFE: ".", CellType.HAZARD: "H", CellType.RADIATION: "X"}
        header = "  " + " ".join(str(i) for i in range(self.n))
        rows = [header]
        for y in range(self.n):
            row_items = []
            for x in range(self.n):
                if (x, y) == self.start_pos:
                    row_items.append("S")
                elif (x, y) == self.goal_pos:
                    row_items.append("G")
                else:
                    row_items.append(symbols[self.cells[(x, y)]])
            rows.append(f"{y} " + " ".join(row_items))
        return "\n".join(rows)
