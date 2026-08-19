# Autonomous Mars Rover — Goal-Directed KB Agent with Organic Terrain

A simulated Mars rover that navigates an unknown Martian planetary grid to reach an **Extraction Goal** using **propositional logic inference (PL-RESOLUTION)** over a Knowledge Base. Every movement decision is derived from `ASK(KB, query)` — with guaranteed 100% solvability and organic procedural terrain visuals.

---

## 🌟 What's New in this Release

1. **Goal-Directed Mission Navigation**:
   - Fixed **Start Landing Pad `(0,0)`** and **Extraction Beacon `(N-1, N-1)`**.
   - Solvability Guarantee: Every generated map is verified via BFS pathfinding before mission start. If random hazards block all routes, a safe corridor is injected, guaranteeing 100% solvability.
   - Goal-Directed Heuristic: Rover prioritizes KB-inferred safe cells that reduce Manhattan distance to Goal, with global frontier backtracking when local paths are blocked.
2. **Organic Planetary Terrain (No Hard Grid Lines)**:
   - **Continuous Martian Surface**: Procedural multi-layer rust soil (`#B7410E`) with dust speckles, rock boulders, and impact craters.
   - **Acid Pools (Hazards)**: Irregular organic bubbling green fluid pools with scorched mineral rims, caustic highlights, and rising bubble particles.
   - **Gas Clouds (Radiation)**: Billowing, soft-edged semi-transparent toxic vapor clouds with dynamic drifting particle animations.
   - **Soft Atmospheric Fog-of-War**: Dark atmospheric dust shroud that organically clears with feathered radial light around perceived areas.
3. **Animated Rover & Directional Trails**:
   - Directional facing: The rover rotates to face its movement vector.
   - Persistent tire tracks: Leaves realistic wheel tracks on traveled terrain.
   - Smooth 60 FPS interpolation (`lerp`) with controllable decision step rates.

---

## Quick Start

### 1. Mars-Themed Pygame Simulation (Default)
```bash
python main.py                  # Pygame GUI with fresh random map (100% solvable)
python main.py --size 8         # 8x8 grid simulation
python main.py --speed 0.3      # Fast animation rate (0.3s per step)
python main.py --seed 42        # Fixed reproducible seed
```

### 2. Headless / Console-Only Mode
```bash
python main.py --no-gui         # Clean live console logs
python main.py --no-gui --no-color # Without ANSI colors
```

### 3. Run Verification & Stress Tests
```bash
python tests.py
```

---

## Interactive Pygame Controls

| Key | Action |
|---|---|
| `[SPACE]` | **Pause / Resume** simulation |
| `[RIGHT ARROW]` | **Single Step** forward (when paused) |
| `[+]` / `[-]` | **Speed Up / Slow Down** animation rate |
| `[R]` | **Generate New Solvable Map** & restart |
| `[ESC]` | **Quit** simulation |

---

## Propositional Symbols & Inference

Each cell `(x,y)` is modeled with the following propositional symbols:

| Symbol | Meaning |
|---|---|
| `HazardSignal_(x,y)` | An acid pool hazard was perceived at/adjacent to cell `(x,y)` |
| `RadiationSignal_(x,y)` | Toxic radiation gas cloud detected at cell `(x,y)` |
| `Safe_(x,y)` | Cell `(x,y)` is inferred safe to enter |
| `Visited_(x,y)` | Rover has physically visited cell `(x,y)` |
| `Blocked_(x,y)` | Cell `(x,y)` is blocked (hazard or radiation confirmed) |

### Core Rules (CNF Clauses)

1. **Hazard Avoidance**: `HazardSignal_(x,y) → Blocked_(x,y)`
   $$\{\neg \text{HazardSignal\_}(x,y), \text{Blocked\_}(x,y)\}$$
2. **Radiation Avoidance**: `RadiationSignal_(x,y) → Blocked_(x,y)`
   $$\{\neg \text{RadiationSignal\_}(x,y), \text{Blocked\_}(x,y)\}$$
3. **Safety Inference**: $\neg \text{HazardSignal\_}(x,y) \wedge \neg \text{RadiationSignal\_}(x,y) \rightarrow \text{Safe\_}(x,y)$
   $$\{\text{HazardSignal\_}(x,y), \text{RadiationSignal\_}(x,y), \text{Safe\_}(x,y)\}$$
4. **Blocked Implies Unsafe**: $\text{Blocked\_}(x,y) \rightarrow \neg \text{Safe\_}(x,y)$
   $$\{\neg \text{Blocked\_}(x,y), \neg \text{Safe\_}(x,y)\}$$

---

## Architecture & Causality Invariant

```
       ┌────────────────────────┐
       │   Mars 2D Grid World   │ (Solvability validated: Start -> Goal)
       └───────────┬────────────┘
                   │ get_percepts(x,y)
                   ▼
       ┌────────────────────────┐
       │   TELL(KB, percept)    │ (Eager unit propagation -> derives facts)
       └───────────┬────────────┘
                   │
                   ▼
       ┌────────────────────────┐
       │   ASK(KB, Safe_(nx,ny))│ (PL-RESOLUTION: refutation theorem proving)
       └───────────┬────────────┘
                   │
                   ▼
       ┌────────────────────────┐
       │   GOAL-DIRECTED MOVE   │ (A* distance to Goal + frontier backtracking)
       └───────────┬────────────┘
                   │
         ┌─────────┴─────────┐
         ▼                   ▼
┌──────────────────┐ ┌──────────────────────┐
│ Live Console Log │ │ Organic Pygame Render│ (Acid pools, gas clouds, trails)
└──────────────────┘ └──────────────────────┘
```

> **Strict Causality Invariant**: The console log and KB inference always complete *before* the rover moves on screen. The GUI never reveals any cell that has not been perceived by the KB.

---

## File Structure

| File | Description |
|---|---|
| [`grid.py`](file:///d:/Ai_rover/grid.py) | Grid world model, Start/Goal definitions, solvability validation, and corridor injector. |
| [`kb_engine.py`](file:///d:/Ai_rover/kb_engine.py) | Propositional KB, CNF clauses, Unit Propagation, and `PL-RESOLUTION` engine. |
| [`agent.py`](file:///d:/Ai_rover/agent.py) | Goal-directed KB agent with heuristic pathing, global frontier backtracking, and safety invariant. |
| [`visualizer.py`](file:///d:/Ai_rover/visualizer.py) | Mars-themed organic renderer (acid pools, gas clouds, landing pad, extraction beacon, tread trails). |
| [`logger.py`](file:///d:/Ai_rover/logger.py) | Timestamped step-correlated console logger with ASCII fallback grid. |
| [`main.py`](file:///d:/Ai_rover/main.py) | Simulation entry point supporting both Pygame GUI and Headless CLI modes. |
| [`tests.py`](file:///d:/Ai_rover/tests.py) | Verification & stress test suite (50-run map solvability, 10-run goal completion). |
