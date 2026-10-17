"""
gui_tkinter.py - Bloxorz GUI built with tkinter (ships with Python).

Run:  python gui_tkinter.py        (or  python main.py tkinter)
"""
import tkinter as tk
from tkinter import ttk

from game import SPLIT, STAND, orientation
from gui_common import (COLORS, HELP_TEXT, KEY_TO_DIR, SOLVER_NAMES,
                        Session, bridge_color, switch_color)

CANVAS_W, CANVAS_H = 760, 580


class App:
    def __init__(self, root):
        self.root = root
        self.s = Session()
        self.after_id = None
        root.title("Bloxorz - tkinter")
        root.configure(bg=COLORS["bg"])

        self.canvas = tk.Canvas(root, width=CANVAS_W, height=CANVAS_H,
                                bg=COLORS["bg"], highlightthickness=0)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda e: self.draw())

        panel = tk.Frame(root, bg=COLORS["panel"], width=270)
        panel.pack(side="right", fill="y")
        panel.pack_propagate(False)
        self._build_panel(panel)

        root.bind("<Key>", self.on_key)
        self.canvas.focus_set()
        self.refresh()

    # ------------------------------------------------------------- widgets
    def _label(self, parent, text="", size=10, bold=False, color=None, wrap=240, **kw):
        font = ("Helvetica", size, "bold" if bold else "normal")
        return tk.Label(parent, text=text, font=font, bg=COLORS["panel"],
                        fg=color or COLORS["text"], wraplength=wrap, justify="left",
                        anchor="w", **kw)

    def _button(self, parent, text, command):
        return tk.Button(parent, text=text, command=lambda: (command(), self.canvas.focus_set()),
                         takefocus=0, relief="flat", bg="#3a4160", fg=COLORS["text"],
                         activebackground="#4d577f", activeforeground="white", pady=4)

    def _build_panel(self, p):
        pad = dict(padx=14, fill="x")
        self._label(p, "BLOXORZ", 18, True).pack(pady=(14, 2), **pad)
        self.lbl_level = self._label(p, "", 10, color=COLORS["muted"])
        self.lbl_level.pack(**pad)

        self.combo = ttk.Combobox(p, values=self.s.names, state="readonly", takefocus=0)
        self.combo.pack(pady=(8, 4), **pad)
        self.combo.bind("<<ComboboxSelected>>", self.on_select_level)

        row = tk.Frame(p, bg=COLORS["panel"])
        row.pack(pady=4, **pad)
        self._button(row, "New Game", self.new_game).pack(side="left", expand=True, fill="x", padx=(0, 3))
        self._button(row, "Restart", self.restart).pack(side="left", expand=True, fill="x", padx=(3, 0))

        self._label(p, "Solvers", 11, True).pack(pady=(12, 2), **pad)
        for name in SOLVER_NAMES:
            self._button(p, f"Solve {name}", lambda n=name: self.solve(n)).pack(pady=2, **pad)
        self._button(p, "Stop replay", self.stop).pack(pady=(6, 2), **pad)

        self.speed = tk.IntVar(value=400)
        tk.Scale(p, from_=100, to=1000, orient="horizontal", variable=self.speed,
                 label="Replay delay (ms)", bg=COLORS["panel"], fg=COLORS["text"],
                 highlightthickness=0, troughcolor="#3a4160", takefocus=0).pack(pady=4, **pad)

        self.lbl_moves = self._label(p, "", 11, True)
        self.lbl_moves.pack(pady=(8, 0), **pad)
        self.lbl_msg = self._label(p, "", 10)
        self.lbl_msg.pack(pady=2, **pad)
        self.lbl_result = self._label(p, "", 9, color=COLORS["muted"])
        self.lbl_result.pack(pady=2, **pad)
        self._label(p, HELP_TEXT, 9, color=COLORS["muted"]).pack(side="bottom", pady=10, **pad)

    # ------------------------------------------------------------- actions
    def _cancel_replay_timer(self):
        if self.after_id is not None:
            self.root.after_cancel(self.after_id)
            self.after_id = None

    def new_game(self):
        self._cancel_replay_timer()
        self.s.next_level()
        self.refresh()

    def restart(self):
        self._cancel_replay_timer()
        self.s.stop_replay(silent=True)
        self.s.restart()
        self.refresh()

    def on_select_level(self, _event=None):
        self._cancel_replay_timer()
        self.s.load(self.combo.current())
        self.canvas.focus_set()
        self.refresh()

    def solve(self, name):
        self._cancel_replay_timer()
        self.s.message = f"Running {name}..."
        self.refresh()
        self.root.update_idletasks()
        self.s.solve(name)
        self.refresh()
        self._schedule()

    def stop(self):
        self._cancel_replay_timer()
        self.s.stop_replay()
        self.refresh()

    def _schedule(self):
        if self.s.replaying:
            self.after_id = self.root.after(self.speed.get(), self._tick)

    def _tick(self):
        self.after_id = None
        self.s.replay_step()
        self.refresh()
        self._schedule()

    def on_key(self, event):
        key = event.keysym.lower()
        if key in KEY_TO_DIR:
            self.s.move(KEY_TO_DIR[key])
        elif key == "space":
            self.s.toggle_active()
        elif key == "r":
            self.restart()
            return
        elif key == "n":
            self.new_game()
            return
        else:
            return
        self.refresh()

    # ------------------------------------------------------------- drawing
    def refresh(self):
        s = self.s
        self.combo.current(s.index)
        self.lbl_level.config(text=s.level_name)
        self.lbl_moves.config(text=f"Moves: {s.moves}    [{s.status.upper()}]")
        self.lbl_msg.config(text=s.message)
        self.lbl_result.config(text=s.result_text)
        self.draw()

    def draw(self):
        c, s = self.canvas, self.s
        c.delete("all")
        g = s.game
        w = c.winfo_width() if c.winfo_width() > 1 else CANVAS_W
        h = c.winfo_height() if c.winfo_height() > 1 else CANVAS_H
        cell = int(min(80, (w - 60) / g.cols, (h - 60) / g.rows))
        ox, oy = (w - cell * g.cols) // 2, (h - cell * g.rows) // 2

        def box(r, col, inset=0):
            x, y = ox + col * cell, oy + r * cell
            return x + inset, y + inset, x + cell - inset, y + cell - inset

        # tiles
        for r in range(g.rows):
            for col in range(g.cols):
                info = s.cell_info(r, col)
                if info.tile == "void":
                    continue
                x0, y0, x1, y1 = box(r, col, 1)
                if info.tile in ("floor", "goal"):
                    c.create_rectangle(x0, y0, x1, y1, fill=COLORS["floor"], outline=COLORS["floor_edge"])
                    if info.tile == "goal":
                        hx0, hy0, hx1, hy1 = box(r, col, cell // 4)
                        c.create_rectangle(hx0, hy0, hx1, hy1, fill=COLORS["hole"], outline="")
                elif info.tile == "fragile":
                    c.create_rectangle(x0, y0, x1, y1, fill=COLORS["fragile"], outline=COLORS["fragile_edge"])
                    c.create_line(x0 + cell * .2, y0 + cell * .3, x0 + cell * .5, y0 + cell * .55,
                                  x0 + cell * .4, y0 + cell * .8, fill=COLORS["fragile_edge"], width=2)
                elif info.tile == "bridge_open":
                    c.create_rectangle(x0, y0, x1, y1, fill=bridge_color(info.bridge),
                                       outline=COLORS["floor_edge"])
                else:  # bridge_closed
                    c.create_rectangle(x0, y0, x1, y1, fill="", outline=bridge_color(info.bridge),
                                       width=2, dash=(4, 3))
                if info.switch is not None:
                    self._draw_switch(info.switch, box(r, col))

        # ghost markers where a split switch will drop the two cubes
        for sw in g.switches.values():
            if sw.kind == "split":
                for (r, col) in sw.split_to:
                    x0, y0, x1, y1 = box(r, col, int(cell * .32))
                    c.create_oval(x0, y0, x1, y1, outline=COLORS["split"], width=2, dash=(3, 3))

        self._draw_block(box)

    def _draw_switch(self, sw, bbox):
        c = self.canvas
        x0, y0, x1, y1 = bbox
        cx, cy, cell = (x0 + x1) / 2, (y0 + y1) / 2, x1 - x0
        color = switch_color(sw)
        if sw.kind == "soft":
            r = cell * 0.24
            c.create_oval(cx - r, cy - r, cx + r, cy + r, fill=color, outline="#222")
        elif sw.kind == "heavy":
            d = cell * 0.25
            c.create_line(cx - d, cy - d, cx + d, cy + d, fill=color, width=5)
            c.create_line(cx - d, cy + d, cx + d, cy - d, fill=color, width=5)
        else:  # split
            c.create_text(cx, cy, text="( )", fill=color,
                          font=("Helvetica", max(10, int(cell * 0.38)), "bold"))

    def _draw_block(self, box):
        c, s = self.canvas, self.s
        cells = s.state[0]
        o = orientation(cells)
        fill = s.block_color()
        cell = box(0, 0)[2] - box(0, 0)[0]
        if o == SPLIT:
            for cube in cells:
                x0, y0, x1, y1 = box(cube[0], cube[1], cell // 5)
                is_active = cube == s.active and s.status == "playing"
                c.create_rectangle(x0, y0, x1, y1, fill=fill,
                                   outline=COLORS["active"] if is_active else COLORS["block_edge"],
                                   width=4 if is_active else 2)
            return
        a, b = cells
        ax0, ay0, _, _ = box(a[0], a[1], cell // 8)
        _, _, bx1, by1 = box(b[0], b[1], cell // 8)
        c.create_rectangle(ax0, ay0, bx1, by1, fill=fill, outline=COLORS["block_edge"], width=2)
        if o == STAND:
            tx0, ty0, tx1, ty1 = box(a[0], a[1], cell // 3)
            c.create_rectangle(tx0, ty0, tx1, ty1, fill=COLORS["block_top"], outline="")


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
