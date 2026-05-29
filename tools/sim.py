#!/usr/bin/env python3
"""
Simulador local do RetroSC Pong (RP2040).

Reproduz em Python a logica de jogo e o rendering do framebuffer 1-bit
de src/game.c, carregando os mesmos bitmaps e a mesma fonte direto dos
arquivos C. Util para iterar em telas/UX antes de flashear hardware.

Uso:
    python tools/sim.py

Controles:
    Mouse Y na metade esquerda  -> raquete P1
    Mouse Y na metade direita   -> raquete P2
    Espaco                      -> botao START
    R                           -> reseta high-scores em memoria
    Q ou ESC                    -> sair

Notas:
- Audio nao e simulado (e PWM dedicado no hardware).
- A janela e 3x o framebuffer = 768x576.
- A persistencia de high-scores em flash NAO e simulada (so RAM).
"""

import os
import re
import sys
import math
import random
import time
from pathlib import Path

import pygame

# ============================================================
# Constantes (espelham src/config.h)
# ============================================================
FB_W, FB_H        = 256, 192
SCALE             = 3
WIN_SCORE         = 7
PADDLE_W, PADDLE_H = 3, 24
BALL_SIZE         = 3
PADDLE_MARGIN     = 6
BALL_SPEED_INIT_Q = 0x180
BALL_SPEED_MAX_Q  = 0x500
BALL_SPEED_STEP_Q = 0x020
HISCORE_COUNT     = 5
INITIALS_LEN      = 3
FONT_CELL_W       = 6

# ============================================================
# Estados
# ============================================================
(GS_ATTRACT, GS_COUNTDOWN, GS_PLAY, GS_ROUND_END,
 GS_GAME_OVER, GS_ENTER_INITIALS, GS_HIGH_SCORES) = range(7)

# ============================================================
# Carregar assets de src/assets.c
# ============================================================
def load_assets():
    root = Path(__file__).parent.parent
    text = (root / "src" / "assets.c").read_text(encoding="utf-8", errors="replace")
    assets = {}
    for sym in ("retrosc_logo",):
        m = re.search(rf"{sym}_data\[\d+\]\s*=\s*\{{(.*?)\}};", text, re.DOTALL)
        if not m:
            raise RuntimeError(f"Nao achei {sym}_data em assets.c")
        hexs = re.findall(r"0x[0-9A-Fa-f]+", m.group(1))
        data = bytes(int(h, 16) for h in hexs)
        prefix = sym.upper()
        for k in ("W", "H", "STRIDE"):
            v = re.search(rf"{prefix}_{k}\s*=\s*(\d+)", text)
            if not v:
                raise RuntimeError(f"Nao achei {prefix}_{k}")
            assets[f"{sym}_{k}"] = int(v.group(1))
        assets[sym] = data
    return assets

# ============================================================
# Carregar fonte de src/font.c (formato C: ['X' - 0x20] = {bytes})
# ============================================================
def load_font():
    root = Path(__file__).parent.parent
    text = (root / "src" / "font.c").read_text(encoding="utf-8", errors="replace")
    glyphs = {}
    pattern = re.compile(r"\['([^']+|\\')'\s*-\s*0x20\]\s*=\s*\{([^}]+)\}", re.DOTALL)
    for m in pattern.finditer(text):
        ch = m.group(1)
        if ch.startswith("\\"):
            ch = {"\\'": "'", "\\\\": "\\"}.get(ch, ch[-1])
        bytes_ = [int(h, 16) for h in re.findall(r"0x[0-9A-Fa-f]+", m.group(2))]
        if len(bytes_) >= 7:
            glyphs[ch] = bytes_[:7]
    # garante espaco
    glyphs.setdefault(" ", [0]*7)
    return glyphs

# ============================================================
# Framebuffer + primitivas de desenho (mesma logica de gfx.c)
# ============================================================
class FB:
    def __init__(self):
        # numpy seria mais rapido, mas mantenho dep so pygame
        self.px = bytearray(FB_W * FB_H)

    def clear(self, color=0):
        v = 0xFF if color else 0
        for i in range(len(self.px)):
            self.px[i] = v

    def set(self, x, y, color):
        if 0 <= x < FB_W and 0 <= y < FB_H:
            self.px[y * FB_W + x] = 0xFF if color else 0

    def fill_rect(self, x, y, w, h, color):
        v = 0xFF if color else 0
        x0 = max(0, x); x1 = min(FB_W, x + w)
        y0 = max(0, y); y1 = min(FB_H, y + h)
        for yy in range(y0, y1):
            base = yy * FB_W
            for xx in range(x0, x1):
                self.px[base + xx] = v

    def blit_1bit(self, data, bw, bh, x, y, color=1):
        stride = (bw + 7) // 8
        v = 0xFF if color else 0
        for row in range(bh):
            dy = y + row
            if not (0 <= dy < FB_H):
                continue
            base = dy * FB_W
            for col in range(bw):
                dx = x + col
                if not (0 <= dx < FB_W):
                    continue
                b = data[row * stride + (col >> 3)]
                if b & (0x80 >> (col & 7)):
                    self.px[base + dx] = v

    def dotted_vline(self, x, y0, y1, dot_h, gap_h):
        phase = 0
        draw = 1
        for y in range(y0, y1):
            if 0 <= y < FB_H and 0 <= x < FB_W:
                self.px[y * FB_W + x] = 0xFF if draw else 0
            phase += 1
            if draw and phase >= dot_h:
                phase = 0; draw = 0
            elif (not draw) and phase >= gap_h:
                phase = 0; draw = 1

def gfx_text(fb, glyphs, x, y, s, scale, color=1):
    cx = x
    for c in s:
        cc = c.upper() if c.isalpha() else c
        g = glyphs.get(cc, glyphs[" "])
        for r in range(7):
            row = g[r]
            for col in range(5):
                if row & (0x80 >> col):
                    fb.fill_rect(cx + col*scale, y + r*scale, scale, scale, color)
        cx += 6 * scale

def text_width(s, scale):
    return len(s) * 6 * scale

def center_text(fb, glyphs, y, s, scale, color=1):
    w = text_width(s, scale)
    gfx_text(fb, glyphs, (FB_W - w)//2, y, s, scale, color)

# ============================================================
# Estado do jogo
# ============================================================
class Game:
    def __init__(self, assets, glyphs):
        self.assets = assets
        self.glyphs = glyphs
        self.fb = FB()
        self.state = GS_ATTRACT
        self.state_timer = 0
        self.score = [0, 0]
        self.paddle_y = [132, 132]   # zona de demo (atract)
        self.last_winner = 0
        self.ball_x = (FB_W // 2) << 8
        self.ball_y = (FB_H - 40) << 8
        self.ball_vx = BALL_SPEED_INIT_Q
        self.ball_vy = BALL_SPEED_INIT_Q // 2
        self.ball_speed_q = BALL_SPEED_INIT_Q
        self.last_pot_value = [2048, 2048]
        self.baseline_pot = [2048, 2048]
        self.movement_remaining = 0
        # Highscore: (score, player, "ABC")
        self.hiscores = [(0, 0, "   ")] * HISCORE_COUNT
        # Estado de entrada de iniciais
        self.initials_buf = list("   ")
        self.initials_slot = 0
        self.initials_armed = False
        # Input mockado por mouse: cada frame setamos
        self.input_pot = [2048, 2048]
        self.input_start = False

    def set_state(self, s):
        self.state = s
        self.state_timer = 0

    def input_paddle_y(self, p):
        v = self.input_pot[p]
        rng = FB_H - PADDLE_H
        y = (v * rng) // 4095
        return max(0, min(rng, y))

    def poll_input(self):
        for i in (0, 1):
            d = abs(self.input_pot[i] - self.baseline_pot[i])
            if d > 40:
                self.movement_remaining = 20
                self.baseline_pot[i] = self.input_pot[i]
        if self.movement_remaining > 0:
            self.movement_remaining -= 1

    def serve_ball(self, direction):
        self.ball_x = (FB_W // 2) << 8
        self.ball_y = (FB_H // 2) << 8
        self.ball_speed_q = BALL_SPEED_INIT_Q
        r = (random.randint(0, 255)) - 128
        vy_frac = (r * self.ball_speed_q) // 256
        s2 = self.ball_speed_q * self.ball_speed_q
        vy2 = vy_frac * vy_frac
        vx2 = max(0, s2 - vy2)
        vx_abs = int(math.sqrt(vx2)) or self.ball_speed_q
        self.ball_vx = direction * vx_abs
        self.ball_vy = vy_frac

    def reset_round(self, last_scorer):
        self.paddle_y[0] = (FB_H - PADDLE_H)//2
        self.paddle_y[1] = (FB_H - PADDLE_H)//2
        self.serve_ball(-1 if last_scorer == 1 else +1)

    def update_paddles_human(self):
        self.paddle_y[0] = self.input_paddle_y(0)
        self.paddle_y[1] = self.input_paddle_y(1)

    def update_paddles_demo(self):
        DEMO_PADDLE_Y_MIN = 116
        for i in (0, 1):
            target = (self.ball_y >> 8) - PADDLE_H // 2
            diff = target - self.paddle_y[i]
            speed = 2
            if abs(diff) > speed:
                diff = speed if diff > 0 else -speed
            self.paddle_y[i] += diff
            self.paddle_y[i] = max(DEMO_PADDLE_Y_MIN,
                                   min(FB_H - PADDLE_H, self.paddle_y[i]))

    def on_paddle_hit(self, idx):
        pad_top = self.paddle_y[idx]
        pad_center = pad_top + PADDLE_H // 2
        by = self.ball_y >> 8
        offset = by - pad_center
        if self.ball_speed_q < BALL_SPEED_MAX_Q:
            self.ball_speed_q += BALL_SPEED_STEP_Q
        vy_frac = (offset * self.ball_speed_q) // PADDLE_H
        s2 = self.ball_speed_q * self.ball_speed_q
        vx2 = max(0, s2 - vy_frac * vy_frac)
        vx_abs = int(math.sqrt(vx2)) or (self.ball_speed_q // 2)
        self.ball_vx = +vx_abs if idx == 0 else -vx_abs
        self.ball_vy = vy_frac

    def physics(self):
        self.ball_x += self.ball_vx
        self.ball_y += self.ball_vy
        # paredes
        if self.ball_y < 0:
            self.ball_y = 0; self.ball_vy = -self.ball_vy
        max_y = (FB_H - BALL_SIZE) << 8
        if self.ball_y > max_y:
            self.ball_y = max_y; self.ball_vy = -self.ball_vy
        bx = self.ball_x >> 8
        by = self.ball_y >> 8
        # raquete esq
        p0_x = PADDLE_MARGIN
        if self.ball_vx < 0 and bx <= p0_x + PADDLE_W and bx + BALL_SIZE > p0_x:
            if by + BALL_SIZE > self.paddle_y[0] and by < self.paddle_y[0] + PADDLE_H:
                self.ball_x = (p0_x + PADDLE_W) << 8
                self.on_paddle_hit(0)
        # raquete dir
        p1_x = FB_W - PADDLE_MARGIN - PADDLE_W
        if self.ball_vx > 0 and bx + BALL_SIZE >= p1_x and bx < p1_x + PADDLE_W:
            if by + BALL_SIZE > self.paddle_y[1] and by < self.paddle_y[1] + PADDLE_H:
                self.ball_x = (p1_x - BALL_SIZE) << 8
                self.on_paddle_hit(1)
        if bx + BALL_SIZE < 0:
            self.score[1] += 1
            self.set_state(GS_ROUND_END)
        elif bx > FB_W:
            self.score[0] += 1
            self.set_state(GS_ROUND_END)

    def hi_qualifies(self, score):
        return any(score > s for s, _, _ in self.hiscores)

    def hi_consider(self, score, player, initials):
        pos = -1
        for i, (s, _, _) in enumerate(self.hiscores):
            if score > s:
                pos = i; break
        if pos < 0:
            return
        ini = "".join(c if "A" <= c <= "Z" else " " for c in initials)
        new = (score, player, (ini + "   ")[:3])
        self.hiscores = self.hiscores[:pos] + [new] + self.hiscores[pos:-1]

    # ============== desenho ===============
    def draw_field(self):
        self.fb.dotted_vline(FB_W // 2, 0, FB_H, 4, 4)

    def draw_paddles(self):
        self.fb.fill_rect(PADDLE_MARGIN, self.paddle_y[0], PADDLE_W, PADDLE_H, 1)
        self.fb.fill_rect(FB_W - PADDLE_MARGIN - PADDLE_W, self.paddle_y[1], PADDLE_W, PADDLE_H, 1)

    def draw_ball(self):
        self.fb.fill_rect(self.ball_x >> 8, self.ball_y >> 8, BALL_SIZE, BALL_SIZE, 1)

    def draw_scores(self):
        s0 = str(self.score[0]); s1 = str(self.score[1])
        gfx_text(self.fb, self.glyphs, FB_W//2 - 30 - text_width(s0, 3), 8, s0, 3, 1)
        gfx_text(self.fb, self.glyphs, FB_W//2 + 30, 8, s1, 3, 1)

    def draw_attract(self):
        self.fb.clear(0)
        lw = self.assets["retrosc_logo_W"]
        lh = self.assets["retrosc_logo_H"]
        self.fb.blit_1bit(self.assets["retrosc_logo"], lw, lh, (FB_W - lw)//2, 4, 1)
        center_text(self.fb, self.glyphs, 4 + lh + 8, "RETRO PONG", 3)
        self.fb.dotted_vline(FB_W // 2, FB_H - 60, FB_H - 12, 4, 4)
        self.fb.fill_rect(PADDLE_MARGIN, self.paddle_y[0], PADDLE_W, PADDLE_H, 1)
        self.fb.fill_rect(FB_W - PADDLE_MARGIN - PADDLE_W, self.paddle_y[1], PADDLE_W, PADDLE_H, 1)
        self.draw_ball()
        if ((self.state_timer >> 5) & 1) == 0:
            center_text(self.fb, self.glyphs, FB_H - 9, "MOVA UM POTENCIOMETRO", 1)

    def draw_countdown(self):
        self.fb.clear(0)
        self.draw_field(); self.draw_scores(); self.draw_paddles()
        sec_left = 3 - self.state_timer // 60
        if sec_left > 0:
            center_text(self.fb, self.glyphs, FB_H // 2 - 10, str(sec_left), 3)
        else:
            center_text(self.fb, self.glyphs, FB_H // 2 - 10, "GO", 3)

    def draw_play(self):
        self.fb.clear(0)
        self.draw_field(); self.draw_scores(); self.draw_paddles(); self.draw_ball()

    def draw_round_end(self):
        self.draw_play()

    def draw_game_over(self):
        self.fb.clear(0)
        self.draw_scores()
        msg = f"JOGADOR {self.last_winner} VENCE"
        center_text(self.fb, self.glyphs, FB_H//2 - 8, msg, 1)
        if (self.state_timer >> 4) & 1:
            center_text(self.fb, self.glyphs, FB_H//2 + 8, "GAME OVER", 2)

    def draw_highscores(self):
        self.fb.clear(0)
        center_text(self.fb, self.glyphs, 8, "HIGH SCORES", 2)
        y = 36
        for i, (s, p, ini) in enumerate(self.hiscores):
            if s > 0:
                line = f"{i+1}. {ini}  {s:2d}  P{p}"
            else:
                line = f"{i+1}. ---   -    "
            gfx_text(self.fb, self.glyphs, 60, y, line, 1, 1)
            y += 14
        center_text(self.fb, self.glyphs, FB_H - 12, "RETRO PONG", 1)

    def draw_enter_initials(self):
        self.fb.clear(0)
        center_text(self.fb, self.glyphs, 8, "NEW HIGH SCORE!", 2)
        win = max(self.score)
        center_text(self.fb, self.glyphs, 32, f"JOGADOR {self.last_winner} - {win}", 1)

        slot_w = FONT_CELL_W * 4
        gap = 8
        total = INITIALS_LEN * slot_w + (INITIALS_LEN - 1) * gap
        x0 = (FB_W - total) // 2
        y0 = 64
        for i in range(INITIALS_LEN):
            sx = x0 + i * (slot_w + gap)
            c = self.initials_buf[i]
            s = c if c != " " else ("_" if i != self.initials_slot else " ")
            # slot atual pisca
            show = not (i == self.initials_slot and ((self.state_timer >> 3) & 1))
            if show:
                gfx_text(self.fb, self.glyphs, sx, y0, s, 4, 1)
            if i == self.initials_slot:
                self.fb.fill_rect(sx, y0 + 8*4 + 2, slot_w - 4, 2, 1)
        center_text(self.fb, self.glyphs, FB_H - 30, "POT = LETRA", 1)
        if ((self.state_timer >> 5) & 1) == 0:
            center_text(self.fb, self.glyphs, FB_H - 18, "START PARA CONFIRMAR", 1)
        center_text(self.fb, self.glyphs, FB_H - 8, f"P{self.last_winner}", 1)

    # ============== frame por estado ===============
    def frame(self):
        # Espelha game_frame() de game.c
        if self.state == GS_ATTRACT:
            self.update_paddles_demo()
            if self.ball_x < ((PADDLE_MARGIN + PADDLE_W) << 8):
                self.ball_vx = abs(self.ball_vx)
            if self.ball_x > ((FB_W - PADDLE_MARGIN - PADDLE_W - BALL_SIZE) << 8):
                self.ball_vx = -abs(self.ball_vx)
            min_y = (FB_H - 70) << 8
            max_y = (FB_H - 6 - BALL_SIZE) << 8
            if self.ball_y < min_y: self.ball_y = min_y; self.ball_vy = abs(self.ball_vy)
            if self.ball_y > max_y: self.ball_y = max_y; self.ball_vy = -abs(self.ball_vy)
            self.ball_x += self.ball_vx
            self.ball_y += self.ball_vy
            if self.movement_remaining > 0 or self.input_start:
                self.score = [0, 0]; self.last_winner = 0
                self.reset_round(0); self.set_state(GS_COUNTDOWN)
                self.state_timer += 1
                return
            self.draw_attract()
        elif self.state == GS_COUNTDOWN:
            self.update_paddles_human(); self.draw_countdown()
            if self.state_timer >= 3*60 + 30: self.set_state(GS_PLAY)
        elif self.state == GS_PLAY:
            self.update_paddles_human(); self.physics(); self.draw_play()
        elif self.state == GS_ROUND_END:
            self.update_paddles_human(); self.draw_round_end()
            if self.state_timer >= 60:
                if self.score[0] >= WIN_SCORE or self.score[1] >= WIN_SCORE:
                    self.last_winner = 1 if self.score[0] > self.score[1] else 2
                    self.set_state(GS_GAME_OVER)
                else:
                    self.reset_round(1 if self.score[0] > self.score[1] else 2)
                    self.set_state(GS_COUNTDOWN)
        elif self.state == GS_GAME_OVER:
            self.draw_game_over()
            if self.state_timer >= 3*60:
                win = max(self.score)
                if self.hi_qualifies(win):
                    self.initials_armed = False
                    self.set_state(GS_ENTER_INITIALS)
                else:
                    self.set_state(GS_HIGH_SCORES)
        elif self.state == GS_ENTER_INITIALS:
            if not self.initials_armed:
                self.initials_buf = [" "] * INITIALS_LEN
                self.initials_slot = 0
                self.initials_armed = True
            if self.initials_slot < INITIALS_LEN:
                pot = self.input_pot[self.last_winner - 1]
                idx = max(0, min(25, (pot * 26) // 4096))
                self.initials_buf[self.initials_slot] = chr(ord("A") + idx)
                if self.input_start:
                    self.initials_slot += 1
            else:
                win = max(self.score)
                self.hi_consider(win, self.last_winner, "".join(self.initials_buf))
                self.set_state(GS_HIGH_SCORES)
                self.state_timer += 1
                return
            self.draw_enter_initials()
        elif self.state == GS_HIGH_SCORES:
            self.draw_highscores()
            if self.state_timer >= 10*60 or self.input_start:
                self.movement_remaining = 0
                self.baseline_pot = list(self.input_pot)
                self.set_state(GS_ATTRACT)
                self.ball_x = (FB_W // 2) << 8
                self.ball_y = (FB_H - 40) << 8
                self.ball_vx = BALL_SPEED_INIT_Q
                self.ball_vy = BALL_SPEED_INIT_Q // 2
        self.state_timer += 1

# ============================================================
# Main loop com pygame
# ============================================================
def main():
    print(__doc__)
    assets = load_assets()
    glyphs = load_font()
    game = Game(assets, glyphs)

    pygame.init()
    win = pygame.display.set_mode((FB_W * SCALE, FB_H * SCALE))
    pygame.display.set_caption("RetroSC Pong — Simulador")
    clock = pygame.time.Clock()
    surf = pygame.Surface((FB_W, FB_H), depth=8)
    palette = [(0, 0, 0)] * 256
    palette[0] = (0, 0, 0)
    palette[255] = (240, 240, 240)
    surf.set_palette(palette)

    running = True
    while running:
        game.input_start = False
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False
            elif ev.type == pygame.KEYDOWN:
                if ev.key in (pygame.K_ESCAPE, pygame.K_q):
                    running = False
                elif ev.key == pygame.K_SPACE:
                    game.input_start = True
                elif ev.key == pygame.K_r:
                    game.hiscores = [(0,0)] * HISCORE_COUNT
                    print("Highscores zeradas.")

        # mapeia mouse Y para pots
        mx, my = pygame.mouse.get_pos()
        ny = max(0, min(FB_H * SCALE - 1, my))
        pot = (ny * 4095) // (FB_H * SCALE - 1)
        if mx < FB_W * SCALE // 2:
            game.input_pot[0] = pot
        else:
            game.input_pot[1] = pot

        game.poll_input()
        game.frame()

        # copia framebuffer (bytearray) para surface 1-byte-per-pixel e escala
        buf = bytes(game.fb.px)
        try:
            pygame.surfarray.blit_array  # noqa: ensure numpy not required
        except Exception:
            pass
        surf_pix = pygame.image.frombuffer(buf, (FB_W, FB_H), "P")
        surf_pix.set_palette(palette)
        scaled = pygame.transform.scale(surf_pix, (FB_W * SCALE, FB_H * SCALE))
        win.blit(scaled, (0, 0))
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()

if __name__ == "__main__":
    main()
