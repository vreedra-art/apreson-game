# -*- coding: utf-8 -*-
"""APRESON ULTIMATE - Single File Build
Preserves original stick-figure art style (white on dark) and AIO/OIA story.
"""
import os, sys, math, random, json
from kivy.config import Config
try:
    if 'ANDROID_ARGUMENT' not in os.environ:
        Config.set('graphics', 'width', '1280')
        Config.set('graphics', 'height', '720')
        Config.set('graphics', 'resizable', True)
        Config.set('input', 'mouse', 'mouse,multitouch_on_demand')
except Exception:
    pass
from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.graphics import Color, Line, Ellipse, Rectangle, Triangle
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.core.text import Label as CoreLabel
from kivy.core.window import Window
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition

# ============================================================
# CONSTANTS
# ============================================================
GROUND = 250
WORLD_W = 3200
WORLD_H = 1000
GOAL_X = 1800
SAVE_FILE = "apreson_save.json"

STORY = {
    1: "APRESON - LEVEL 1\n\nAIO lost in a dark land...\nHe must find his friend OIA.",
    2: "LEVEL 2 - NIGHT\n\nNight has fallen...\nStars and moon above...\nEnemies come from both sides!",
    3: "LEVEL 3 - NIGHT SKY\n\nBOSS FIGHT!\nDefeat the BOSS...\nThen you will find OIA!",
}

LEVELS = {
    1: {"bg": (0.1, 0.1, 0.1, 1), "ground": (1, 1, 1, 1),
        "enemy_speed": 50, "enemy_hp": 30, "damage": 0.15,
        "count": 6, "flyers": 2, "flyer_speed": 60, "name": "DARK LAND"},
    2: {"bg": (0.05, 0.05, 0.2, 1), "ground": (0.8, 0.8, 1, 1),
        "enemy_speed": 80, "enemy_hp": 50, "damage": 0.30,
        "count": 9, "flyers": 4, "flyer_speed": 90, "name": "NIGHT"},
    3: {"bg": (0.1, 0.0, 0.3, 1), "ground": (0.8, 0.8, 1, 1),
        "enemy_speed": 110, "enemy_hp": 80, "damage": 0.50,
        "count": 8, "flyers": 4, "flyer_speed": 120, "name": "NIGHT SKY - BOSS"},
}

DIFFICULTY = {"EASY": {"mult": 0.7}, "NORMAL": {"mult": 1.0}, "HARD": {"mult": 1.4}}

# ============================================================
# HELPERS
# ============================================================
_TEXT_CACHE = {}
def draw_text(canvas, text, x, y, size=28, color=(1, 1, 1, 1)):
    key = (text, size, tuple(color))
    if key not in _TEXT_CACHE:
        label = CoreLabel(text=text, font_size=size, color=color)
        label.refresh()
        _TEXT_CACHE[key] = label.texture
    tex = _TEXT_CACHE[key]
    Rectangle(texture=tex, pos=(x - tex.width/2, y), size=tex.size)

def clamp(v, a, b):
    return max(a, min(b, v))

# ============================================================
# SAVE MANAGER
# ============================================================
class SaveManager:
    @staticmethod
    def default():
        return {"high_score": 0, "unlocked_stage": 1,
                "difficulty": "NORMAL", "coins": 0}

    @staticmethod
    def load():
        try:
            if os.path.exists(SAVE_FILE):
                with open(SAVE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                d = SaveManager.default()
                for k in d:
                    if k not in data or type(data[k]) is not type(d[k]):
                        data[k] = d[k]
                if data["difficulty"] not in DIFFICULTY:
                    data["difficulty"] = "NORMAL"
                return data
        except Exception as e:
            print("Save load err:", e)
        return SaveManager.default()

    @staticmethod
    def save(data):
        try:
            with open(SAVE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print("Save err:", e)

# ============================================================
# PARTICLE
# ============================================================
class Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "color", "size", "alive")
    def __init__(self, x, y, vx, vy, life, color=(1, 1, 1, 1), size=4):
        self.x = x; self.y = y
        self.vx = vx; self.vy = vy
        self.life = life; self.max_life = life
        self.color = color; self.size = size
        self.alive = True

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy -= 600 * dt
        self.life -= dt
        if self.life <= 0:
            self.alive = False

# ============================================================
# BULLET
# ============================================================
class Bullet:
    def __init__(self, x, y, facing, target=None):
        self.x = x; self.y = y; self.facing = facing
        self.target = target; self.alive = True

    def update(self, dt):
        if self.target and getattr(self.target, 'alive', False):
            dx = self.target.x - self.x
            dy = (self.target.y + 100) - self.y
            dist = math.sqrt(dx*dx + dy*dy) or 1
            self.x += (dx/dist) * 650 * dt
            self.y += (dy/dist) * 650 * dt
        else:
            self.x += 600 * self.facing * dt
        if self.x < 0 or self.x > WORLD_W or self.y < 0 or self.y > WORLD_H:
            self.alive = False

class EnemyBullet:
    def __init__(self, x, y, tx, ty, speed=250):
        self.x = x; self.y = y
        dx = tx - x; dy = ty - y
        dist = math.sqrt(dx*dx + dy*dy) or 1
        self.vx = (dx/dist) * speed
        self.vy = (dy/dist) * speed
        self.alive = True

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        if self.x < 0 or self.x > WORLD_W or self.y < 0:
            self.alive = False

# ============================================================
# CHARACTER (AIO / OIA) - preserves stick figure joints
# ============================================================
class Character:
    def __init__(self, x, y, name=""):
        self.x = x; self.y = y; self.name = name
        self.hp = 100.0
        self.facing = 1
        self.vy = 0
        self.ground = GROUND
        self.sword_on = False
        self.anim = 0.0
        self.hair_swing = 0.0
        self.hair_vel = 0.0

    def update(self, dt, left=False, right=False):
        speed = 220
        self.anim += dt * 10
        moving = False
        if left:
            self.x -= speed * dt
            self.facing = -1
            moving = True
        if right:
            self.x += speed * dt
            self.facing = 1
            moving = True
        self.vy -= 1200 * dt
        self.y += self.vy * dt
        if self.y <= self.ground:
            self.y = self.ground
            self.vy = 0
        # preserve hair physics
        target = -self.facing * 12 if moving else 0
        self.hair_vel += (-self.hair_swing + target) * 8 * dt
        self.hair_vel *= 0.92
        self.hair_swing += self.hair_vel * 10 * dt
        # world bounds
        self.x = clamp(self.x, 80, WORLD_W - 80)

    def jump(self):
        if self.y <= self.ground + 1:
            self.vy = 550

    def joints(self):
        s = math.sin(self.anim) * 12
        return {
            "head": (self.x, self.y + 115),
            "neck": (self.x, self.y + 90),
            "hip":  (self.x, self.y + 45),
            "sh_l": (self.x, self.y + 85),
            "el_l": (self.x - 20 * self.facing, self.y + 60 + s),
            "wr_l": (self.x - 35 * self.facing, self.y + 75),
            "sh_r": (self.x, self.y + 85),
            "el_r": (self.x + 20 * self.facing, self.y + 60 - s),
            "wr_r": (self.x + 35 * self.facing, self.y + 75),
            "knee_l": (self.x - 15, self.y + 20 + s),
            "ank_l":  (self.x - 20, self.y),
            "knee_r": (self.x + 15, self.y + 20 - s),
            "ank_r":  (self.x + 20, self.y),
        }

# ============================================================
# ENEMY (ground stick figure with teeth)
# ============================================================
class Enemy:
    def __init__(self, x, y, speed, hp, spawn_side="right"):
        self.x = x; self.y = y
        self.hp = hp; self.speed = speed; self.alive = True
        self.facing = -1 if spawn_side == "right" else 1
        self.anim = 0.0
        self.spawn_side = spawn_side
        self.hurt_timer = 0.0

    def update(self, dt, px):
        self.anim += dt * 8
        self.hurt_timer = max(0, self.hurt_timer - dt)
        if self.x > px + 50:
            self.x -= self.speed * dt; self.facing = -1
        elif self.x < px - 50:
            self.x += self.speed * dt; self.facing = 1

    def joints(self):
        s = math.sin(self.anim) * 12
        return {
            "head": (self.x, self.y + 115),
            "neck": (self.x, self.y + 90),
            "hip":  (self.x, self.y + 45),
            "sh_l": (self.x, self.y + 85),
            "el_l": (self.x - 20 * self.facing, self.y + 60 + s),
            "wr_l": (self.x - 35 * self.facing, self.y + 75),
            "sh_r": (self.x, self.y + 85),
            "el_r": (self.x + 20 * self.facing, self.y + 60 - s),
            "wr_r": (self.x + 35 * self.facing, self.y + 75),
            "knee_l": (self.x - 15, self.y + 20 + s),
            "ank_l":  (self.x - 20, self.y),
            "knee_r": (self.x + 15, self.y + 20 - s),
            "ank_r":  (self.x + 20, self.y),
        }

# ============================================================
# FLYER (orange winged enemy)
# ============================================================
class Flyer:
    def __init__(self, x, y, speed):
        self.x = x; self.y = y; self.base_y = y
        self.speed = speed; self.hp = 40; self.alive = True
        self.anim = 0.0; self.shoot_timer = 1.0
        self.hurt_timer = 0.0

    def update(self, dt, px):
        self.anim += dt * 10
        self.hurt_timer = max(0, self.hurt_timer - dt)
        if self.x > px + 100:
            self.x -= self.speed * dt
        elif self.x < px - 100:
            self.x += self.speed * dt
        self.y = self.base_y + math.sin(self.anim) * 30
        self.shoot_timer -= dt

# ============================================================
# BOSS (large stick figure with crown)
# ============================================================
class Boss:
    def __init__(self, x, y, mult):
        self.x = x; self.y = y
        self.hp = 400 * mult
        self.max_hp = 400 * mult
        self.alive = True
        self.facing = -1
        self.anim = 0.0
        self.shoot_timer = 1.0
        self.jump_timer = 2.0
        self.hurt_timer = 0.0

    def update(self, dt, px):
        self.anim += dt * 6
        self.hurt_timer = max(0, self.hurt_timer - dt)
        if self.x > px + 120:
            self.x -= 40 * dt; self.facing = -1
        elif self.x < px - 120:
            self.x += 40 * dt; self.facing = 1
        self.jump_timer -= dt
        if self.jump_timer <= 0:
            self.jump_timer = 2.5
            self.y += 80
        self.shoot_timer -= dt
        if self.y > GROUND:
            self.y -= 100 * dt
        if self.y < GROUND:
            self.y = GROUND

# ============================================================
# GAME WORLD (with camera + touch input)
# ============================================================
class GameWorld(Widget):
    def __init__(self, level=1, difficulty="NORMAL", score=0,
                 on_level_complete=None, on_death=None, **kwargs):
        super().__init__(**kwargs)
        self.level = level
        self.difficulty = difficulty
        self.score = score
        self.on_level_complete = on_level_complete
        self.on_death = on_death
        self.cfg = LEVELS[level]
        self.mult = DIFFICULTY[difficulty]["mult"]

        self.player = Character(200, GROUND, name="AIO")
        self.oia = Character(2700, GROUND, name="OIA")
        self.oia_found = False
        self.camera_x = 0.0

        self.bullets = []
        self.enemy_bullets = []
        self.particles = []
        self.show_names_time = 4.0
        self.level_done = False
        self.dead_done = False
        self.time = 0.0
        self.spawn_timer = 2.0
        self.paused = False
        self.fire_cd = 0.0
        self.sword_cd = 0.0

        # enemies
        positions = [700, 900, 1100, 1250, 1400, 1550, 1700,
                     1850, 2000, 2200, 2400, 2600, 2800, 3000]
        self.enemies = []
        for i in range(self.cfg["count"]):
            side = "right" if i % 2 == 0 else "left"
            self.enemies.append(Enemy(
                positions[i % len(positions)], GROUND,
                self.cfg["enemy_speed"] * self.mult,
                self.cfg["enemy_hp"] * self.mult, spawn_side=side))

        fly_pos = [(800, 550), (1200, 600), (1600, 550),
                   (2000, 600), (2400, 550), (2800, 600)]
        self.flyers = []
        for i in range(self.cfg["flyers"]):
            px, py = fly_pos[i % len(fly_pos)]
            self.flyers.append(Flyer(px, py,
                                     self.cfg["flyer_speed"] * self.mult))

        self.boss = Boss(1450, GROUND, self.mult) if level == 3 else None

        # input state (set by TouchControls / keyboard)
        self.input = {"left": False, "right": False,
                      "jump_pressed": False, "fire_held": False,
                      "sword_pressed": False}

        # keyboard
        Window.bind(on_key_down=self._key_down, on_key_up=self._key_up)

        self.event = Clock.schedule_interval(self.update, 1/60)

    def _key_down(self, win, key, *a):
        if key in (276, 97):   self.input["left"] = True
        elif key in (275, 100): self.input["right"] = True
        elif key in (32, 119):  self.input["jump_pressed"] = True
        elif key in (106, 102): self.input["fire_held"] = True
        elif key in (107, 101): self.input["sword_pressed"] = True

    def _key_up(self, win, key, *a):
        if key in (276, 97):   self.input["left"] = False
        elif key in (275, 100): self.input["right"] = False
        elif key in (106, 102): self.input["fire_held"] = False

    def spawn_particles(self, x, y, count, color=(1, 1, 1, 1)):
        for _ in range(count):
            ang = random.uniform(0, 2 * math.pi)
            sp = random.uniform(80, 220)
            self.particles.append(Particle(
                x, y, math.cos(ang)*sp, math.sin(ang)*sp,
                random.uniform(0.25, 0.55), color, 5))

    def spawn_enemy_from_sides(self, dt):
        if self.level == 3:
            return
        self.spawn_timer -= dt
        alive = sum(1 for e in self.enemies if e.alive)
        if self.spawn_timer <= 0 and alive < 10:
            self.spawn_timer = 2.5 / self.mult
            side = random.choice(["left", "right"])
            if side == "right":
                sx = self.player.x + 700 + random.randint(0, 200)
            else:
                sx = self.player.x - 700 - random.randint(0, 200)
            sx = clamp(sx, 100, WORLD_W - 100)
            self.enemies.append(Enemy(
                sx, GROUND,
                self.cfg["enemy_speed"] * self.mult,
                self.cfg["enemy_hp"] * self.mult, spawn_side=side))

    def find_target(self):
        """Auto-target nearest enemy in facing direction (for mobile)."""
        best = None; best_d = 700
        candidates = []
        if self.boss and self.boss.alive:
            candidates.append(self.boss)
        for f in self.flyers:
            if f.alive: candidates.append(f)
        for e in self.enemies:
            if e.alive: candidates.append(e)
        for c in candidates:
            dx = c.x - self.player.x
            # only ahead of player
            if dx * self.player.facing > 0:
                d = abs(dx)
                if d < best_d:
                    best_d = d; best = c
        return best

    def update(self, dt):
        if self.paused or self.level_done or self.dead_done:
            return
        self.time += dt
        self.fire_cd = max(0, self.fire_cd - dt)
        self.sword_cd = max(0, self.sword_cd - dt)
        if self.show_names_time > 0:
            self.show_names_time -= dt

        # ----- player movement -----
        self.player.update(dt, self.input["left"], self.input["right"])

        # ----- jump -----
        if self.input["jump_pressed"]:
            self.player.jump()
            self.input["jump_pressed"] = False

        # ----- fire -----
        if self.input["fire_held"] and self.fire_cd <= 0:
            self.fire_cd = 0.18
            j = self.player.joints()
            target = self.find_target()
            self.bullets.append(Bullet(j["wr_r"][0], j["wr_r"][1],
                                       self.player.facing, target=target))
            self.spawn_particles(j["wr_r"][0], j["wr_r"][1], 2, (1, 1, 0.5, 1))

        # ----- sword -----
        if self.input["sword_pressed"] and self.sword_cd <= 0:
            self.sword_cd = 0.4
            self.player.sword_on = True
            Clock.schedule_once(
                lambda d: setattr(self.player, 'sword_on', False), 0.2)
            for e in self.enemies:
                if e.alive and abs(e.x - self.player.x) < 90:
                    e.hp -= 30
                    e.hurt_timer = 0.15
                    self.spawn_particles(e.x, e.y + 80, 6)
                    if e.hp <= 0:
                        e.alive = False; self.score += 200
            for f in self.flyers:
                if f.alive and abs(f.x - self.player.x) < 90 \
                   and abs(f.y - (self.player.y + 100)) < 90:
                    f.hp -= 30
                    self.spawn_particles(f.x, f.y, 6)
                    if f.hp <= 0:
                        f.alive = False; self.score += 300
            if self.boss and self.boss.alive \
               and abs(self.boss.x - self.player.x) < 120:
                self.boss.hp -= 40
                self.boss.hurt_timer = 0.15
                self.spawn_particles(self.boss.x, self.boss.y + 150, 10,
                                     (1, 1, 0.5, 1))
                if self.boss.hp <= 0:
                    self.boss.alive = False
                    self.score += 1000
                    self.oia_found = True
                    self.show_names_time = 4.0
            self.input["sword_pressed"] = False

        # ----- spawn enemies -----
        self.spawn_enemy_from_sides(dt)

        # ----- OIA follow -----
        if self.oia_found:
            if self.oia.x < self.player.x - 100:
                self.oia.update(dt, False, True)
            elif self.oia.x > self.player.x + 100:
                self.oia.update(dt, True, False)
            else:
                self.oia.update(dt)

        # ----- enemy updates -----
        for e in self.enemies:
            if not e.alive: continue
            e.update(dt, self.player.x)
            if abs(e.x - self.player.x) < 40 and \
               abs(e.y - self.player.y) < 60:
                self.player.hp -= self.cfg["damage"] * self.mult

        # ----- boss update -----
        if self.boss and self.boss.alive:
            self.boss.update(dt, self.player.x)
            if abs(self.boss.x - self.player.x) < 80 and \
               abs(self.boss.y - self.player.y) < 120:
                self.player.hp -= 0.4 * self.mult
            if self.boss.shoot_timer <= 0:
                self.boss.shoot_timer = 1.2 / self.mult
                for dy in (-20, 0, 20):
                    self.enemy_bullets.append(EnemyBullet(
                        self.boss.x, self.boss.y + 150 + dy,
                        self.player.x, self.player.y + 60, speed=300))

        # ----- flyer updates -----
        for f in self.flyers:
            if not f.alive: continue
            f.update(dt, self.player.x)
            if f.shoot_timer <= 0:
                f.shoot_timer = 1.5 / self.mult
                self.enemy_bullets.append(EnemyBullet(
                    f.x, f.y, self.player.x, self.player.y + 60))

        # ----- enemy bullets -----
        for eb in self.enemy_bullets[:]:
            eb.update(dt)
            if abs(eb.x - self.player.x) < 25 and \
               abs(eb.y - (self.player.y + 60)) < 50:
                self.player.hp -= 10
                self.spawn_particles(eb.x, eb.y, 4, (1, 0.3, 0.3, 1))
                eb.alive = False
            if not eb.alive:
                self.enemy_bullets.remove(eb)

        # ----- player bullets -----
        for b in self.bullets[:]:
            b.update(dt)
            for e in self.enemies:
                if e.alive and abs(b.x - e.x) < 30 and abs(b.y - e.y) < 120:
                    e.hp -= 25
                    e.hurt_timer = 0.15
                    self.spawn_particles(e.x, e.y + 80, 4)
                    b.alive = False
                    if e.hp <= 0:
                        e.alive = False
                        self.score += 200
                    break
            if b.alive:
                for f in self.flyers:
                    if f.alive and abs(b.x - f.x) < 35 and \
                       abs(b.y - f.y) < 40:
                        f.hp -= 25
                        f.hurt_timer = 0.15
                        self.spawn_particles(f.x, f.y, 4, (1, 0.7, 0.3, 1))
                        b.alive = False
                        if f.hp <= 0:
                            f.alive = False
                            self.score += 300
                        break
            if b.alive and self.boss and self.boss.alive and \
               abs(b.x - self.boss.x) < 70 and \
               abs(b.y - (self.boss.y + 150)) < 150:
                self.boss.hp -= 25
                self.boss.hurt_timer = 0.15
                self.spawn_particles(self.boss.x, self.boss.y + 150, 5,
                                     (1, 1, 0.5, 1))
                b.alive = False
                if self.boss.hp <= 0:
                    self.boss.alive = False
                    self.score += 1000
                    self.oia_found = True
                    self.show_names_time = 4.0
            if not b.alive:
                self.bullets.remove(b)

        # ----- particles -----
        for p in self.particles[:]:
            p.update(dt)
            if not p.alive:
                self.particles.remove(p)

        # ----- death -----
        if self.player.hp <= 0 and not self.dead_done:
            self.dead_done = True
            Clock.unschedule(self.event)
            Window.unbind(on_key_down=self._key_down)
            Window.unbind(on_key_up=self._key_up)
            if self.on_death:
                self.on_death(self.level, self.score)
            return

        # ----- level end -----
        if self.player.x > GOAL_X and not self.level_done:
            if self.level == 3 and self.boss and self.boss.alive:
                self.player.x = GOAL_X - 50
            else:
                self.level_done = True
                Clock.unschedule(self.event)
                Window.unbind(on_key_down=self._key_down)
                Window.unbind(on_key_up=self._key_up)
                if self.on_level_complete:
                    self.on_level_complete(self.level, self.score)
                return

        # ----- camera follow -----
        sw = Window.width
        target_cam = self.player.x - sw / 2
        target_cam = clamp(target_cam, 0, max(0, WORLD_W - sw))
        self.camera_x += (target_cam - self.camera_x) * 0.15

        self.draw()

    # ---------------- DRAW ----------------
    def draw_character(self, ch, is_oia=False):
        j = ch.joints()
        cx = self.camera_x
        Color(1, 1, 1, 1)
        Line(points=[j["neck"][0]-cx, j["neck"][1],
                     j["hip"][0]-cx, j["hip"][1]], width=3)
        Line(points=[j["sh_l"][0]-cx, j["sh_l"][1],
                     j["el_l"][0]-cx, j["el_l"][1],
                     j["wr_l"][0]-cx, j["wr_l"][1]], width=2.5)
        Line(points=[j["sh_r"][0]-cx, j["sh_r"][1],
                     j["el_r"][0]-cx, j["el_r"][1],
                     j["wr_r"][0]-cx, j["wr_r"][1]], width=2.5)
        Line(points=[j["hip"][0]-cx, j["hip"][1],
                     j["knee_l"][0]-cx, j["knee_l"][1],
                     j["ank_l"][0]-cx, j["ank_l"][1]], width=2.5)
        Line(points=[j["hip"][0]-cx, j["hip"][1],
                     j["knee_r"][0]-cx, j["knee_r"][1],
                     j["ank_r"][0]-cx, j["ank_r"][1]], width=2.5)
        Ellipse(pos=(j["head"][0]-cx-22, j["head"][1]-22), size=(44, 44))
        if ch.sword_on:
            Line(points=[j["wr_r"][0]-cx, j["wr_r"][1],
                         j["wr_r"][0]-cx + 50*ch.facing,
                         j["wr_r"][1] + 40], width=3)
        if is_oia:
            hx = j["head"][0] - cx; hy = j["head"][1]
            tie_x = hx - ch.facing * 18
            tie_y = hy + 15
            swing = ch.hair_swing + math.sin(ch.anim * 1.5) * 4
            for offset in (-3, 0, 3):
                Color(1, 1, 1, 1)
                Line(points=[tie_x + offset, tie_y,
                             tie_x + offset - ch.facing*5 + swing, tie_y - 15,
                             tie_x + offset - ch.facing*10 + swing*1.5, tie_y - 30,
                             tie_x + offset - ch.facing*8 + swing*1.2, tie_y - 45],
                     width=2)
            Color(1, 1, 0, 1)
            Ellipse(pos=(tie_x-4, tie_y-4), size=(8, 8))
            Color(1, 1, 1, 1)
            Line(points=[hx + ch.facing*5, hy+22,
                         hx + ch.facing*12, hy+14], width=2)
        if self.show_names_time > 0:
            draw_text(self.canvas, ch.name,
                      j["head"][0]-cx, j["head"][1]+50,
                      size=30, color=(1, 1, 1, 1))

    def draw_enemy(self, e):
        j = e.joints()
        cx = self.camera_x
        col = (1, 1, 1, 1) if e.hurt_timer <= 0 else (1, 0.5, 0.5, 1)
        Color(*col)
        Line(points=[j["neck"][0]-cx, j["neck"][1],
                     j["hip"][0]-cx, j["hip"][1]], width=3)
        Line(points=[j["sh_l"][0]-cx, j["sh_l"][1],
                     j["el_l"][0]-cx, j["el_l"][1],
                     j["wr_l"][0]-cx, j["wr_l"][1]], width=2.5)
        Line(points=[j["sh_r"][0]-cx, j["sh_r"][1],
                     j["el_r"][0]-cx, j["el_r"][1],
                     j["wr_r"][0]-cx, j["wr_r"][1]], width=2.5)
        Line(points=[j["hip"][0]-cx, j["hip"][1],
                     j["knee_l"][0]-cx, j["knee_l"][1],
                     j["ank_l"][0]-cx, j["ank_l"][1]], width=2.5)
        Line(points=[j["hip"][0]-cx, j["hip"][1],
                     j["knee_r"][0]-cx, j["knee_r"][1],
                     j["ank_r"][0]-cx, j["ank_r"][1]], width=2.5)
        Ellipse(pos=(j["head"][0]-cx-22, j["head"][1]-22), size=(44, 44))
        hx = j["head"][0] - cx; hy = j["head"][1]
        Color(0, 0, 0, 1)
        Ellipse(pos=(hx-10, hy+8), size=(5, 5))
        Ellipse(pos=(hx+5, hy+8), size=(5, 5))
        # teeth (preserved original zigzag)
        ty = hy - 8
        Color(*col)
        Line(points=[hx-12, ty, hx-8, ty-6, hx-4, ty, hx, ty-6,
                     hx+4, ty, hx+8, ty-6, hx+12, ty], width=2.5)

    def draw(self):
        self.canvas.clear()
        W = Window.width; H = Window.height
        cx = self.camera_x
        with self.canvas:
            # ---- SKY ----
            Color(*self.cfg["bg"])
            Rectangle(pos=(0, 0), size=(W, H))

            # ---- LEVEL 1: clouds + birds (parallax 0.3x) ----
            if self.level == 1:
                Color(1, 1, 1, 0.25)
                for i, (bx, by) in enumerate([(400, 750), (1000, 800),
                                              (1700, 760), (2400, 820)]):
                    mx = (bx - cx * 0.3 + math.sin(self.time*0.3+i)*20) % (W + 300) - 150
                    Ellipse(pos=(mx, by * H / 1000), size=(140, 50))
                    Ellipse(pos=(mx+50, by * H / 1000 + 20), size=(100, 40))
                    Ellipse(pos=(mx+90, by * H / 1000), size=(120, 45))
                Color(1, 1, 1, 0.7)
                for i in range(5):
                    bx = (300 + i*400 - cx*0.5 + math.sin(self.time*0.5+i)*30) % (W + 200) - 100
                    by = 700 + i*20 + math.sin(self.time*2+i)*10
                    flap = math.sin(self.time*8+i)*8
                    Line(points=[bx-15, by, bx, by+8+flap, bx+15, by], width=1.5)

            # ---- LEVEL 2: moon + stars (parallax 0.15x) ----
            if self.level == 2:
                Color(1, 1, 1, 1)
                star_list = [(200, 800), (500, 850), (800, 780), (1200, 900),
                             (1800, 820), (2400, 880), (2800, 800),
                             (600, 700), (1500, 750), (100, 650), (2000, 750)]
                for sx, sy in star_list:
                    px = (sx - cx*0.15) % (W + 100) - 50
                    tw = 6 + math.sin(self.time*3 + sx) * 3
                    Ellipse(pos=(px, sy*H/1000), size=(tw, tw))
                # moon
                mx = (2500 - cx*0.15) % (W + 200) - 100
                Color(1, 1, 0.8, 1)
                Ellipse(pos=(mx, 720*H/1000), size=(130, 130))
                Color(*self.cfg["bg"])
                Ellipse(pos=(mx+30, 740*H/1000), size=(100, 100))

            # ---- LEVEL 3: stars ----
            if self.level == 3:
                Color(1, 1, 1, 1)
                for sx, sy in [(200, 800), (500, 850), (800, 780), (1200, 900),
                               (1800, 820), (2400, 880), (2800, 800),
                               (600, 700), (1500, 750)]:
                    px = (sx - cx*0.15) % (W + 100) - 50
                    tw = 6 + math.sin(self.time*3 + sx) * 3
                    Ellipse(pos=(px, sy*H/1000), size=(tw, tw))

            # ---- GROUND ----
            Color(*self.cfg["ground"])
            Line(points=[0, GROUND, W, GROUND], width=3)

            # ---- GOAL FLAG (green) ----
            fx = GOAL_X - cx
            if -100 < fx < W + 100:
                Color(0, 1, 0, 1)
                Line(points=[fx, GROUND, fx, GROUND+120], width=3)
                Triangle(points=[fx, GROUND+120, fx, GROUND+80, fx+50, GROUND+100])

            # ---- OIA ----
            if self.oia_found and -100 < (self.oia.x - cx) < W + 100:
                self.draw_character(self.oia, is_oia=True)

            # ---- ENEMIES ----
            for e in self.enemies:
                if e.alive and -150 < (e.x - cx) < W + 150:
                    self.draw_enemy(e)

            # ---- FLYERS ----
            for f in self.flyers:
                if f.alive and -100 < (f.x - cx) < W + 100:
                    fx_ = f.x - cx
                    Color(1, 0.5, 0, 1) if f.hurt_timer <= 0 else Color(1, 1, 1, 1)
                    wing = math.sin(f.anim) * 20
                    Line(points=[fx_-30, f.y, fx_, f.y+20+wing, fx_+30, f.y], width=3)
                    Ellipse(pos=(fx_-15, f.y-15), size=(30, 30))
                    Color(0, 0, 0, 1)
                    Ellipse(pos=(fx_-8, f.y), size=(5, 5))
                    Ellipse(pos=(fx_+3, f.y), size=(5, 5))
                    Line(points=[fx_-10, f.y-8, fx_-5, f.y-13, fx_, f.y-8,
                                 fx_+5, f.y-13, fx_+10, f.y-8], width=2)

            # ---- BOSS ----
            if self.boss and self.boss.alive:
                bx = self.boss.x - cx; by = self.boss.y
                if -200 < bx < W + 200:
                    col = (1, 1, 1, 1) if self.boss.hurt_timer <= 0 \
                          else (1, 0.5, 0.5, 1)
                    Color(*col)
                    Line(points=[bx, by+180, bx, by+90], width=6)
                    Line(points=[bx, by+170, bx-50, by+120], width=5)
                    Line(points=[bx, by+170, bx+50, by+120], width=5)
                    Line(points=[bx, by+90, bx-40, by], width=5)
                    Line(points=[bx, by+90, bx+40, by], width=5)
                    Ellipse(pos=(bx-45, by+180), size=(90, 90))
                    Color(1, 1, 0, 1)
                    Triangle(points=[bx-30, by+270, bx-15, by+310, bx, by+270])
                    Triangle(points=[bx, by+270, bx+15, by+310, bx+30, by+270])
                    Color(0, 0, 0, 1)
                    Ellipse(pos=(bx-20, by+225), size=(12, 12))
                    Ellipse(pos=(bx+8, by+225), size=(12, 12))
                    Line(points=[bx-30, by+195, bx-20, by+185, bx-10, by+195,
                                 bx, by+185, bx+10, by+195, bx+20, by+185,
                                 bx+30, by+195], width=3.5)
                    # boss HP bar above
                    Color(1, 0, 0, 1)
                    Rectangle(pos=(bx-80, by+330), size=(160, 12))
                    Color(0, 1, 0, 1)
                    frac = self.boss.hp / self.boss.max_hp
                    Rectangle(pos=(bx-80, by+330), size=(160*frac, 12))
                    draw_text(self.canvas, "BOSS", bx, by+350,
                              size=24, color=(1, 1, 1, 1))

            # ---- BULLETS ----
            Color(1, 1, 0, 1)
            for b in self.bullets:
                bx = b.x - cx
                if 0 < bx < W:
                    Ellipse(pos=(bx-5, b.y-5), size=(10, 10))
            Color(1, 0, 0, 1)
            for eb in self.enemy_bullets:
                ex = eb.x - cx
                if 0 < ex < W:
                    Ellipse(pos=(ex-6, eb.y-6), size=(12, 12))

            # ---- PARTICLES ----
            for p in self.particles:
                px = p.x - cx
                if 0 < px < W:
                    alpha = p.life / p.max_life
                    Color(p.color[0], p.color[1], p.color[2], alpha)
                    Ellipse(pos=(px - p.size/2, p.y - p.size/2),
                            size=(p.size, p.size))

            # ---- PLAYER ----
            self.draw_character(self.player, is_oia=False)

# ============================================================
# TOUCH CONTROLS
# ============================================================
class TouchControls(Widget):
    def __init__(self, world, **kwargs):
        super().__init__(**kwargs)
        self.world = world
        self.joy_uid = None
        self.joy_center = (0, 0)
        self.joy_pos = [0.0, 0.0]
        self.joy_radius = 80
        self.buttons = {}   # name -> (cx, cy, r, uid)
        self._jump_lock = False
        self._sword_lock = False
        self.bind(size=self._layout, pos=self._layout)
        Clock.schedule_once(self._layout, 0.1)

    def _layout(self, *a):
        W, H = Window.width, Window.height
        self.joy_center = (W * 0.15, H * 0.22)
        self.joy_radius = min(W, H) * 0.11
        r = min(W, H) * 0.085
        self.buttons = {
            "jump":  [W * 0.88, H * 0.30, r, None],
            "fire":  [W * 0.75, H * 0.15, r, None],
            "sword": [W * 0.90, H * 0.14, r, None],
        }

    def on_touch_down(self, touch):
        x, y = touch.x, touch.y
        # joystick zone
        jx, jy = self.joy_center
        if (x - jx)**2 + (y - jy)**2 < (self.joy_radius * 1.8)**2:
            self.joy_uid = touch.uid
            return True
        # action buttons
        for name, (cx, cy, r, _) in self.buttons.items():
            if (x - cx)**2 + (y - cy)**2 < r*r:
                self.buttons[name][3] = touch.uid
                if name == "jump" and not self._jump_lock:
                    self.world.input["jump_pressed"] = True
                    self._jump_lock = True
                elif name == "sword" and not self._sword_lock:
                    self.world.input["sword_pressed"] = True
                    self._sword_lock = True
                elif name == "fire":
                    self.world.input["fire_held"] = True
                return True
        return False

    def on_touch_move(self, touch):
        if touch.uid == self.joy_uid:
            jx, jy = self.joy_center
            dx = touch.x - jx; dy = touch.y - jy
            mag = math.hypot(dx, dy)
            if mag > self.joy_radius:
                dx = dx / mag * self.joy_radius
                dy = dy / mag * self.joy_radius
            self.joy_pos = [dx / self.joy_radius, dy / self.joy_radius]
            self.world.input["left"] = self.joy_pos[0] < -0.25
            self.world.input["right"] = self.joy_pos[0] > 0.25
            return True
        return False

    def on_touch_up(self, touch):
        if touch.uid == self.joy_uid:
            self.joy_uid = None
            self.joy_pos = [0.0, 0.0]
            self.world.input["left"] = False
            self.world.input["right"] = False
            return True
        for name in list(self.buttons.keys()):
            cx, cy, r, uid = self.buttons[name]
            if uid == touch.uid:
                self.buttons[name][3] = None
                if name == "jump":
                    self._jump_lock = False
                elif name == "sword":
                    self._sword_lock = False
                elif name == "fire":
                    self.world.input["fire_held"] = False
                return True
        return False

    def redraw(self):
        self.canvas.clear()
        if not self.buttons:
            return
        with self.canvas:
            # joystick
            jx, jy = self.joy_center
            r = self.joy_radius
            Color(0.3, 0.3, 0.4, 0.35)
            Ellipse(pos=(jx - r, jy - r), size=(r*2, r*2))
            Color(0.7, 0.7, 0.9, 0.6)
            Line(circle=(jx, jy, r), width=2)
            kx = jx + self.joy_pos[0] * r * 0.7
            ky = jy + self.joy_pos[1] * r * 0.7
            kr = r * 0.42
            Color(0.9, 0.9, 1, 0.7)
            Ellipse(pos=(kx - kr, ky - kr), size=(kr*2, kr*2))
            # action buttons
            for name, (cx, cy, r, uid) in self.buttons.items():
                pressed = uid is not None
                Color(1, 0.9, 0.3, 0.85) if pressed \
                    else Color(0.3, 0.35, 0.55, 0.6)
                Ellipse(pos=(cx - r, cy - r), size=(r*2, r*2))
                Color(1, 1, 1, 0.85)
                Line(circle=(cx, cy, r), width=2)
                # icon
                Color(1, 1, 1, 0.9)
                if name == "jump":
                    Triangle(points=[cx - r*0.35, cy - r*0.2,
                                     cx + r*0.35, cy - r*0.2,
                                     cx, cy + r*0.45])
                elif name == "sword":
                    Line(points=[cx - r*0.35, cy - r*0.35,
                                 cx + r*0.35, cy + r*0.35], width=4)
                    Line(points=[cx + r*0.1, cy - r*0.35,
                                 cx + r*0.35, cy + r*0.35,
                                 cx - r*0.15, cy + r*0.1], width=3)
                elif name == "fire":
                    Color(1, 0.7, 0.3, 1)
                    Ellipse(pos=(cx - r*0.3, cy - r*0.3),
                            size=(r*0.6, r*0.6))

# ============================================================
# HUD
# ============================================================
class HUD(Widget):
    def __init__(self, world, **kwargs):
        super().__init__(**kwargs)
        self.world = world

    def redraw(self):
        self.canvas.clear()
        w = self.world
        if not w or not w.player:
            return
        W = Window.width; H = Window.height
        with self.canvas:
            draw_text(self.canvas, f"HP {int(w.player.hp)}", 80, H - 40,
                      size=22, color=(1, 1, 1, 1))
            draw_text(self.canvas, f"SCORE {w.score}", W/2, H - 40,
                      size=22, color=(1, 1, 1, 1))
            draw_text(self.canvas, f"LV {w.level}", W - 90, H - 40,
                      size=22, color=(1, 1, 1, 1))
            if w.boss and w.boss.alive:
                bw = W * 0.5
                bx = (W - bw) / 2
                Color(0.3, 0, 0, 0.85)
                Rectangle(pos=(bx-2, H-90), size=(bw+4, 18))
                Color(0, 0.8, 0, 1)
                frac = clamp(w.boss.hp / w.boss.max_hp, 0, 1)
                Rectangle(pos=(bx, H-88), size=(bw * frac, 14))
                draw_text(self.canvas, "BOSS", W/2, H-68, size=16,
                          color=(1, 1, 1, 1))

# ============================================================
# GAME SCREEN
# ============================================================
class GameScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.root = FloatLayout()
        self.add_widget(self.root)
        self.world = None
        self.hud = None
        self.controls = None
        self.hud_ev = None
        self.pause_overlay = None

    def start(self, level, difficulty, score=0):
        self.root.clear_widgets()
        self.world = GameWorld(level, difficulty, score,
                               on_level_complete=self._on_complete,
                               on_death=self._on_death)
        self.root.add_widget(self.world)
        self.hud = HUD(self.world)
        self.root.add_widget(self.hud)
        self.controls = TouchControls(self.world)
        self.root.add_widget(self.controls)

        pause_btn = Button(text="||", font_size='18sp',
                           size_hint=(0.07, 0.07),
                           pos_hint={"right": 0.99, "top": 0.99},
                           background_color=(0.2, 0.2, 0.3, 0.75))
        pause_btn.bind(on_press=lambda *a: self._show_pause())
        self.root.add_widget(pause_btn)

        self.hud_ev = Clock.schedule_interval(
            lambda dt: (self.hud.redraw(), self.controls.redraw()), 1/20)

    def _on_complete(self, level, score):
        self._cleanup()
        app = App.get_running_app()
        app.save_data["high_score"] = max(app.save_data["high_score"], score)
        if level + 1 <= 3:
            app.save_data["unlocked_stage"] = max(
                app.save_data["unlocked_stage"], level + 1)
        SaveManager.save(app.save_data)
        Clock.schedule_once(
            lambda dt: app.show_level_complete(level, score), 0.8)

    def _on_death(self, level, score):
        self._cleanup()
        app = App.get_running_app()
        Clock.schedule_once(
            lambda dt: app.show_death(level, score), 0.8)

    def _cleanup(self):
        if self.hud_ev:
            Clock.unschedule(self.hud_ev)
            self.hud_ev = None

    def _show_pause(self):
        if not self.world or self.world.paused:
            return
        self.world.paused = True
        ov = FloatLayout()
        with ov.canvas.before:
            Color(0, 0, 0, 0.7)
            self._pause_bg = Rectangle(pos=(0, 0),
                                        size=(Window.width, Window.height))
        ov.add_widget(Label(text="PAUSED", font_size='40sp',
                            color=(1, 1, 1, 1),
                            pos_hint={"center_x": 0.5, "top": 0.75}))
        box = BoxLayout(orientation='vertical', spacing=10,
                        size_hint=(0.4, 0.4),
                        pos_hint={"center_x": 0.5, "center_y": 0.4})
        for txt, cb in [("RESUME", self._resume),
                        ("RESTART", self._restart),
                        ("MAIN MENU", self._to_menu)]:
            b = Button(text=txt, font_size='20sp',
                       background_color=(0.25, 0.35, 0.6, 1))
            b.bind(on_press=lambda *a, c=cb: c())
            box.add_widget(b)
        ov.add_widget(box)
        self.root.add_widget(ov)
        self.pause_overlay = ov

    def _resume(self):
        if self.pause_overlay:
            self.root.remove_widget(self.pause_overlay)
            self.pause_overlay = None
        self.world.paused = False

    def _restart(self):
        self._cleanup()
        if self.pause_overlay:
            self.root.remove_widget(self.pause_overlay)
            self.pause_overlay = None
        level = self.world.level
        diff = self.world.difficulty
        self.start(level, diff, 0)

    def _to_menu(self):
        self._cleanup()
        if self.pause_overlay:
            self.root.remove_widget(self.pause_overlay)
            self.pause_overlay = None
        if self.world:
            self.world.paused = True
        App.get_running_app().go_menu()

# ============================================================
# MENU / OTHER SCREENS
# ============================================================
class MenuScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bg = Widget()
        self.add_widget(self.bg)
        self.root = FloatLayout()
        self.add_widget(self.root)
        self.anim_phase = 0.0
        Clock.schedule_interval(self._animate, 1/30)

    def on_enter(self):
        self._build_ui()

    def _build_ui(self):
        self.root.clear_widgets()
        self.root.add_widget(Label(text="APRESON", font_size='56sp',
                                   color=(1, 1, 1, 1),
                                   pos_hint={"center_x": 0.5, "top": 0.92}))
        self.root.add_widget(Label(text="AIO  +  OIA", font_size='26sp',
                                   color=(1, 1, 0.7, 1),
                                   pos_hint={"center_x": 0.5, "top": 0.82}))
        app = App.get_running_app()
        diff = app.save_data.get("difficulty", "NORMAL")
        self.root.add_widget(Label(text=f"Difficulty: {diff}",
                                   font_size='18sp',
                                   color=(1, 1, 0.5, 1),
                                   pos_hint={"center_x": 0.5, "top": 0.74}))

        box = BoxLayout(orientation='vertical', spacing=10,
                        size_hint=(0.5, 0.5),
                        pos_hint={"center_x": 0.5, "center_y": 0.4})
        buttons = [
            ("START GAME", self._start),
            ("STAGE SELECT", self._stage_select),
            ("DIFFICULTY", self._difficulty),
            ("ABOUT", self._about),
        ]
        for txt, cb in buttons:
            b = Button(text=txt, font_size='20sp',
                       background_color=(0.2, 0.3, 0.5, 1))
            b.bind(on_press=lambda *a, c=cb: c())
            box.add_widget(b)
        self.root.add_widget(box)
        quit_btn = Button(text="QUIT", font_size='16sp',
                          size_hint=(0.15, 0.06),
                          pos_hint={"right": 0.99, "y": 0.01},
                          background_color=(0.5, 0.15, 0.15, 1))
        quit_btn.bind(on_press=lambda *a: App.get_running_app().stop())
        self.root.add_widget(quit_btn)

    def _animate(self, dt):
        self.anim_phase += dt
        self.bg.canvas.clear()
        W, H = Window.width, Window.height
        with self.bg.canvas:
            Color(0.05, 0.05, 0.1)
            Rectangle(pos=(0, 0), size=(W, H))
            Color(0.12, 0.1, 0.22)
            Rectangle(pos=(0, H*0.4), size=(W, H*0.6))
            for i in range(40):
                sx = (i * 173 + self.anim_phase * 8) % W
                sy = (i * 89) % int(H * 0.7) + H * 0.2
                tw = 0.5 + 0.5 * math.sin(self.anim_phase * 2 + i)
                Color(1, 1, 1, tw * 0.8)
                Ellipse(pos=(sx, sy), size=(3, 3))
            # moon
            Color(0.95, 0.95, 1.0, 0.9)
            Ellipse(pos=(W*0.78, H*0.72), size=(90, 90))
            Color(0.12, 0.1, 0.22)
            Ellipse(pos=(W*0.78 + 18, H*0.72 + 12), size=(90, 90))
            # silhouetted AIO
            ax = W * 0.5
            ay = H * 0.2
            bob = math.sin(self.anim_phase * 2) * 4
            j = {
                "head": (ax, ay + 115 + bob),
                "neck": (ax, ay + 90 + bob),
                "hip": (ax, ay + 45 + bob),
                "sh_l": (ax, ay + 85 + bob),
                "el_l": (ax - 20, ay + 60 + bob),
                "wr_l": (ax - 35, ay + 75 + bob),
                "sh_r": (ax, ay + 85 + bob),
                "el_r": (ax + 20, ay + 60 + bob),
                "wr_r": (ax + 35, ay + 75 + bob),
                "knee_l": (ax - 15, ay + 20 + bob),
                "ank_l": (ax - 20, ay + bob),
                "knee_r": (ax + 15, ay + 20 + bob),
                "ank_r": (ax + 20, ay + bob),
            }
            Color(0.5, 0.6, 0.9, 0.55)
            Line(points=[*j["neck"], *j["hip"]], width=3)
            Line(points=[*j["sh_l"], *j["el_l"], *j["wr_l"]], width=2.5)
            Line(points=[*j["sh_r"], *j["el_r"], *j["wr_r"]], width=2.5)
            Line(points=[*j["hip"], *j["knee_l"], *j["ank_l"]], width=2.5)
            Line(points=[*j["hip"], *j["knee_r"], *j["ank_r"]], width=2.5)
            Ellipse(pos=(j["head"][0]-22, j["head"][1]-22), size=(44, 44))

    def _start(self):
        app = App.get_running_app()
        app.show_story(1)

    def _stage_select(self):
        App.get_running_app().show_stage_select()

    def _difficulty(self):
        App.get_running_app().show_difficulty()

    def _about(self):
        App.get_running_app().show_about()

class DifficultyScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.root = FloatLayout()
        self.add_widget(self.root)

    def on_enter(self):
        self.root.clear_widgets()
        self.root.add_widget(Label(text="DIFFICULTY", font_size='40sp',
                                   color=(1, 1, 1, 1),
                                   pos_hint={"center_x": 0.5, "top": 0.85}))
        app = App.get_running_app()
        cur = app.save_data.get("difficulty", "NORMAL")
        box = BoxLayout(orientation='vertical', spacing=10,
                        size_hint=(0.5, 0.5),
                        pos_hint={"center_x": 0.5, "center_y": 0.45})
        colors = {"EASY": (0.2, 0.5, 0.2, 1),
                  "NORMAL": (0.5, 0.5, 0.1, 1),
                  "HARD": (0.6, 0.1, 0.1, 1)}
        for diff in ["EASY", "NORMAL", "HARD"]:
            bg = colors[diff] if diff != cur else (0.2, 0.7, 0.3, 1)
            b = Button(text=diff + ("  ✓" if diff == cur else ""),
                       font_size='22sp', background_color=bg)
            b.bind(on_press=lambda *a, d=diff: self._set(d))
            box.add_widget(b)
        self.root.add_widget(box)
        back = Button(text="BACK", size_hint=(0.3, 0.08),
                      pos_hint={"center_x": 0.5, "y": 0.05},
                      background_color=(0.3, 0.3, 0.3, 1))
        back.bind(on_press=lambda *a: App.get_running_app().go_menu())
        self.root.add_widget(back)

    def _set(self, diff):
        app = App.get_running_app()
        app.save_data["difficulty"] = diff
        SaveManager.save(app.save_data)
        self.on_enter()

class StageSelectScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.root = FloatLayout()
        self.add_widget(self.root)

    def on_enter(self):
        self.root.clear_widgets()
        self.root.add_widget(Label(text="SELECT STAGE", font_size='40sp',
                                   color=(1, 1, 1, 1),
                                   pos_hint={"center_x": 0.5, "top": 0.85}))
        app = App.get_running_app()
        unlocked = app.save_data.get("unlocked_stage", 1)
        names = ["DARK LAND", "NIGHT", "NIGHT SKY - BOSS"]
        box = BoxLayout(orientation='vertical', spacing=10,
                        size_hint=(0.55, 0.5),
                        pos_hint={"center_x": 0.5, "center_y": 0.45})
        for i, name in enumerate(names):
            lvl = i + 1
            unlocked_ok = lvl <= unlocked
            b = Button(text=f"{'🔒 ' if not unlocked_ok else ''}LEVEL {lvl}: {name}",
                       font_size='18sp',
                       background_color=(0.25, 0.45, 0.25, 1)
                       if unlocked_ok else (0.3, 0.3, 0.3, 0.7),
                       disabled=not unlocked_ok)
            b.bind(on_press=lambda *a, L=lvl: self._pick(L))
            box.add_widget(b)
        self.root.add_widget(box)
        back = Button(text="BACK", size_hint=(0.3, 0.08),
                      pos_hint={"center_x": 0.5, "y": 0.05},
                      background_color=(0.3, 0.3, 0.3, 1))
        back.bind(on_press=lambda *a: App.get_running_app().go_menu())
        self.root.add_widget(back)

    def _pick(self, level):
        App.get_running_app().show_story(level)

class StoryScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.root = FloatLayout()
        self.add_widget(self.root)
        self.level = 1

    def show(self, level):
        self.level = level
        self.root.clear_widgets()
        self.root.add_widget(Label(text=STORY[level], font_size='24sp',
                                   color=(1, 1, 1, 1),
                                   halign='center', valign='middle',
                                   size_hint=(0.9, 0.5),
                                   pos_hint={"center_x": 0.5, "center_y": 0.55}))
        b = Button(text="START LEVEL", font_size='22sp',
                   size_hint=(0.4, 0.12),
                   pos_hint={"center_x": 0.5, "y": 0.1},
                   background_color=(0.2, 0.5, 0.2, 1))
        b.bind(on_press=lambda *a: self._start())
        self.root.add_widget(b)
        back = Button(text="MENU", size_hint=(0.3, 0.08),
                      pos_hint={"center_x": 0.5, "y": 0.02},
                      background_color=(0.3, 0.3, 0.3, 1))
        back.bind(on_press=lambda *a: App.get_running_app().go_menu())
        self.root.add_widget(back)

    def _start(self):
        app = App.get_running_app()
        app.start_game(self.level)

class AboutScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.root = FloatLayout()
        self.add_widget(self.root)

    def on_enter(self):
        self.root.clear_widgets()
        self.root.add_widget(Label(text="APRESON", font_size='44sp',
                                   color=(1, 1, 1, 1),
                                   pos_hint={"center_x": 0.5, "top": 0.9}))
        text = ("AIO lost his friend OIA.\n\n"
                "Travel 3 levels to find her:\n"
                "  · Dark Land\n"
                "  · Night\n"
                "  · Night Sky (Boss)\n\n"
                "Controls:\n"
                "  · Left joystick = move\n"
                "  · Jump / Fire / Sword buttons\n\n"
                "Made with Python + Kivy.")
        self.root.add_widget(Label(text=text, font_size='18sp',
                                   color=(1, 1, 1, 1),
                                   halign='center', valign='middle',
                                   size_hint=(0.9, 0.6),
                                   pos_hint={"center_x": 0.5, "center_y": 0.45}))
        back = Button(text="BACK", size_hint=(0.3, 0.08),
                      pos_hint={"center_x": 0.5, "y": 0.05},
                      background_color=(0.3, 0.3, 0.3, 1))
        back.bind(on_press=lambda *a: App.get_running_app().go_menu())
        self.root.add_widget(back)

class EndScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.root = FloatLayout()
        self.add_widget(self.root)

    def show_end(self, won, level, score):
        self.root.clear_widgets()
        if won:
            if level < 3:
                title = f"LEVEL {level} COMPLETE!"
                msg = f"Score: {score}\n\nNext: Level {level + 1}"
                btn_text = "NEXT LEVEL"
                cb = lambda *a: App.get_running_app().show_story(level + 1)
            else:
                title = "YOU FOUND OIA!"
                msg = (f"AIO: OIA! Finally I found you!\n"
                       f"OIA: AIO! I knew you would come!\n\n"
                       f"Together again!\nScore: {score}\n\nTHE END")
                btn_text = "PLAY AGAIN"
                cb = lambda *a: App.get_running_app().show_story(1)
        else:
            title = "YOU DIED!"
            msg = f"Level {level}\nScore: {score}\n\nTry again!"
            btn_text = "RETRY LEVEL"
            cb = lambda *a: App.get_running_app().show_story(level)

        color = (0.3, 1, 0.3, 1) if won else (1, 0.3, 0.3, 1)
        self.root.add_widget(Label(text=title, font_size='38sp',
                                   color=color,
                                   pos_hint={"center_x": 0.5, "top": 0.85}))
        self.root.add_widget(Label(text=msg, font_size='22sp',
                                   color=(1, 1, 1, 1),
                                   halign='center', valign='middle',
                                   size_hint=(0.9, 0.5),
                                   pos_hint={"center_x": 0.5, "center_y": 0.55}))
        b = Button(text=btn_text, font_size='22sp',
                   size_hint=(0.4, 0.12),
                   pos_hint={"center_x": 0.5, "y": 0.1},
                   background_color=(0.2, 0.5, 0.2, 1) if won
                   else (0.6, 0.2, 0.2, 1))
        b.bind(on_press=cb)
        self.root.add_widget(b)
        back = Button(text="MAIN MENU", size_hint=(0.3, 0.08),
                      pos_hint={"center_x": 0.5, "y": 0.02},
                      background_color=(0.3, 0.3, 0.3, 1))
        back.bind(on_press=lambda *a: App.get_running_app().go_menu())
        self.root.add_widget(back)

# ============================================================
# APP
# ============================================================
class ApresonApp(App):
    def build(self):
        self.title = "APRESON ULTIMATE"
        self.save_data = SaveManager.load()
        self.sm = ScreenManager(transition=FadeTransition(duration=0.25))
        self.sm.add_widget(MenuScreen(name="menu"))
        self.sm.add_widget(DifficultyScreen(name="difficulty"))
        self.sm.add_widget(StageSelectScreen(name="stages"))
        self.sm.add_widget(StoryScreen(name="story"))
        self.sm.add_widget(AboutScreen(name="about"))
        self.sm.add_widget(GameScreen(name="game"))
        self.sm.add_widget(EndScreen(name="end"))
        return self.sm

    def on_start(self):
        try:
            Window.fullscreen = 'auto'
        except Exception:
            pass

    def go_menu(self):
        self.sm.current = "menu"

    def show_difficulty(self):
        self.sm.current = "difficulty"

    def show_stage_select(self):
        self.sm.current = "stages"

    def show_story(self, level):
        self.sm.get_screen("story").show(level)
        self.sm.current = "story"

    def show_about(self):
        self.sm.current = "about"

    def start_game(self, level):
        gs = self.sm.get_screen("game")
        gs.start(level, self.save_data.get("difficulty", "NORMAL"))
        self.sm.current = "game"

    def show_level_complete(self, level, score):
        self.sm.get_screen("end").show_end(True, level, score)
        self.sm.current = "end"

    def show_death(self, level, score):
        self.sm.get_screen("end").show_end(False, level, score)
        self.sm.current = "end"

if __name__ == "__main__":
    ApresonApp().run()