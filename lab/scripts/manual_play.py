from __future__ import annotations

import argparse
import tkinter as tk
from typing import Dict, Tuple

from lab.envs.grid.environment import GridWorldEnvironment
from lab.envs.grid.maps import get_map, register_builtin_maps

Action = Tuple[int, int]


class ManualPlayApp:
    CELL_SIZE = 40  # fixed square cell size (px)

    def __init__(self, master: tk.Tk, map_name: str) -> None:
        self.master = master

        register_builtin_maps()  # ensures builtin + `maps/*.map` are registered
        self.grid_map = get_map(map_name)
        self.env = GridWorldEnvironment(grid_map=self.grid_map, step_reward=0.0)

        self._done = False

        self.canvas = tk.Canvas(
            master,
            width=self.grid_map.width * self.CELL_SIZE,
            height=self.grid_map.height * self.CELL_SIZE,
            bg="white",
            highlightthickness=0,
        )
        # Keep the canvas as the main area; the "table" will be rendered inside the window bottom.
        self.canvas.pack(side=tk.TOP, fill="both", expand=True)

        # Bottom status "table".
        self.info_table = tk.Frame(master, bd=1, relief="sunken")
        self.info_table.pack(side=tk.BOTTOM, fill="x", padx=6, pady=6)

        header_style = {"anchor": "w", "font": ("TkDefaultFont", 10, "bold")}
        tk.Label(self.info_table, text="Field", **header_style).grid(row=0, column=0, sticky="w", padx=6)
        tk.Label(self.info_table, text="Value", **header_style).grid(row=0, column=1, sticky="w", padx=6)

        self._value_labels: Dict[str, tk.Label] = {}
        for row_idx, field in enumerate(
            ["Action", "done", "success", "blocked", "info"], start=1
        ):
            tk.Label(self.info_table, text=field, anchor="w").grid(
                row=row_idx, column=0, sticky="w", padx=6
            )
            val = tk.Label(self.info_table, text="", anchor="w", justify="left")
            val.grid(row=row_idx, column=1, sticky="w", padx=6)
            self._value_labels[field] = val

        # Initial hint.
        self._value_labels["info"].config(text="WASD: move, R: reset")

        self.action_map: Dict[str, Action] = {
            "w": (0, -1),
            "s": (0, 1),
            "a": (-1, 0),
            "d": (1, 0),
        }

        self.master.bind("<KeyPress>", self.handle_keypress)
        self.render()

    def _colors(self) -> Dict[str, str]:
        # Map elem.symbol -> fill color
        return {
            "#": "#222222",
            ".": "#FFFFFF",
            "S": "#2E86C1",
            "G": "#27AE60",
            "x": "#E74C3C",
        }

    def render(self) -> None:
        self.canvas.delete("all")

        colors = self._colors()
        cell = self.CELL_SIZE

        # Draw grid cells
        for y in range(self.grid_map.height):
            for x in range(self.grid_map.width):
                elem = self.grid_map.get_element_at((x, y))
                sym = getattr(elem, "symbol", "?")
                fill = colors.get(sym, "#DDDDDD")
                # Use black outline to keep grid readable.
                self.canvas.create_rectangle(
                    x * cell,
                    y * cell,
                    (x + 1) * cell,
                    (y + 1) * cell,
                    fill=fill,
                    outline="#000000",
                    width=1,
                )

        # Draw agent (FGHN) as a yellow circle at env.state
        sx, sy = self.env.state
        r = cell // 4  # radius
        cx = sx * cell + cell // 2
        cy = sy * cell + cell // 2
        self.canvas.create_oval(
            cx - r,
            cy - r,
            cx + r,
            cy + r,
            fill="#FFD400",
            outline="#B8860B",
            width=2,
        )

    def handle_keypress(self, event: tk.Event) -> None:
        key = (getattr(event, "char", "") or "").lower()

        if key == "r":
            self.env.reset()
            self._done = False
            self._value_labels["Action"].config(text="reset")
            self._value_labels["done"].config(text="False")
            self._value_labels["success"].config(text="")
            self._value_labels["blocked"].config(text="")
            self._value_labels["info"].config(text="Reset. WASD: move, R: reset")
            self.render()
            return

        if self._done:
            self._value_labels["info"].config(text="Episode ended (done=True). Press R to reset.")
            return

        if key not in self.action_map:
            return

        action = self.action_map[key]
        step_result = self.env.step(action)
        self._done = bool(step_result.done)

        success = step_result.info.get("success") if isinstance(step_result.info, dict) else None
        blocked = step_result.info.get("blocked") if isinstance(step_result.info, dict) else None

        self._value_labels["Action"].config(text=f"{key} {action}")
        self._value_labels["done"].config(text=str(step_result.done))
        self._value_labels["success"].config(text="" if success is None else str(success))
        self._value_labels["blocked"].config(text="" if blocked is None else str(blocked))
        self._value_labels["info"].config(text=str(step_result.info))
        self.render()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--map-name", type=str, default="level_01_trap_maze")
    args = ap.parse_args()

    root = tk.Tk()
    root.title(f"Manual Play (map={args.map_name})")
    app = ManualPlayApp(root, map_name=args.map_name)
    root.mainloop()


if __name__ == "__main__":
    main()

