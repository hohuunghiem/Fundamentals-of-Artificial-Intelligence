"""
gui_pygame.py - Bloxorz GUI built with pygame  (pip install pygame).

Run:  python gui_pygame.py        (or  python main.py pygame)
"""
import pygame

from game import SPLIT, STAND, orientation
from gui_common import (COLORS, HELP_TEXT, SOLVER_NAMES, Session, bridge_color, switch_color)

WIN_W, WIN_H = 1020, 720
PANEL_W = 280
BOARD_W = WIN_W - PANEL_W

KEY_TO_DIR = {pygame.K_UP: "U", pygame.K_w: "U", pygame.K_DOWN: "D", pygame.K_s: "D",
              pygame.K_LEFT: "L", pygame.K_a: "L", pygame.K_RIGHT: "R", pygame.K_d: "R"}


def rgb(hex_color: str):
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


C = {k: rgb(v) for k, v in COLORS.items()}


def wrap_text(text, font, max_width):
    """Split `text` into lines no wider than max_width pixels (keeps explicit newlines)."""
    lines = []
    for paragraph in text.split("\n"):
        line = ""
        for word in paragraph.split(" "):
            trial = word if not line else line + " " + word
            if font.size(trial)[0] <= max_width or not line:
                line = trial
            else:
                lines.append(line)
                line = word
        lines.append(line)
    return lines


class Button:
    def __init__(self, rect, label, callback):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.callback = callback

    def draw(self, surface, font, mouse):
        color = (77, 87, 127) if self.rect.collidepoint(mouse) else (58, 65, 96)
        pygame.draw.rect(surface, color, self.rect, border_radius=6)
        text = font.render(self.label, True, C["text"])
        surface.blit(text, text.get_rect(center=self.rect.center))


class App:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Bloxorz - pygame")
        self.screen = pygame.display.set_mode((WIN_W, WIN_H))
        self.font = pygame.font.Font(None, 24)
        self.small = pygame.font.Font(None, 20)
        self.big = pygame.font.Font(None, 40)
        self.s = Session()
        self.delay = 400                  # ms between replayed moves
        self.next_step = 0
        self.buttons = []
        self._build_buttons()

    # ------------------------------------------------------------- buttons
    def _build_buttons(self):
        x, w, h, gap = BOARD_W + 16, PANEL_W - 32, 34, 8
        y = 130
        half = (w - gap) // 2
        self.buttons.append(Button((x, y, half, h), "New Game", self.new_game))
        self.buttons.append(Button((x + half + gap, y, half, h), "Restart", self.restart))
        y += h + gap + 24
        for name in SOLVER_NAMES:
            self.buttons.append(Button((x, y, w, h), f"Solve {name}", lambda n=name: self.solve(n)))
            y += h + gap
        self.buttons.append(Button((x, y, w, h), "Stop replay", self.stop))
        y += h + gap
        self.buttons.append(Button((x, y, half, h), "Slower", lambda: self.change_delay(+100)))
        self.buttons.append(Button((x + half + gap, y, half, h), "Faster", lambda: self.change_delay(-100)))
        self.text_y = y + h + 16

    def new_game(self):
        self.s.next_level()

    def restart(self):
        self.s.stop_replay(silent=True)
        self.s.restart()

    def stop(self):
        self.s.stop_replay()

    def change_delay(self, delta):
        self.delay = max(100, min(1000, self.delay + delta))

    def solve(self, name):
        self.s.message = f"Running {name}..."
        self.draw()
        pygame.display.flip()             # show "Running..." before the (blocking) search
        self.s.solve(name)
        self.next_step = pygame.time.get_ticks() + self.delay

    # --------------------------------------------------------------- input
    def on_key(self, key):
        if key in KEY_TO_DIR:
            self.s.move(KEY_TO_DIR[key])
        elif key == pygame.K_SPACE:
            self.s.toggle_active()
        elif key == pygame.K_r:
            self.restart()
        elif key == pygame.K_n:
            self.new_game()
        elif pygame.K_1 <= key <= pygame.K_9:
            idx = key - pygame.K_1
            if idx < len(self.s.paths):
                self.s.load(idx)

    def on_click(self, pos):
        for b in self.buttons:
            if b.rect.collidepoint(pos):
                b.callback()
                return

    # ---------------------------------------------------------------- loop
    def run(self):
        clock = pygame.time.Clock()
        running = True
        while running:
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    running = False
                elif e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_ESCAPE:
                        running = False
                    else:
                        self.on_key(e.key)
                elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                    self.on_click(e.pos)
            now = pygame.time.get_ticks()
            if self.s.replaying and now >= self.next_step:
                self.s.replay_step()
                self.next_step = now + self.delay
            self.draw()
            pygame.display.flip()
            clock.tick(60)
        pygame.quit()

    # ------------------------------------------------------------- drawing
    def draw(self):
        scr = self.screen
        scr.fill(C["bg"])
        self._draw_board()
        self._draw_panel()

    def _draw_board(self):
        scr, s, g = self.screen, self.s, self.s.game
        cell = int(min(80, (BOARD_W - 60) / g.cols, (WIN_H - 60) / g.rows))
        ox, oy = (BOARD_W - cell * g.cols) // 2, (WIN_H - cell * g.rows) // 2

        def box(r, c, inset=0):
            return pygame.Rect(ox + c * cell + inset, oy + r * cell + inset,
                               cell - 2 * inset, cell - 2 * inset)

        for r in range(g.rows):
            for c in range(g.cols):
                info = s.cell_info(r, c)
                if info.tile == "void":
                    continue
                rect = box(r, c, 1)
                if info.tile in ("floor", "goal"):
                    pygame.draw.rect(scr, C["floor"], rect)
                    pygame.draw.rect(scr, C["floor_edge"], rect, 1)
                    if info.tile == "goal":
                        pygame.draw.rect(scr, C["hole"], box(r, c, cell // 4))
                elif info.tile == "fragile":
                    pygame.draw.rect(scr, C["fragile"], rect)
                    pygame.draw.rect(scr, C["fragile_edge"], rect, 1)
                    x, y = rect.x, rect.y
                    pygame.draw.lines(scr, C["fragile_edge"], False,
                                      [(x + cell * .2, y + cell * .3), (x + cell * .5, y + cell * .55),
                                       (x + cell * .4, y + cell * .8)], 2)
                elif info.tile == "bridge_open":
                    pygame.draw.rect(scr, rgb(bridge_color(info.bridge)), rect)
                    pygame.draw.rect(scr, C["floor_edge"], rect, 1)
                else:  # bridge_closed
                    pygame.draw.rect(scr, rgb(bridge_color(info.bridge)), rect, 2)
                if info.switch is not None:
                    self._draw_switch(info.switch, box(r, c))

        for sw in g.switches.values():                 # where a split switch drops the cubes
            if sw.kind == "split":
                for (r, c) in sw.split_to:
                    pygame.draw.circle(scr, C["split"], box(r, c).center, int(cell * .18), 2)

        self._draw_block(box, cell)

    def _draw_switch(self, sw, rect):
        scr = self.screen
        color = rgb(switch_color(sw))
        cx, cy = rect.center
        cell = rect.width
        if sw.kind == "soft":
            pygame.draw.circle(scr, color, (cx, cy), int(cell * .24))
            pygame.draw.circle(scr, (34, 34, 34), (cx, cy), int(cell * .24), 2)
        elif sw.kind == "heavy":
            d = int(cell * .25)
            pygame.draw.line(scr, color, (cx - d, cy - d), (cx + d, cy + d), 5)
            pygame.draw.line(scr, color, (cx - d, cy + d), (cx + d, cy - d), 5)
        else:  # split
            font = pygame.font.Font(None, max(18, int(cell * .6)))
            text = font.render("( )", True, color)
            scr.blit(text, text.get_rect(center=(cx, cy)))

    def _draw_block(self, box, cell):
        scr, s = self.screen, self.s
        cells = s.state[0]
        o = orientation(cells)
        fill = rgb(s.block_color())
        edge = C["block_edge"]
        if o == SPLIT:
            for cube in cells:
                rect = box(cube[0], cube[1], cell // 5)
                is_active = cube == s.active and s.status == "playing"
                pygame.draw.rect(scr, fill, rect, border_radius=6)
                pygame.draw.rect(scr, C["active"] if is_active else edge, rect,
                                 4 if is_active else 2, border_radius=6)
            return
        a, b = cells
        rect = box(a[0], a[1], cell // 8).union(box(b[0], b[1], cell // 8))
        pygame.draw.rect(scr, fill, rect, border_radius=8)
        pygame.draw.rect(scr, edge, rect, 2, border_radius=8)
        if o == STAND:
            pygame.draw.rect(scr, C["block_top"], box(a[0], a[1], cell // 3), border_radius=4)

    def _draw_panel(self):
        scr, s = self.screen, self.s
        pygame.draw.rect(scr, C["panel"], (BOARD_W, 0, PANEL_W, WIN_H))
        x = BOARD_W + 16
        maxw = PANEL_W - 32
        scr.blit(self.big.render("BLOXORZ", True, C["text"]), (x, 16))
        for i, line in enumerate(wrap_text(s.level_name, self.small, maxw)[:2]):
            scr.blit(self.small.render(line, True, C["muted"]), (x, 62 + i * 20))
        scr.blit(self.small.render(f"Level {s.index + 1}/{len(s.paths)}  (keys 1-9)", True, C["muted"]),
                 (x, 104))
        scr.blit(self.small.render("Solvers", True, C["text"]), (x, 130 + 34 + 8 + 4))

        mouse = pygame.mouse.get_pos()
        for b in self.buttons:
            b.draw(scr, self.font, mouse)

        y = self.text_y
        scr.blit(self.font.render(f"Moves: {s.moves}   [{s.status.upper()}]", True, C["text"]), (x, y))
        y += 26
        scr.blit(self.small.render(f"Replay delay: {self.delay} ms", True, C["muted"]), (x, y))
        y += 24
        for text, color in ((s.message, C["text"]), (s.result_text, C["muted"]), (HELP_TEXT, C["muted"])):
            for line in wrap_text(text, self.small, maxw):
                if y < WIN_H - 18:
                    scr.blit(self.small.render(line, True, color), (x, y))
                y += 19
            y += 8


def main():
    App().run()


if __name__ == "__main__":
    main()
