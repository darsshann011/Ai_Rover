"""
tests.py — Comprehensive Verification & Stress Testing for Mars Rover KB Agent

Unit & Stress Tests:
  1. Hazard percept blocks movement (ASK Safe returns False)
  2. Radiation percept blocks entry (ASK Safe returns False)
  3. No-signal percept infers safety (ASK Safe returns True)
  4. Manual resolution correctness on a known clause set
  5. Partial observability (sensing range strictly enforced)
  6. 50-Run Start->Goal Map Solvability Stress Test (100% path guaranteed)
  7. 10-Run Goal-Directed Navigation Stress Test (100% Goal Reachability)

Run with:  python tests.py
"""

import io
import sys
from kb_engine import KnowledgeBase, encode_percept_rules, make_clause
from grid import MarsGrid, CellType
from agent import MarsRoverAgent
from logger import RoverLogger


def test_hazard_blocks_movement():
    """TEST 1: TELL a hazard percept -> ASK Safe returns False."""
    print("TEST 1: Hazard percept blocks movement")
    kb = KnowledgeBase()
    rules = encode_percept_rules(1, 1)
    kb.tell(rules, source="Rules for (1,1)")
    kb.tell(make_clause("HazardSignal_(1,1)"), source="Percept: hazard at (1,1)")

    result_safe = kb.ask_is_safe(1, 1)
    result_blocked = kb.ask_is_blocked(1, 1)

    assert not result_safe, f"Expected Safe_(1,1) = False, got {result_safe}"
    assert result_blocked, f"Expected Blocked_(1,1) = True, got {result_blocked}"
    print(f"  [OK] Safe_(1,1) = {result_safe} (correctly False)")
    print(f"  [OK] Blocked_(1,1) = {result_blocked} (correctly True)")
    print("  PASSED\n")


def test_radiation_blocks_entry():
    """TEST 2: TELL a radiation percept -> ASK Safe returns False."""
    print("TEST 2: Radiation percept blocks entry")
    kb = KnowledgeBase()
    rules = encode_percept_rules(2, 2)
    kb.tell(rules, source="Rules for (2,2)")
    kb.tell(make_clause("RadiationSignal_(2,2)"), source="Percept: radiation at (2,2)")

    result_safe = kb.ask_is_safe(2, 2)
    result_blocked = kb.ask_is_blocked(2, 2)

    assert not result_safe, f"Expected Safe_(2,2) = False, got {result_safe}"
    assert result_blocked, f"Expected Blocked_(2,2) = True, got {result_blocked}"
    print(f"  [OK] Safe_(2,2) = {result_safe} (correctly False)")
    print(f"  [OK] Blocked_(2,2) = {result_blocked} (correctly True)")
    print("  PASSED\n")


def test_safe_inference():
    """TEST 3: TELL no hazard AND no radiation -> ASK Safe returns True."""
    print("TEST 3: No-signal percept infers safety")
    kb = KnowledgeBase()
    rules = encode_percept_rules(3, 3)
    kb.tell(rules, source="Rules for (3,3)")
    kb.tell(make_clause("~HazardSignal_(3,3)"), source="No hazard at (3,3)")
    kb.tell(make_clause("~RadiationSignal_(3,3)"), source="No radiation at (3,3)")

    result_safe = kb.ask_is_safe(3, 3)
    result_blocked = kb.ask_is_blocked(3, 3)

    assert result_safe, f"Expected Safe_(3,3) = True, got {result_safe}"
    assert not result_blocked, f"Expected Blocked_(3,3) = False, got {result_blocked}"
    print(f"  [OK] Safe_(3,3) = {result_safe} (correctly True)")
    print(f"  [OK] Blocked_(3,3) = {result_blocked} (correctly False)")
    print("  PASSED\n")


def test_resolution_manual():
    """TEST 4: Manual resolution correctness check."""
    print("TEST 4: Manual resolution correctness")
    kb = KnowledgeBase()
    kb.tell(make_clause("A", "B"), source="clause {A, B}")
    kb.tell(make_clause("~A", "C"), source="clause {~A, C}")
    kb.tell(make_clause("~B"), source="clause {~B}")
    kb.tell(make_clause("~C", "D"), source="clause {~C, D}")

    result = kb.ask("D", positive=True)
    assert result, f"Expected KB |= D, got {result}"
    print(f"  [OK] KB |= D: {result} (correctly True)")

    result_e = kb.ask("E", positive=True)
    assert not result_e, f"Expected KB |/= E, got {result_e}"
    print(f"  [OK] KB |= E: {result_e} (correctly False -- E is not in KB)")
    print("  PASSED\n")


def test_perception_range():
    """TEST 5: Partial observability -- percepts strictly within range."""
    print("TEST 5: Partial observability (sensing range)")
    grid = MarsGrid(n=6, seed=42)
    percepts = grid.get_percepts(0, 0)

    for (cx, cy) in percepts:
        dist = abs(cx) + abs(cy)
        assert dist <= 2, f"Perceived ({cx},{cy}) at distance {dist} > 2 from (0,0)"

    for x in range(grid.n):
        for y in range(grid.n):
            if abs(x) + abs(y) > 2:
                assert (x, y) not in percepts, f"({x},{y}) should not be perceived from (0,0)"

    print(f"  [OK] All percepts within sensing range (distance <= 2)")
    print(f"  [OK] No cells outside range were revealed")
    print("  PASSED\n")


def test_50_maps_solvability_stress():
    """TEST 6: 50-Run Start->Goal Map Solvability Stress Test."""
    print("TEST 6: 50-Run Map Generation Solvability Stress Test")
    solvable_count = 0
    total_runs = 50

    for i in range(total_runs):
        grid, attempts, path = MarsGrid.create_solvable_grid(n=6, seed=None)
        assert path is not None, f"Run #{i+1} failed to create a valid path!"
        assert len(path) >= 6, f"Path length {len(path)} is unexpectedly short!"
        for px, py in path:
            assert grid.get_true_cell(px, py) == CellType.SAFE, f"Path cell ({px},{py}) is not SAFE!"
        solvable_count += 1

    assert solvable_count == total_runs
    print(f"  [OK] {solvable_count}/{total_runs} randomly generated maps had 100% valid Start->Goal paths")
    print("  PASSED\n")


def test_10_full_simulations_goal_stress():
    """TEST 7: 10-Run Goal-Directed Navigation Stress Test (100% Goal Reachability)."""
    print("TEST 7: 10-Run Goal-Directed Navigation Stress Test (100% Goal Reachability)")
    goal_reached_count = 0
    total_runs = 10

    for i in range(total_runs):
        grid, _, true_path = MarsGrid.create_solvable_grid(n=6, seed=None)
        logger = RoverLogger(use_color=False)

        old_stdout = sys.stdout
        sys.stdout = io.StringIO()

        agent = MarsRoverAgent(grid, logger=logger, max_steps=250)
        result = agent.run()

        sys.stdout = old_stdout

        assert result["reached_goal"], f"Run #{i+1} (seed={grid.seed}) failed to reach goal!"
        goal_reached_count += 1

        violations = []
        for vx, vy in result["visited"]:
            cell = grid.get_true_cell(vx, vy)
            if cell != CellType.SAFE:
                violations.append((vx, vy, cell.value))
        assert len(violations) == 0, f"Run #{i+1} had safety violations: {violations}"

    assert goal_reached_count == total_runs
    print(f"  [OK] 10/10 runs reached Extraction Goal with 0 safety violations")
    print("  PASSED\n")


if __name__ == "__main__":
    print("=" * 65)
    print("  MARS ROVER KB AGENT -- COMPREHENSIVE VERIFICATION & STRESS TESTS")
    print("=" * 65 + "\n")

    tests = [
        test_hazard_blocks_movement,
        test_radiation_blocks_entry,
        test_safe_inference,
        test_resolution_manual,
        test_perception_range,
        test_50_maps_solvability_stress,
        test_10_full_simulations_goal_stress,
    ]

    passed = 0
    failed = 0
    for test_fn in tests:
        try:
            test_fn()
            passed += 1
        except AssertionError as e:
            print(f"  FAILED: {e}\n")
            failed += 1
        except Exception as e:
            print(f"  ERROR: {type(e).__name__}: {e}\n")
            failed += 1

    print("=" * 65)
    print(f"  RESULTS: {passed} passed, {failed} failed out of {len(tests)}")
    print("=" * 65)
    sys.exit(0 if failed == 0 else 1)
