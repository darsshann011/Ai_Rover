"""
main.py — Main Entry Point for ARES-1 Autonomous Mars Rover KB-Agent Simulation

Modes:
  1. Default: Cinematic 3D WebGL Simulation (Three.js + Shaders + Web Audio Synth)
     Auto-launches local server and opens browser to http://localhost:8000
  2. --2d: 2D Pygame Simulation with photographic terrain and sprite
  3. --cli / --no-gui: Headless terminal mode with live proposition resolution logs

Usage:
    python main.py             # 3D Cinematic Simulation (Default)
    python main.py --2d        # 2D Pygame visualizer
    python main.py --cli       # Headless terminal-only simulation
    python main.py --size 8    # 8x8 grid
    python main.py --port 8080 # Custom 3D server port
"""

import argparse
import sys
import threading
import time
import webbrowser
from grid import MarsGrid, CellType
from agent import MarsRoverAgent
from logger import RoverLogger
from server import start_server


def run_3d_simulation(args):
    """Launch 3D WebGL Three.js simulation server and open browser."""
    port = args.port
    print("=" * 65)
    print("  ARES-1 MARS ROVER -- 3D CINEMATIC PLANETARY SIMULATION")
    print("=" * 65)
    print(f"  Starting local 3D server on port {port}...")
    print(f"  URL: http://localhost:{port}")
    print("  Press Ctrl+C to terminate simulation.")
    print("=" * 65 + "\n")

    httpd = start_server(port=port, size=args.size, seed=args.seed)

    # Open default browser automatically in background thread
    def open_browser():
        time.sleep(0.8)
        webbrowser.open(f"http://localhost:{port}")

    threading.Thread(target=open_browser, daemon=True).start()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[3D Server] Shutting down simulation...")
        httpd.server_close()
        return 0


def run_2d_or_cli_simulation(args):
    """Run 2D Pygame or headless terminal simulation."""
    start_pos = (0, 0)
    goal_pos = (args.size - 1, args.size - 1)

    grid, attempts, true_path = MarsGrid.create_solvable_grid(
        n=args.size,
        seed=args.seed,
        start_pos=start_pos,
        goal_pos=goal_pos,
        hazard_density=args.hazard_density,
        radiation_density=args.radiation_density,
    )

    stats = grid.get_stats()
    path_len = len(true_path) if true_path else 0

    print("=" * 65)
    print("  ARES-1 AUTONOMOUS MARS ROVER -- MISSION INITIALIZATION")
    print("=" * 65)
    print(f"  Random Seed:          {grid.seed} {'(Randomized)' if grid.is_randomized else '(Fixed Seed)'}")
    print(f"  Grid Dimensions:      {args.size}x{args.size} ({stats['total']} cells)")
    print(f"  Terrain Distribution: Safe: {stats['safe']} ({stats['safe_pct']:.1f}%) | Hazards: {stats['hazard']} ({stats['hazard_pct']:.1f}%) | Rad: {stats['radiation']} ({stats['rad_pct']:.1f}%)")
    print(f"  [INIT] Path validated: Start{start_pos} -> Goal{goal_pos}, length {path_len} cells (attempt #{attempts})")
    print(f"  Display Mode:         {'Headless Console' if args.no_gui else '2D Pygame Visualizer'}")
    print("=" * 65 + "\n")

    logger = RoverLogger(use_color=not args.no_color)
    agent = MarsRoverAgent(grid, logger=logger, max_steps=args.max_steps)

    if not args.no_gui:
        try:
            from visualizer import MarsRoverVisualizer
            visualizer = MarsRoverVisualizer(
                grid=grid,
                agent=agent,
                logger=logger,
                step_delay=args.speed
            )
            result_code = visualizer.run()
            if result_code == "RESTART":
                args.seed = None
                return "RESTART"
        except ImportError as e:
            print(f"[Warning] Pygame not available ({e}). Falling back to CLI mode.")
            agent.run()
        except Exception as e:
            print(f"[Simulator] GUI session ended: {e}")
    else:
        agent.run()

    result = agent._build_result()
    print("\n" + "=" * 65)
    print("  MISSION TELEMETRY SUMMARY")
    print("=" * 65)
    print(f"  Seed Used:            {grid.seed}")
    print(f"  Mission Status:       {'GOAL REACHED! [OK]' if result['reached_goal'] else 'INCOMPLETE'}")
    print(f"  Total Steps Taken:    {result['steps']}")
    print(f"  Cells Visited:        {result['visited_count']} / {result['total_cells']}")
    print(f"  KB Clauses (final):   {result['kb_clause_count']}")
    print(f"  Known Facts:          {result['known_facts_count']}")
    print(f"  Hazard/Rad Avoided:   {len(result['hazard_avoidance_events'])}")

    violations = [
        (vx, vy, grid.get_true_cell(vx, vy))
        for (vx, vy) in result['visited']
        if grid.get_true_cell(vx, vy) != CellType.SAFE
    ]

    if violations:
        print(f"\n  [!] SAFETY VIOLATIONS DETECTED: {len(violations)}")
    else:
        print(f"\n  [OK] SAFETY INVARIANT VERIFIED: Rover never entered a hazard or radiation zone.")

    print("=" * 65)
    return 0 if not violations and result['reached_goal'] else 1


def main():
    parser = argparse.ArgumentParser(
        description="ARES-1 Autonomous Mars Rover — 3D Knowledge-Based Agent Simulation"
    )
    parser.add_argument(
        "--size", type=int, default=6,
        help="Grid dimension N. Default: 6"
    )
    parser.add_argument(
        "--seed", type=int, default=None,
        help="Random seed. If None, generates a fresh random map on every run."
    )
    parser.add_argument(
        "--port", type=int, default=8000,
        help="Port for 3D web server. Default: 8000"
    )
    parser.add_argument(
        "--hazard-density", type=float, default=0.20,
        help="Fraction of cells that are hazards. Default: 0.20"
    )
    parser.add_argument(
        "--radiation-density", type=float, default=0.15,
        help="Fraction of cells that are radiation zones. Default: 0.15"
    )
    parser.add_argument(
        "--speed", type=float, default=1.0,
        help="Decision step delay in seconds. Default: 1.0"
    )
    parser.add_argument(
        "--max-steps", type=int, default=300,
        help="Maximum simulation steps. Default: 300"
    )
    parser.add_argument(
        "--2d", action="store_true", dest="mode_2d",
        help="Run in legacy 2D Pygame visualizer mode."
    )
    parser.add_argument(
        "--cli", "--no-gui", action="store_true", dest="no_gui",
        help="Run in headless terminal mode without 3D WebGL or Pygame."
    )
    parser.add_argument(
        "--no-color", action="store_true",
        help="Disable ANSI color codes in console output."
    )
    args = parser.parse_args()

    # If --cli or --2d is specified, run standard simulation loop
    if args.no_gui or args.mode_2d:
        while True:
            status = run_2d_or_cli_simulation(args)
            if status != "RESTART":
                break
        return 0

    # Default: Run 3D Cinematic WebGL Simulation
    return run_3d_simulation(args)


if __name__ == "__main__":
    sys.exit(main())
