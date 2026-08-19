# ARES-1 Autonomous Mars Rover — 3D Knowledge-Based Mission Simulation

A state-of-the-art **3D Planetary Simulation** of an autonomous Mars Rover navigating an unknown Martian landscape to reach an **Orbital Extraction Goal** using **Propositional Logic Inference (PL-RESOLUTION)** over a Knowledge Base. Every single rover decision is derived by logical inference — with 100% solvability guarantee, dynamic PBR lighting, articulated 3D rover physics, procedural shaders, and synthesized audio.

---

## 🌟 3D Simulation Features

1. **High-Fidelity 3D Martian Planetary Surface**:
   - Procedural heightmapped Martian terrain with sand dunes, crater basins, and scattered rock boulders.
   - Atmospheric dust particle storm drifting with Martian wind.
   - Dynamic directional sunlight casting soft real-time shadows across the landscape.
   - **Start Base (0,0)**: High-tech Martian Landing Pad with glowing boundary beacon lights.
   - **Goal Extraction Tower (N-1, N-1)**: Sci-Fi Extraction Tower shooting a skyward orbital blue laser beam.

2. **Articulated 3D Mars Rover Model**:
   - 6 individually animated all-terrain treaded wheels that roll with ground velocity and steer dynamically.
   - NASA gold/white foil avionics body, solar panel deck, antenna dish, and pan-tilt camera mast.
   - Dual high-intensity LED headlights casting real-time spotlight cones on terrain.
   - Holographic 3D Sonar radar scanning dome displaying partial-observability perception in real time.
   - Persistent 3D wheel tracks across traversed Martian terrain.

3. **3D Hazards & Radiation Plasma**:
   - **Acid Pools (Hazards)**: Depressed organic fluid basins with toxic green caustic glow (`#22ff44`) and rotating 3D warning triangles.
   - **Radiation Anomalies (Radiation)**: Swirling ethereal volumetric energy spheres with rotating golden/yellow hazard rings (`#f5d741`).

4. **3D Volumetric Fog-of-War**:
   - Unexplored cells are shrouded in dark Martian sandstorm clouds.
   - Perceived cells dissolve with an energy sweep as the rover explores.

5. **4 Camera Modes**:
   - 🎥 **Chase Cam**: Cinematic follow camera tracking behind the rover.
   - 🛰️ **Satellite Cam**: Top-down tactical overview of the entire 3D grid.
   - 🤖 **Rover Mast Cam (FPV)**: First-person rover cockpit view with holographic visor reticle and telemetry.
   - 🚀 **Orbit Cam**: Free 3D orbital control (drag to rotate, scroll to zoom, right-click to pan).

6. **Procedural Mars Audio Engine (Web Audio API)**:
   - Synthesized real-time soundscape: Martian wind ambience, electric servo motor whine, sonar radar pings, hazard alert sirens, and victory fanfare.

7. **Cyberpunk Mission Control HUD**:
   - Live Telemetry: Step counter, `(X, Y)` position, Extraction Goal distance, KB clause count, Avoidance counters.
   - Interactive Speed Controller Slider (`0.25x` to `4.0x`) with quick nudge buttons.
   - Clickable **"REGENERATE MAP [R]"** button for fresh 100% solvable random missions.
   - Live propositional resolution logic stream.

---

## 🚀 Quick Start

### 1. Launch 3D Simulation (Default)
```bash
python main.py
```
*Automatically starts the local server and opens the 3D cinematic simulation in your default browser at `http://localhost:8000`.*

### 2. Custom Size / Port
```bash
python main.py --size 8 --port 8080
```

### 3. Legacy 2D Pygame Visualizer
```bash
python main.py --2d
```

### 4. Headless Console-Only Mode
```bash
python main.py --cli
```

### 5. Run Verification & Stress Tests
```bash
python tests.py
```

---

## 🎮 Interactive Controls

| Control | Action |
|---|---|
| `[SPACE]` | **Pause / Resume** simulation |
| `[RIGHT ARROW]` | **Single Step** forward (when paused) |
| `[R]` | **Regenerate Solvable Map** & restart mission |
| `[C]` | **Cycle Camera Mode** (Chase ➔ Satellite ➔ Mast FPV ➔ Orbit) |
| `[G]` | **Toggle 3D Grid Lines** ON / OFF |
| `[+]` / `[-]` | **Speed Up / Slow Down** simulation rate (or use HUD slider) |
| `[Mouse Drag]` | **Orbit / Look Around** (in Orbit Cam mode) |

---

## 🧠 Propositional Logic Knowledge Base

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
