"""
main.py — Entry Point for Autonomous Mars Rover Goal-Directed Simulation

Features:
  - 100% Solvable Start → Goal guaranteed map generation
  - Mars-Themed Organic Pygame Visualizer (acid pools, gas clouds, landing pad, extraction tower)
  - Headless Console Mode (--no-gui / --cli)
  - Live synchronized telemetry and resolution inference logs

Usage:
    python main.py                  # Pygame GUI with fresh random map (Guaranteed solvable)
    python main.py --no-gui         # Terminal-only mode
    python main.py --size 8         # 8x8 grid
    python main.py --speed 0.4      # Faster Pygame decision step rate (0.4s)
    python main.py --seed 42        # Fixed reproducible seed
"""

import argparse
import sys
from grid import MarsGrid, CellType
from agent import MarsRoverAgent
from logger import RoverLogger


def run_simulation(args):
    """Run a single Mars rover simulation session."""
    start_pos = (0, 0)
    goal_pos = (args.size - 1, args.size - 1)

    # 1. Create a guaranteed-solvable grid
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
    print("  ARES-1 AUTONOMOUS MARS ROVER — MISSION INITIALIZATION")
    print("=" * 65)
    print(f"  Random Seed:          {grid.seed} {'(Randomized)' if grid.is_randomized else '(Fixed Seed)'}")
    print(f"  Grid Dimensions:      {args.size}x{args.size} ({stats['total']} cells)")
    print(f"  Terrain Distribution: Safe: {stats['safe']} ({stats['safe_pct']:.1f}%) | Hazards (Acid): {stats['hazard']} ({stats['hazard_pct']:.1f}%) | Rad (Gas): {stats['radiation']} ({stats['rad_pct']:.1f}%)")
    print(f"  [INIT] Path validated: Start{start_pos} → Goal{goal_pos}, length {path_len} cells, hazards={stats['hazard']}, radiation={stats['radiation']} (attempt #{attempts})")
    print(f"  Display Mode:         {'Headless Console' if args.no_gui else 'Organic Mars Pygame GUI + Live Telemetry'}")
    print("=" * 65 + "\n")

    # 2. Setup logger
    logger = RoverLogger(use_color=not args.no_color)

    # 3. Setup agent
    agent = MarsRoverAgent(grid, logger=logger, max_steps=args.max_steps)

    # 4. Launch Pygame GUI or CLI runner
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
                print("\n[Simulator] Regenerating fresh guaranteed-solvable map...\n")
                args.seed = None
                return "RESTART"
        except ImportError as e:
            print(f"[Warning] Pygame not available ({e}). Falling back to CLI mode.")
            agent.run()
        except Exception as e:
            print(f"[Simulator] GUI session ended: {e}")
    else:
        agent.run()

    # 5. Final Telemetry Summary & Verification
    result = agent._build_result()
    print("\n" + "=" * 65)
    print("  MISSION TELEMETRY SUMMARY")
    print("=" * 65)
    print(f"  Seed Used:            {grid.seed}")
    print(f"  Mission Status:       {'GOAL REACHED! ✓' if result['reached_goal'] else 'INCOMPLETE'}")
    print(f"  Total Steps Taken:    {result['steps']}")
    print(f"  Cells Visited:        {result['visited_count']} / {result['total_cells']}")
    print(f"  KB Clauses (final):   {result['kb_clause_count']}")
    print(f"  Known Facts:          {result['known_facts_count']}")
    print(f"  Hazard/Rad Avoided:   {len(result['hazard_avoidance_events'])}")

    if result['hazard_avoidance_events']:
        print("\n  Hazard Avoidance Log:")
        for step, hx, hy, htype in result['hazard_avoidance_events']:
            print(f"    Step {step}: {htype} at ({hx},{hy}) — avoided by KB inference")

    # Verify Safety Invariant
    violations = []
    for (vx, vy) in result['visited']:
        cell = grid.get_true_cell(vx, vy)
        if cell != CellType.SAFE:
            violations.append((vx, vy, cell))

    if violations:
        print(f"\n  ⚠ SAFETY VIOLATIONS DETECTED: {len(violations)}")
        for vx, vy, cell in violations:
            print(f"    ({vx},{vy}) = {cell.value} — INVALID MOVEMENT!")
    else:
        print(f"\n  ✓ SAFETY INVARIANT VERIFIED: Rover never entered a hazard or radiation zone.")

    print("=" * 65)
    return 0 if not violations and result['reached_goal'] else 1


def main():
    parser = argparse.ArgumentParser(
        description="Autonomous Mars Rover — Goal-Directed KB Agent with Organic Terrain"
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
        "--hazard-density", type=float, default=0.20,
        help="Fraction of cells that are hazards. Default: 0.20"
    )
    parser.add_argument(
        "--radiation-density", type=float, default=0.15,
        help="Fraction of cells that are radiation zones. Default: 0.15"
    )
    parser.add_argument(
        "--speed", type=float, default=1.0,
        help="Pygame decision step delay in seconds. Default: 1.0 (readable pacing)"
    )
    parser.add_argument(
        "--max-steps", type=int, default=300,
        help="Maximum simulation steps. Default: 300"
    )
    parser.add_argument(
        "--no-gui", "--cli", action="store_true", dest="no_gui",
        help="Run in headless terminal mode without opening Pygame."
    )
    parser.add_argument(
        "--no-color", action="store_true",
        help="Disable ANSI color codes in console output."
    )
    args = parser.parse_args()

    while True:
        status = run_simulation(args)
        if status != "RESTART":
            break


if __name__ == "__main__":
    sys.exit(main())
