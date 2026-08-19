"""
visualizer.py — Mars Rover Visualizer with Photo Background & Clean UI HUD

Features:
  - Static photographic Mars surface background (no drawn grid lines)
  - Custom detailed Rover sprite with smooth interpolation and directional rotation
  - Clean Symbol-based Hazard (Warning Triangle) and Radiation (Trefoil) markers
    with dark high-contrast backings (no unrenderable emoji glyphs)
  - Clickable "Regenerate Map" UI button + [R] key for full state reset
  - Start (Landing Base) and Goal (Extraction Beacon) landmark icons
  - Soft atmospheric Fog-of-War overlay for unperceived cells
  - Persistent tire tracks on traveled terrain
  - Slower, readable step pacing (default 1.0s per decision step)
  - Debug grid overlay toggle ([G] key)
  - Generously spaced, polished Mission Control HUD with zero overlapping text
"""

import math
import os
import random
import time
import pygame
from grid import CellType, MarsGrid
from agent import MarsRoverAgent
from logger import RoverLogger


# ==========================================
# UI & COLOR DEFINITIONS
# ==========================================
COLOR_SPACE_BG = (12, 14, 20)
COLOR_PANEL_BG = (18, 23, 34)
COLOR_PANEL_BORDER = (40, 52, 75)
COLOR_ACCENT_CYAN = (64, 200, 224)
COLOR_ACCENT_ORANGE = (235, 115, 45)
COLOR_ACCENT_GREEN = (85, 225, 105)
COLOR_ACCENT_RED = (240, 75, 75)
COLOR_ACCENT_YELLOW = (245, 215, 65)
COLOR_TEXT_WHITE = (242, 245, 252)
COLOR_TEXT_MUTED = (145, 158, 180)

# Button Colors
BTN_BG_NORMAL = (28, 48, 72)
BTN_BG_HOVER = (42, 74, 110)
BTN_BORDER = (64, 180, 215)


class MarsRoverVisualizer:
    """Photographic background visualizer with symbol overlays and interactive controls."""

    def __init__(self, grid, agent, logger=None, step_delay=1.0):
        """
        Args:
            grid: MarsGrid instance.
            agent: MarsRoverAgent instance.
            logger: RoverLogger instance.
            step_delay: Decision step delay in seconds. Default: 1.0s (readable pacing).
        """
        self.grid = grid
        self.agent = agent
        self.logger = logger or RoverLogger()
        self.step_delay = max(0.1, float(step_delay))

        # Simulation state
        self.is_paused = False
        self.is_finished = False
        self.speed_multiplier = 1.0
        self.last_step_time = time.time()
        self.current_step_data = None
        self.step_generator = self.agent.run_step_by_step()

        # Debug grid toggle
        self.show_debug_grid = False

        # Rover animated position
        self.rover_pixel_x = 0.0
        self.rover_pixel_y = 0.0
        self.rover_target_pixel_x = 0.0
        self.rover_target_pixel_y = 0.0
        self.move_progress = 1.0
        self.move_speed = 4.0
        self.rover_heading = 0.0

        # Animation queues and trail
        self.animation_path_queue = []
        self.tire_tracks = []

        # Pygame init
        pygame.init()
        pygame.font.init()

        # Dynamic Sizing
        self.tile_size = max(70, min(95, 540 // self.grid.n))
        self.grid_pixel_size = self.grid.n * self.tile_size
        self.grid_offset_x = 35
        self.grid_offset_y = 65

        self.hud_width = 410
        self.window_width = self.grid_offset_x + self.grid_pixel_size + 30 + self.hud_width + 30
        self.window_height = max(self.grid_pixel_size + self.grid_offset_y + 45, 740)

        self.screen = pygame.display.set_mode((self.window_width, self.window_height))
        pygame.display.set_caption("ARES-1 Mars Rover — Goal-Directed KB Mission")
        self.clock = pygame.time.Clock()

        # Fonts with clean scaling
        self.font_title = pygame.font.SysFont("Segoe UI, Arial, sans-serif", 20, bold=True)
        self.font_subtitle = pygame.font.SysFont("Segoe UI, Arial, sans-serif", 13)
        self.font_card_title = pygame.font.SysFont("Segoe UI, Arial, sans-serif", 12, bold=True)
        self.font_stat_val = pygame.font.SysFont("Consolas, Courier, monospace", 16, bold=True)
        self.font_stat_val_sm = pygame.font.SysFont("Consolas, Courier, monospace", 13, bold=True)
        self.font_stat_lbl = pygame.font.SysFont("Segoe UI, Arial, sans-serif", 11)
        self.font_log = pygame.font.SysFont("Consolas, Courier, monospace", 11)
        self.font_badge = pygame.font.SysFont("Segoe UI, Arial, sans-serif", 12, bold=True)
        self.font_btn = pygame.font.SysFont("Segoe UI, Arial, sans-serif", 13, bold=True)

        # UI Button rect
        self.btn_regenerate_rect = pygame.Rect(0, 0, 10, 10)
        self.btn_is_hovered = False

        # Load Image Assets
        self._load_assets()

        # Initialize rover pixel position
        start_center = self.grid_to_center_screen(*self.grid.start_pos)
        self.rover_pixel_x, self.rover_pixel_y = start_center
        self.rover_target_pixel_x, self.rover_target_pixel_y = start_center
        self.tire_tracks.append(start_center)

        # Log startup
        self.logger.print_header(self.grid)

    def _load_assets(self):
        """
        Load and prepare Mars background image and Rover sprite.
        Maintains aspect ratio and fits background cleanly without distortion.
        """
        assets_dir = os.path.join(os.path.dirname(__file__), "assets")

        # 1. Mars Background Image
        bg_path = os.path.join(assets_dir, "mars_bg.jpg")
        if os.path.exists(bg_path):
            raw_bg = pygame.image.load(bg_path).convert()
            img_w, img_h = raw_bg.get_size()
            target_w, target_h = self.grid_pixel_size, self.grid_pixel_size

            # Scale preserving aspect ratio (fill target)
            scale = max(target_w / img_w, target_h / img_h)
            new_w = int(img_w * scale)
            new_h = int(img_h * scale)
            scaled_bg = pygame.transform.smoothscale(raw_bg, (new_w, new_h))

            # Center crop to exact grid size
            crop_x = (new_w - target_w) // 2
            crop_y = (new_h - target_h) // 2
            self.bg_surface = scaled_bg.subsurface((crop_x, crop_y, target_w, target_h))
        else:
            self.bg_surface = pygame.Surface((self.grid_pixel_size, self.grid_pixel_size))
            self.bg_surface.fill((175, 62, 18))

        # 2. Rover Sprite
        rover_path = os.path.join(assets_dir, "rover.png")
        if os.path.exists(rover_path):
            raw_rover = pygame.image.load(rover_path).convert_alpha()
            raw_rover = pygame.transform.flip(raw_rover, True, False)

            rw, rh = raw_rover.get_size()
            target_rover_w = int(self.tile_size * 0.76)
            target_rover_h = int(target_rover_w * (rh / rw))
            self.rover_sprite_base = pygame.transform.smoothscale(raw_rover, (target_rover_w, target_rover_h))
        else:
            self.rover_sprite_base = None

    def grid_to_center_screen(self, gx, gy):
        """Convert logical grid (gx, gy) to center pixel coordinate (px, py)."""
        return (
            self.grid_offset_x + gx * self.tile_size + self.tile_size / 2,
            self.grid_offset_y + gy * self.tile_size + self.tile_size / 2,
        )

    def reset_simulation(self):
        """
        Complete state reset triggered by 'Regenerate Map' button or [R] key.
        Generates fresh solvable map, clears KB facts/clauses, resets rover and counters.
        """
        print("\n" + "=" * 65)
        print("  [RESET] REGENERATING FRESH SOLVABLE MISSION MAP...")
        print("=" * 65)

        # 1. Create a brand new guaranteed-solvable grid
        new_grid, attempts, true_path = MarsGrid.create_solvable_grid(
            n=self.grid.n,
            seed=None,
            start_pos=self.grid.start_pos,
            goal_pos=self.grid.goal_pos,
            hazard_density=self.grid.hazard_density,
            radiation_density=self.grid.radiation_density,
        )
        self.grid = new_grid

        # 2. Reset agent with the new grid
        self.agent.reset_with_grid(new_grid)

        # 3. Reset visualizer telemetry and movement state
        self.is_finished = False
        self.current_step_data = None
        self.step_generator = self.agent.run_step_by_step()

        start_center = self.grid_to_center_screen(*new_grid.start_pos)
        self.rover_pixel_x, self.rover_pixel_y = start_center
        self.rover_target_pixel_x, self.rover_target_pixel_y = start_center
        self.move_progress = 1.0
        self.rover_heading = 0.0
        self.animation_path_queue.clear()
        self.tire_tracks = [start_center]
        self.last_step_time = time.time()

        # 4. Log new mission initialization
        stats = new_grid.get_stats()
        print(f"  Random Seed:          {new_grid.seed} (Randomized)")
        print(f"  [INIT] Path validated: Start{new_grid.start_pos} -> Goal{new_grid.goal_pos}, length {len(true_path)} cells (attempt #{attempts})")
        print("=" * 65 + "\n")
        self.logger.print_header(self.grid)

    def run(self):
        """Main Pygame application loop."""
        running = True

        while running:
            dt = self.clock.tick(60) / 1000.0
            mouse_pos = pygame.mouse.get_pos()
            self.btn_is_hovered = self.btn_regenerate_rect.collidepoint(mouse_pos)

            # 1. Event Handling
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.btn_is_hovered:
                        self.reset_simulation()
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_SPACE:
                        self.is_paused = not self.is_paused
                    elif event.key == pygame.K_RIGHT:
                        if not self.is_finished:
                            self._execute_agent_step()
                    elif event.key == pygame.K_r:
                        self.reset_simulation()
                    elif event.key == pygame.K_g:
                        self.show_debug_grid = not self.show_debug_grid
                    elif event.key in (pygame.K_PLUS, pygame.K_KP_PLUS, pygame.K_EQUALS):
                        self.speed_multiplier = min(4.0, self.speed_multiplier * 1.3)
                    elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                        self.speed_multiplier = max(0.25, self.speed_multiplier / 1.3)

            # 2. Logic Step Trigger
            current_time = time.time()
            effective_delay = self.step_delay / self.speed_multiplier

            if not self.is_paused and not self.is_finished:
                if self.move_progress >= 1.0 and not self.animation_path_queue:
                    if (current_time - self.last_step_time) >= effective_delay:
                        self._execute_agent_step()
                        self.last_step_time = current_time

            # 3. Rover Movement Interpolation
            self._update_rover_animation(dt)

            # 4. Render Frame
            self._render_frame(dt)
            pygame.display.flip()

        pygame.quit()
        return "QUIT"

    def _execute_agent_step(self):
        """Execute one KB decision step, log to console, and queue animation."""
        if self.is_finished:
            return

        try:
            step_data = next(self.step_generator)
            self.current_step_data = step_data

            step = step_data["step"]
            prev_x, prev_y = step_data["prev_pos"]
            cur_x, cur_y = step_data["rover_pos"]

            # --- SYNCHRONIZED CONSOLE LOGS ---
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
                    self.animation_path_queue = list(step_data["path"][1:])
                    self._start_next_path_leg()
            elif step_data["action_type"] == "MOVE":
                self.logger.print_decision(step, step_data["decision_text"])
                tx, ty = self.grid_to_center_screen(cur_x, cur_y)
                self.rover_target_pixel_x = tx
                self.rover_target_pixel_y = ty
                self.move_progress = 0.0
                dx = tx - self.rover_pixel_x
                dy = ty - self.rover_pixel_y
                if dx != 0 or dy != 0:
                    self.rover_heading = math.atan2(dy, dx)
            elif step_data["action_type"] in ("HALT", "GOAL_REACHED"):
                self.logger.print_decision(step, step_data["decision_text"])

            if step_data["is_done"]:
                self.is_finished = True
                self.logger.print_exploration_complete(
                    step,
                    len(step_data["visited"]),
                    self.grid.n * self.grid.n,
                    step_data["completion_reason"]
                )

        except StopIteration:
            self.is_finished = True

    def _start_next_path_leg(self):
        """Start smooth lerp towards next waypoint in backtrack path."""
        if self.animation_path_queue:
            nx, ny = self.animation_path_queue.pop(0)
            tx, ty = self.grid_to_center_screen(nx, ny)
            self.rover_target_pixel_x = tx
            self.rover_target_pixel_y = ty
            self.move_progress = 0.0
            dx = tx - self.rover_pixel_x
            dy = ty - self.rover_pixel_y
            if dx != 0 or dy != 0:
                self.rover_heading = math.atan2(dy, dx)

    def _update_rover_animation(self, dt):
        """Interpolate rover pixel position towards target."""
        if self.move_progress < 1.0:
            speed = self.move_speed * self.speed_multiplier
            self.move_progress = min(1.0, self.move_progress + speed * dt)

            t = self.move_progress
            ease_t = t * t * (3.0 - 2.0 * t)

            self.rover_pixel_x += (self.rover_target_pixel_x - self.rover_pixel_x) * ease_t
            self.rover_pixel_y += (self.rover_target_pixel_y - self.rover_pixel_y) * ease_t

            # Record trail
            cur_pos = (self.rover_pixel_x, self.rover_pixel_y)
            if not self.tire_tracks or math.hypot(cur_pos[0] - self.tire_tracks[-1][0], cur_pos[1] - self.tire_tracks[-1][1]) > 10:
                self.tire_tracks.append(cur_pos)

            if self.move_progress >= 1.0:
                self.rover_pixel_x = self.rover_target_pixel_x
                self.rover_pixel_y = self.rover_target_pixel_y
                if self.animation_path_queue:
                    self._start_next_path_leg()

    def _render_frame(self, dt):
        """Render base photo background, overlays, rover, and HUD."""
        self.screen.fill(COLOR_SPACE_BG)

        # 1. Header
        self._render_header()

        # 2. Mars Photo Terrain Surface
        self._render_mars_photo_grid()

        # 3. Rover Sprite & Sensor Pulse
        self._render_rover()

        # 4. HUD Telemetry Panel & Buttons
        self._render_hud()

    def _render_header(self):
        """Render top mission title bar."""
        title_surf = self.font_title.render("ARES-1 MARS ROVER", True, COLOR_TEXT_WHITE)
        self.screen.blit(title_surf, (self.grid_offset_x, 14))

        gx, gy = self.grid.goal_pos
        sub_surf = self.font_subtitle.render(
            f"Goal-Directed KB Agent  |  Start (0,0) -> Extraction ({gx},{gy})  |  Photo Terrain Surface",
            True, COLOR_ACCENT_CYAN
        )
        self.screen.blit(sub_surf, (self.grid_offset_x, 38))

    def _render_mars_photo_grid(self):
        """
        Render Mars surface photo as the base layer, with symbol overlays,
        soft fog-of-war, and optional debug grid.
        """
        # A. Base Photo Layer (scaled & center-cropped, no grid lines)
        self.screen.blit(self.bg_surface, (self.grid_offset_x, self.grid_offset_y))

        # B. Traveled Path / Tire Tracks
        if len(self.tire_tracks) > 1:
            for i in range(len(self.tire_tracks) - 1):
                p1 = self.tire_tracks[i]
                p2 = self.tire_tracks[i + 1]
                pygame.draw.line(self.screen, (75, 24, 6), p1, p2, 4)

        # C. Inferred Safe Waypoint Markers (s)
        for (sx, sy) in self.agent.known_safe:
            if (sx, sy) not in self.agent.visited and (sx, sy) != self.grid.goal_pos:
                scx, scy = self.grid_to_center_screen(sx, sy)
                # Waypoint beacon ring with dark contrast backing
                pygame.draw.circle(self.screen, (16, 20, 28, 180), (scx, scy), int(self.tile_size * 0.26))
                pygame.draw.circle(self.screen, (230, 120, 50), (scx, scy), int(self.tile_size * 0.26), width=2)
                pygame.draw.circle(self.screen, (80, 220, 120), (scx, scy), 4)

        # D. Start Landmark (Landing Pad)
        self._render_start_landmark()

        # E. Goal Landmark (Extraction Beacon Tower)
        self._render_goal_landmark()

        # F. Symbol Overlay: Hazards (Warning Triangle)
        for pos in self.agent.known_hazard:
            self._render_hazard_symbol(pos)

        # G. Symbol Overlay: Radiation (Radioactive Trefoil)
        for pos in self.agent.known_radiation:
            self._render_radiation_symbol(pos)

        # H. Soft Atmospheric Fog-of-War
        self._render_fog_of_war()

        # I. Optional Debug Grid (Toggled via [G] key)
        if self.show_debug_grid:
            self._render_debug_grid()

        # Outer Frame Border
        frame_rect = pygame.Rect(
            self.grid_offset_x - 3,
            self.grid_offset_y - 3,
            self.grid_pixel_size + 6,
            self.grid_pixel_size + 6
        )
        pygame.draw.rect(self.screen, COLOR_PANEL_BORDER, frame_rect, width=2, border_radius=4)

    def _render_hazard_symbol(self, pos):
        """
        Render crisp Warning Triangle icon for Hazard cell with dark contrast backing.
        """
        cx, cy = self.grid_to_center_screen(*pos)
        badge_r = int(self.tile_size * 0.32)

        # High-contrast dark backing circle
        backing_surf = pygame.Surface((badge_r * 2 + 4, badge_r * 2 + 4), pygame.SRCALPHA)
        pygame.draw.circle(backing_surf, (18, 16, 20, 230), (badge_r + 2, badge_r + 2), badge_r)
        pygame.draw.circle(backing_surf, (220, 50, 50, 255), (badge_r + 2, badge_r + 2), badge_r, width=2)
        self.screen.blit(backing_surf, (cx - badge_r - 2, cy - badge_r - 2))

        # Warning Triangle (Yellow/Orange)
        tri_size = badge_r * 0.75
        tri_pts = [
            (cx, cy - tri_size),
            (cx - tri_size * 0.95, cy + tri_size * 0.75),
            (cx + tri_size * 0.95, cy + tri_size * 0.75),
        ]
        pygame.draw.polygon(self.screen, (245, 175, 25), tri_pts)
        pygame.draw.polygon(self.screen, (255, 235, 180), tri_pts, width=1)

        # Exclamation Mark [ ! ] inside triangle
        pygame.draw.line(self.screen, (20, 20, 20), (cx, cy - tri_size * 0.4), (cx, cy + tri_size * 0.2), 3)
        pygame.draw.circle(self.screen, (20, 20, 20), (cx, cy + tri_size * 0.5), 2)

    def _render_radiation_symbol(self, pos):
        """
        Render crisp Radioactive Trefoil icon for Radiation cell with dark contrast backing.
        """
        cx, cy = self.grid_to_center_screen(*pos)
        badge_r = int(self.tile_size * 0.32)

        # High-contrast dark backing circle
        backing_surf = pygame.Surface((badge_r * 2 + 4, badge_r * 2 + 4), pygame.SRCALPHA)
        pygame.draw.circle(backing_surf, (15, 22, 14, 230), (badge_r + 2, badge_r + 2), badge_r)
        pygame.draw.circle(backing_surf, (140, 230, 40, 255), (badge_r + 2, badge_r + 2), badge_r, width=2)
        self.screen.blit(backing_surf, (cx - badge_r - 2, cy - badge_r - 2))

        # Radioactive Trefoil Blades (Neon Yellow-Green)
        center_dot_rad = max(3, int(badge_r * 0.2))
        pygame.draw.circle(self.screen, COLOR_ACCENT_YELLOW, (cx, cy), center_dot_rad)

        blade_r = badge_r * 0.65
        for angle_deg in [0, 120, 240]:
            rad = math.radians(angle_deg - 90)
            bx = cx + math.cos(rad) * blade_r
            by = cy + math.sin(rad) * blade_r
            pygame.draw.circle(self.screen, COLOR_ACCENT_YELLOW, (int(bx), int(by)), int(badge_r * 0.26))

        pygame.draw.circle(self.screen, (20, 25, 20), (cx, cy), max(1, center_dot_rad - 2))

    def _render_start_landmark(self):
        """Render Base Landing Pad icon at Start (0,0)."""
        sx, sy = self.grid_to_center_screen(*self.grid.start_pos)
        pad_size = int(self.tile_size * 0.35)

        # Landing pad octagonal base
        pts = []
        for i in range(8):
            ang = math.radians(i * 45 + 22.5)
            pts.append((sx + math.cos(ang) * pad_size, sy + math.sin(ang) * pad_size))
        pygame.draw.polygon(self.screen, (32, 40, 52), pts)
        pygame.draw.polygon(self.screen, (235, 190, 45), pts, width=2)

        lbl = self.font_card_title.render("BASE", True, (245, 205, 60))
        lrect = lbl.get_rect(center=(sx, sy))
        self.screen.blit(lbl, lrect)

    def _render_goal_landmark(self):
        """Render Extraction Beacon icon at Goal (N-1, N-1)."""
        gx, gy = self.grid_to_center_screen(*self.grid.goal_pos)
        pulse = math.sin(time.time() * 4.0) * 3.0
        rad = int(self.tile_size * 0.36 + pulse)

        # Skyward signal pulse ring
        beacon_surface = pygame.Surface((rad * 2 + 10, rad * 2 + 10), pygame.SRCALPHA)
        pygame.draw.circle(beacon_surface, (64, 200, 224, 75), (rad + 5, rad + 5), rad, width=2)
        pygame.draw.circle(beacon_surface, (64, 200, 224, 30), (rad + 5, rad + 5), rad - 5, width=1)
        self.screen.blit(beacon_surface, (gx - rad - 5, gy - rad - 5))

        # Extraction Tower Structure
        pygame.draw.polygon(self.screen, (40, 55, 75), [
            (gx, gy - 16), (gx - 10, gy + 12), (gx + 10, gy + 12)
        ])
        pygame.draw.polygon(self.screen, COLOR_ACCENT_CYAN, [
            (gx, gy - 16), (gx - 10, gy + 12), (gx + 10, gy + 12)
        ], width=2)

        # Glowing core
        pygame.draw.circle(self.screen, (255, 255, 255), (gx, gy - 16), 4)
        pygame.draw.circle(self.screen, COLOR_ACCENT_CYAN, (gx, gy - 16), 7, width=1)

        glbl = self.font_stat_lbl.render("GOAL", True, COLOR_ACCENT_CYAN)
        grect = glbl.get_rect(center=(gx, gy + 18))
        self.screen.blit(glbl, grect)

    def _render_fog_of_war(self):
        """
        Soft atmospheric Fog-of-War overlay.
        Unperceived cells are shrouded in dark translucent dust;
        perceived cells punch smooth feathered light holes.
        """
        w, h = self.grid_pixel_size, self.grid_pixel_size
        fog = pygame.Surface((w, h), pygame.SRCALPHA)
        fog.fill((16, 12, 14, 230))

        reveal_radius = int(self.tile_size * 0.72)
        for (cx, cy) in self.agent.sensed_cells:
            pcx = cx * self.tile_size + self.tile_size // 2
            pcy = cy * self.tile_size + self.tile_size // 2
            pygame.draw.circle(fog, (0, 0, 0, 0), (pcx, pcy), reveal_radius)
            pygame.draw.circle(fog, (16, 12, 14, 50), (pcx, pcy), reveal_radius + 8, width=8)

        # Rover light punch-out
        rover_rel_x = int(self.rover_pixel_x - self.grid_offset_x)
        rover_rel_y = int(self.rover_pixel_y - self.grid_offset_y)
        pygame.draw.circle(fog, (0, 0, 0, 0), (rover_rel_x, rover_rel_y), int(self.tile_size * 0.82))

        # Always reveal Start and Goal landmarks through fog
        sx, sy = self.grid.start_pos
        pygame.draw.circle(fog, (0, 0, 0, 0), (sx * self.tile_size + self.tile_size // 2, sy * self.tile_size + self.tile_size // 2), reveal_radius)
        gx, gy = self.grid.goal_pos
        pygame.draw.circle(fog, (0, 0, 0, 0), (gx * self.tile_size + self.tile_size // 2, gy * self.tile_size + self.tile_size // 2), reveal_radius)

        self.screen.blit(fog, (self.grid_offset_x, self.grid_offset_y))

    def _render_debug_grid(self):
        """Optional faint grid guidelines (toggled via [G] key)."""
        for i in range(self.grid.n + 1):
            x = self.grid_offset_x + i * self.tile_size
            y = self.grid_offset_y + i * self.tile_size
            pygame.draw.line(self.screen, (240, 240, 255, 60), (x, self.grid_offset_y), (x, self.grid_offset_y + self.grid_pixel_size), 1)
            pygame.draw.line(self.screen, (240, 240, 255, 60), (self.grid_offset_x, y), (self.grid_offset_x + self.grid_pixel_size, y), 1)

    def _render_rover(self):
        """Render directional Mars rover sprite with animated radar sweep."""
        rx = int(self.rover_pixel_x)
        ry = int(self.rover_pixel_y)

        # 1. Partial-observability radar sweep pulse
        pulse_r = int((self.tile_size * 1.22) + math.sin(time.time() * 3.5) * 4.0)
        sensor_surface = pygame.Surface((pulse_r * 2, pulse_r * 2), pygame.SRCALPHA)
        pygame.draw.circle(sensor_surface, (64, 200, 224, 40), (pulse_r, pulse_r), pulse_r, width=1)
        pygame.draw.circle(sensor_surface, (64, 200, 224, 15), (pulse_r, pulse_r), pulse_r - 8, width=1)
        self.screen.blit(sensor_surface, (rx - pulse_r, ry - pulse_r))

        # 2. Render Custom Rover Sprite with rotation
        if self.rover_sprite_base:
            deg = -math.degrees(self.rover_heading)
            rotated_sprite = pygame.transform.rotate(self.rover_sprite_base, deg)
            rot_rect = rotated_sprite.get_rect(center=(rx, ry))
            self.screen.blit(rotated_sprite, rot_rect)
        else:
            body_w = self.tile_size * 0.45
            body_h = self.tile_size * 0.35
            chassis = pygame.Rect(0, 0, body_w, body_h)
            chassis.center = (rx, ry)
            pygame.draw.rect(self.screen, (225, 230, 240), chassis, border_radius=4)
            pygame.draw.circle(self.screen, (230, 60, 40), (int(rx + math.cos(self.rover_heading) * 12), int(ry + math.sin(self.rover_heading) * 12)), 4)

    def _render_hud(self):
        """Render generously spaced, polished Mission Control HUD panel."""
        hud_x = self.grid_offset_x + self.grid_pixel_size + 25
        hud_y = self.grid_offset_y - 15
        hud_h = self.window_height - hud_y - 25

        # Background Card
        panel_rect = pygame.Rect(hud_x, hud_y, self.hud_width, hud_h)
        pygame.draw.rect(self.screen, COLOR_PANEL_BG, panel_rect, border_radius=8)
        pygame.draw.rect(self.screen, COLOR_PANEL_BORDER, panel_rect, width=1, border_radius=8)

        cur_y = hud_y + 16

        # --- 1. STATUS BADGE & SPEED ---
        badge_text, badge_color = self._get_status_badge()
        badge_surf = self.font_badge.render(f"  {badge_text}  ", True, badge_color)
        badge_bg_rect = badge_surf.get_rect(topleft=(hud_x + 30, cur_y))
        pygame.draw.rect(self.screen, (28, 36, 50), badge_bg_rect.inflate(12, 6), border_radius=4)
        # Drawn colored indicator circle
        pygame.draw.circle(self.screen, badge_color, (hud_x + 22, cur_y + badge_bg_rect.height // 2), 4)
        self.screen.blit(badge_surf, badge_bg_rect)

        # Speed Multiplier
        speed_txt = self.font_subtitle.render(f"Speed: {self.speed_multiplier:.1f}x", True, COLOR_TEXT_MUTED)
        self.screen.blit(speed_txt, (hud_x + self.hud_width - 85, cur_y))
        cur_y += 38

        # --- 2. REGENERATE MAP BUTTON ---
        self.btn_regenerate_rect = pygame.Rect(hud_x + 16, cur_y, self.hud_width - 32, 40)
        btn_bg = BTN_BG_HOVER if self.btn_is_hovered else BTN_BG_NORMAL
        pygame.draw.rect(self.screen, btn_bg, self.btn_regenerate_rect, border_radius=6)
        pygame.draw.rect(self.screen, BTN_BORDER, self.btn_regenerate_rect, width=1, border_radius=6)

        # Button Text (ASCII-clean, no unrenderable emoji)
        btn_txt = self.font_btn.render(">>  REGENERATE MAP  [R]  <<", True, COLOR_TEXT_WHITE)
        btn_txt_rect = btn_txt.get_rect(center=self.btn_regenerate_rect.center)
        self.screen.blit(btn_txt, btn_txt_rect)
        cur_y += 50

        # --- 3. 2x2 TELEMETRY METRICS GRID (Evenly Spaced Cards) ---
        gx, gy = self.grid.goal_pos
        dist_to_goal = abs(self.agent.x - gx) + abs(self.agent.y - gy)

        metrics = [
            ("STEP", str(self.agent.step), COLOR_TEXT_WHITE, False),
            ("ROVER POS", f"({self.agent.x}, {self.agent.y})", COLOR_ACCENT_ORANGE, False),
            ("EXTRACTION GOAL", f"({gx},{gy}) [d={dist_to_goal}]", COLOR_ACCENT_CYAN, True),
            ("KB CLAUSES", str(self.agent.kb.clause_count), COLOR_ACCENT_GREEN, False),
        ]
        self._render_metric_grid(hud_x + 16, cur_y, self.hud_width - 32, metrics)
        cur_y += 114

        # --- 4. AVOIDANCE COUNTERS (Hazards & Radiation) ---
        avoid_hazards = sum(1 for _, _, _, ht in self.agent.hazard_avoidance_events if ht == "Hazard")
        avoid_rad = sum(1 for _, _, _, ht in self.agent.hazard_avoidance_events if ht == "Radiation")

        card_w = (self.hud_width - 32 - 10) // 2
        card_h = 46

        haz_card = pygame.Rect(hud_x + 16, cur_y, card_w, card_h)
        rad_card = pygame.Rect(haz_card.right + 10, cur_y, card_w, card_h)

        # Hazard Card
        pygame.draw.rect(self.screen, (38, 25, 30), haz_card, border_radius=6)
        pygame.draw.rect(self.screen, (80, 35, 42), haz_card, width=1, border_radius=6)
        # Mini vector warning triangle
        self._draw_mini_warning_icon(haz_card.x + 14, haz_card.y + 14)
        h_val = self.font_stat_val.render(str(avoid_hazards), True, COLOR_ACCENT_RED)
        h_lbl = self.font_stat_lbl.render("Hazards Avoided", True, COLOR_TEXT_MUTED)
        self.screen.blit(h_val, (haz_card.x + 28, haz_card.y + 6))
        self.screen.blit(h_lbl, (haz_card.x + 10, haz_card.y + 26))

        # Radiation Card
        pygame.draw.rect(self.screen, (26, 36, 22), rad_card, border_radius=6)
        pygame.draw.rect(self.screen, (52, 75, 28), rad_card, width=1, border_radius=6)
        # Mini vector trefoil icon
        self._draw_mini_trefoil_icon(rad_card.x + 14, rad_card.y + 14)
        r_val = self.font_stat_val.render(str(avoid_rad), True, COLOR_ACCENT_YELLOW)
        r_lbl = self.font_stat_lbl.render("Radiation Avoided", True, COLOR_TEXT_MUTED)
        self.screen.blit(r_val, (rad_card.x + 28, rad_card.y + 6))
        self.screen.blit(r_lbl, (rad_card.x + 10, rad_card.y + 26))
        cur_y += 56

        # --- 5. PROGRESS TO GOAL / SOLVABILITY BADGE ---
        cov_lbl = self.font_stat_lbl.render(
            f"Start (0,0) -> Goal ({gx},{gy}) | Path: 100% Solvable",
            True, COLOR_TEXT_MUTED
        )
        self.screen.blit(cov_lbl, (hud_x + 16, cur_y))
        cur_y += 18

        max_dist = (self.grid.n - 1) * 2
        prog_pct = max(0.0, min(100.0, ((max_dist - dist_to_goal) / max_dist) * 100.0))
        if self.agent.reached_goal:
            prog_pct = 100.0

        bar_bg = pygame.Rect(hud_x + 16, cur_y, self.hud_width - 32, 8)
        bar_fill = pygame.Rect(hud_x + 16, cur_y, int((self.hud_width - 32) * (prog_pct / 100.0)), 8)
        pygame.draw.rect(self.screen, (32, 40, 56), bar_bg, border_radius=4)
        bar_color = COLOR_ACCENT_GREEN if self.agent.reached_goal else COLOR_ACCENT_CYAN
        pygame.draw.rect(self.screen, bar_color, bar_fill, border_radius=4)
        cur_y += 24

        # --- 6. LIVE LOGICAL INFERENCE FEED ---
        log_title = self.font_card_title.render("LIVE LOGICAL INFERENCE FEED", True, COLOR_ACCENT_CYAN)
        self.screen.blit(log_title, (hud_x + 16, cur_y))
        cur_y += 22

        log_box = pygame.Rect(hud_x + 16, cur_y, self.hud_width - 32, 135)
        pygame.draw.rect(self.screen, (14, 18, 26), log_box, border_radius=6)
        pygame.draw.rect(self.screen, COLOR_PANEL_BORDER, log_box, width=1, border_radius=6)

        self._render_log_feed(log_box.x + 10, log_box.y + 10, log_box.width - 20)
        cur_y += 145

        # --- 7. MISSION CONTROLS GUIDE ---
        ctrl_title = self.font_card_title.render("MISSION CONTROLS", True, COLOR_TEXT_WHITE)
        self.screen.blit(ctrl_title, (hud_x + 16, cur_y))
        cur_y += 20

        ctrls = [
            ("SPACE", "Pause / Resume"),
            ("RIGHT", "Single Step (when paused)"),
            ("+ / -", "Adjust Speed"),
            ("R", "Regenerate Solvable Map"),
            ("G", f"Toggle Debug Grid [{'ON' if self.show_debug_grid else 'OFF'}]"),
            ("ESC", "Quit Simulation"),
        ]
        for key_name, key_desc in ctrls:
            k_surf = self.font_log.render(f"[{key_name:<5}]", True, COLOR_ACCENT_ORANGE)
            d_surf = self.font_subtitle.render(key_desc, True, COLOR_TEXT_MUTED)
            self.screen.blit(k_surf, (hud_x + 16, cur_y))
            self.screen.blit(d_surf, (hud_x + 90, cur_y))
            cur_y += 18

    def _render_metric_grid(self, x, y, width, metrics):
        """Render 2x2 telemetry cards with generous vertical spacing (no overlapping)."""
        card_w = (width - 10) // 2
        card_h = 48

        for i, (lbl, val, col, is_small) in enumerate(metrics):
            cx = x + (i % 2) * (card_w + 10)
            cy = y + (i // 2) * (card_h + 10)

            card_rect = pygame.Rect(cx, cy, card_w, card_h)
            pygame.draw.rect(self.screen, (26, 33, 46), card_rect, border_radius=5)
            pygame.draw.rect(self.screen, (42, 53, 72), card_rect, width=1, border_radius=5)

            # Label at top of card
            l_surf = self.font_stat_lbl.render(lbl, True, COLOR_TEXT_MUTED)
            self.screen.blit(l_surf, (cx + 8, cy + 5))

            # Value below label with clean spacing
            font_to_use = self.font_stat_val_sm if is_small else self.font_stat_val
            v_surf = font_to_use.render(val, True, col)
            self.screen.blit(v_surf, (cx + 8, cy + 23))

    def _draw_mini_warning_icon(self, cx, cy):
        """Draw small vector warning triangle in Avoidance Card."""
        tri_pts = [(cx, cy - 6), (cx - 6, cy + 5), (cx + 6, cy + 5)]
        pygame.draw.polygon(self.screen, (245, 175, 25), tri_pts)
        pygame.draw.line(self.screen, (20, 20, 20), (cx, cy - 3), (cx, cy + 1), 1)
        pygame.draw.circle(self.screen, (20, 20, 20), (cx, cy + 3), 1)

    def _draw_mini_trefoil_icon(self, cx, cy):
        """Draw small vector radiation trefoil in Avoidance Card."""
        pygame.draw.circle(self.screen, COLOR_ACCENT_YELLOW, (cx, cy), 2)
        for angle_deg in [0, 120, 240]:
            rad = math.radians(angle_deg - 90)
            bx = cx + math.cos(rad) * 4
            by = cy + math.sin(rad) * 4
            pygame.draw.circle(self.screen, COLOR_ACCENT_YELLOW, (int(bx), int(by)), 2)

    def _render_log_feed(self, x, y, max_w):
        """Render formatted step lines in HUD feed with clean line spacing."""
        if not self.current_step_data:
            init_txt = self.font_log.render("System online. Planning path to Goal...", True, COLOR_TEXT_MUTED)
            self.screen.blit(init_txt, (x, y))
            return

        step = self.current_step_data["step"]
        lines = [
            (f"[Step {step}] PERCEIVE: {len(self.current_step_data['percepts'])} sensor signals", COLOR_ACCENT_CYAN),
        ]

        if self.current_step_data["tell_log"]:
            inf_count = sum(len(e["inferred"]) for e in self.current_step_data["tell_log"])
            if inf_count > 0:
                lines.append((f"[Step {step}] TELL: +{inf_count} inferred facts via KB", COLOR_ACCENT_ORANGE))
            else:
                lines.append((f"[Step {step}] TELL: KB updated with percepts", COLOR_TEXT_MUTED))

        if self.current_step_data["action_type"] == "GOAL_REACHED":
            lines.append((f"[Step {step}] STATUS: EXTRACTION REACHED!", COLOR_ACCENT_GREEN))
            lines.append((f"[Step {step}] Extraction beacon activated", COLOR_TEXT_WHITE))
        elif self.current_step_data["action_type"] == "MOVE":
            lines.append((f"[Step {step}] ASK: Safe? -> TRUE (entailed)", COLOR_ACCENT_GREEN))
            lines.append((f"[Step {step}] ACTION: Move -> ({self.agent.x},{self.agent.y})", COLOR_TEXT_WHITE))
        elif self.current_step_data["action_type"] == "BACKTRACK":
            lines.append((f"[Step {step}] ASK: Local path blocked", COLOR_ACCENT_RED))
            lines.append((f"[Step {step}] ACTION: Backtracking to frontier", COLOR_ACCENT_YELLOW))
        elif self.current_step_data["action_type"] == "HALT":
            lines.append((f"[Step {step}] STATUS: Halted", COLOR_ACCENT_RED))

        cur_line_y = y
        for text, color in lines[:5]:
            surf = self.font_log.render(text[:45], True, color)
            self.screen.blit(surf, (x, cur_line_y))
            cur_line_y += 22

    def _get_status_badge(self):
        """Return (label, color) for status."""
        if self.agent.reached_goal:
            return "GOAL REACHED", COLOR_ACCENT_GREEN
        if self.is_finished:
            return "MISSION COMPLETE", COLOR_ACCENT_CYAN
        if self.is_paused:
            return "PAUSED", COLOR_ACCENT_YELLOW
        if self.current_step_data:
            if self.current_step_data["action_type"] == "BACKTRACK":
                return "REROUTING / BACKTRACK", COLOR_ACCENT_YELLOW
            if self.current_step_data["hazard_avoidance_events"]:
                last_step = self.current_step_data["hazard_avoidance_events"][-1][0]
                if last_step == self.agent.step:
                    return "HAZARD AVOIDED", COLOR_ACCENT_RED
        return "NAVIGATING TO GOAL", COLOR_ACCENT_CYAN
