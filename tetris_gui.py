"""Simple Tetris game implemented with Tkinter.

Run this module directly to launch the GUI:

    python tetris_gui.py
"""
from __future__ import annotations

import random
import tkinter as tk
from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple

# Board configuration
BOARD_WIDTH = 10
BOARD_HEIGHT = 20
CELL_SIZE = 30
TICK_MS = 600
SPEEDUP_PER_LINE = 15
MIN_TICK_MS = 120

# Type aliases
Point = Tuple[int, int]
ShapeRotation = Sequence[Point]
ShapeDefinition = Sequence[ShapeRotation]


@dataclass
class Tetromino:
    """Represents a tetromino with multiple rotation states."""

    name: str
    rotations: ShapeDefinition
    color: str

    def rotation(self, index: int) -> ShapeRotation:
        return self.rotations[index % len(self.rotations)]


SHAPES: Dict[str, Tetromino] = {
    "I": Tetromino(
        "I",
        (
            ((0, 1), (1, 1), (2, 1), (3, 1)),
            ((2, 0), (2, 1), (2, 2), (2, 3)),
        ),
        "#00c0f0",
    ),
    "J": Tetromino(
        "J",
        (
            ((0, 0), (0, 1), (1, 1), (2, 1)),
            ((1, 0), (2, 0), (1, 1), (1, 2)),
            ((0, 1), (1, 1), (2, 1), (2, 2)),
            ((1, 0), (1, 1), (0, 2), (1, 2)),
        ),
        "#0000f0",
    ),
    "L": Tetromino(
        "L",
        (
            ((2, 0), (0, 1), (1, 1), (2, 1)),
            ((1, 0), (1, 1), (1, 2), (2, 2)),
            ((0, 1), (1, 1), (2, 1), (0, 2)),
            ((0, 0), (1, 0), (1, 1), (1, 2)),
        ),
        "#f0a000",
    ),
    "O": Tetromino(
        "O",
        (
            ((1, 0), (2, 0), (1, 1), (2, 1)),
        ),
        "#f0f000",
    ),
    "S": Tetromino(
        "S",
        (
            ((1, 0), (2, 0), (0, 1), (1, 1)),
            ((1, 0), (1, 1), (2, 1), (2, 2)),
        ),
        "#00f000",
    ),
    "T": Tetromino(
        "T",
        (
            ((1, 0), (0, 1), (1, 1), (2, 1)),
            ((1, 0), (1, 1), (2, 1), (1, 2)),
            ((0, 1), (1, 1), (2, 1), (1, 2)),
            ((1, 0), (0, 1), (1, 1), (1, 2)),
        ),
        "#a000f0",
    ),
    "Z": Tetromino(
        "Z",
        (
            ((0, 0), (1, 0), (1, 1), (2, 1)),
            ((2, 0), (1, 1), (2, 1), (1, 2)),
        ),
        "#f00000",
    ),
}


class TetrisApp:
    """GUI controller for the Tetris game."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Tkinter Tetris")
        self.score = 0
        self.lines_cleared = 0
        self.tick_ms = TICK_MS

        self.board: List[List[str | None]] = [
            [None for _ in range(BOARD_WIDTH)] for _ in range(BOARD_HEIGHT)
        ]
        self.current_shape: Tetromino | None = None
        self.current_rotation = 0
        self.current_position = (3, 0)
        self.next_shape = self.random_shape()
        self.game_running = True

        self.canvas = tk.Canvas(
            root,
            width=BOARD_WIDTH * CELL_SIZE,
            height=BOARD_HEIGHT * CELL_SIZE,
            bg="#0f0f0f",
        )
        self.canvas.grid(row=0, column=0, rowspan=4, padx=10, pady=10)

        self.info_var = tk.StringVar()
        self.info_label = tk.Label(root, textvariable=self.info_var, justify=tk.LEFT)
        self.info_label.grid(row=0, column=1, sticky="nw", padx=(0, 10), pady=10)

        self.next_canvas = tk.Canvas(root, width=6 * CELL_SIZE, height=6 * CELL_SIZE)
        self.next_canvas.grid(row=1, column=1, sticky="n")

        self.status_var = tk.StringVar()
        self.status_label = tk.Label(
            root, textvariable=self.status_var, fg="#888", justify=tk.LEFT
        )
        self.status_label.grid(row=2, column=1, sticky="nw", padx=(0, 10))

        self.control_label = tk.Label(
            root,
            text="Controls:\n←/→ Move\n↑ Rotate\n↓ Soft drop\nSpace Hard drop\nP Pause",
            justify=tk.LEFT,
        )
        self.control_label.grid(row=3, column=1, sticky="nw", padx=(0, 10), pady=(10, 0))

        self.bind_events()
        self.spawn_new_piece()
        # Draw immediately so the initial piece/board is visible as soon as the
        # window appears. Without this, some environments (e.g. macOS) would
        # show a blank canvas until the user pressed a key.
        self.draw_board()
        self.schedule_tick()

    def bind_events(self) -> None:
        self.root.bind("<Left>", lambda _: self.try_move(-1, 0))
        self.root.bind("<Right>", lambda _: self.try_move(1, 0))
        self.root.bind("<Down>", lambda _: self.tick(manual=True))
        self.root.bind("<Up>", lambda _: self.try_rotate())
        self.root.bind("<space>", lambda _: self.hard_drop())
        self.root.bind("<p>", lambda _: self.toggle_pause())

    def toggle_pause(self) -> None:
        self.game_running = not self.game_running
        if self.game_running:
            self.status_var.set("")
            self.schedule_tick()
        else:
            self.status_var.set("Paused")

    def random_shape(self) -> Tetromino:
        return random.choice(list(SHAPES.values()))

    def spawn_new_piece(self) -> None:
        self.current_shape = self.next_shape
        self.next_shape = self.random_shape()
        self.current_rotation = 0
        self.current_position = (BOARD_WIDTH // 2 - 2, 0)
        if not self.is_valid_position(self.current_position, self.current_rotation):
            self.end_game()

    def try_move(self, dx: int, dy: int) -> None:
        if not self.game_running:
            return
        new_pos = (self.current_position[0] + dx, self.current_position[1] + dy)
        if self.is_valid_position(new_pos, self.current_rotation):
            self.current_position = new_pos
            self.draw_board()

    def try_rotate(self) -> None:
        if not self.game_running or self.current_shape is None:
            return
        new_rot = (self.current_rotation + 1) % len(self.current_shape.rotations)
        if self.is_valid_position(self.current_position, new_rot):
            self.current_rotation = new_rot
            self.draw_board()

    def hard_drop(self) -> None:
        if not self.game_running:
            return
        while self.is_valid_position((self.current_position[0], self.current_position[1] + 1), self.current_rotation):
            self.current_position = (
                self.current_position[0],
                self.current_position[1] + 1,
            )
        self.lock_piece()

    def tick(self, manual: bool = False) -> None:
        if not self.game_running or self.current_shape is None:
            return
        new_pos = (self.current_position[0], self.current_position[1] + 1)
        if self.is_valid_position(new_pos, self.current_rotation):
            self.current_position = new_pos
        else:
            self.lock_piece()
        # Always redraw after a tick so automatic gravity visibly moves the
        # piece even without user input.
        self.draw_board()
        if not manual:
            self.schedule_tick()

    def lock_piece(self) -> None:
        if self.current_shape is None:
            return
        for x, y in self.get_blocks(self.current_position, self.current_rotation):
            if y < 0:
                continue
            self.board[y][x] = self.current_shape.color
        lines = self.clear_lines()
        if lines:
            self.lines_cleared += lines
            self.score += (lines ** 2) * 100
            self.tick_ms = max(MIN_TICK_MS, TICK_MS - self.lines_cleared * SPEEDUP_PER_LINE)
        self.spawn_new_piece()
        self.draw_board()

    def clear_lines(self) -> int:
        new_board = [row for row in self.board if not all(cell is not None for cell in row)]
        cleared = BOARD_HEIGHT - len(new_board)
        while len(new_board) < BOARD_HEIGHT:
            new_board.insert(0, [None for _ in range(BOARD_WIDTH)])
        self.board = new_board
        return cleared

    def get_blocks(self, position: Point, rotation: int) -> List[Point]:
        if self.current_shape is None:
            return []
        px, py = position
        return [(px + x, py + y) for x, y in self.current_shape.rotation(rotation)]

    def is_valid_position(self, position: Point, rotation: int) -> bool:
        for x, y in self.get_blocks(position, rotation):
            if x < 0 or x >= BOARD_WIDTH or y >= BOARD_HEIGHT:
                return False
            if y >= 0 and self.board[y][x] is not None:
                return False
        return True

    def draw_board(self) -> None:
        self.canvas.delete("all")
        for y, row in enumerate(self.board):
            for x, cell in enumerate(row):
                if cell:
                    self.draw_cell(self.canvas, x, y, cell)
        if self.current_shape:
            for x, y in self.get_blocks(self.current_position, self.current_rotation):
                if y >= 0:
                    self.draw_cell(self.canvas, x, y, self.current_shape.color)
        self.draw_grid()
        self.draw_next_shape()
        self.update_ui()

    def draw_grid(self) -> None:
        for x in range(BOARD_WIDTH + 1):
            self.canvas.create_line(
                x * CELL_SIZE,
                0,
                x * CELL_SIZE,
                BOARD_HEIGHT * CELL_SIZE,
                fill="#222",
            )
        for y in range(BOARD_HEIGHT + 1):
            self.canvas.create_line(
                0,
                y * CELL_SIZE,
                BOARD_WIDTH * CELL_SIZE,
                y * CELL_SIZE,
                fill="#222",
            )

    def draw_cell(self, canvas: tk.Canvas, x: int, y: int, color: str) -> None:
        x0 = x * CELL_SIZE
        y0 = y * CELL_SIZE
        canvas.create_rectangle(
            x0 + 1,
            y0 + 1,
            x0 + CELL_SIZE - 1,
            y0 + CELL_SIZE - 1,
            fill=color,
            outline="#0f0f0f",
        )

    def draw_next_shape(self) -> None:
        self.next_canvas.delete("all")
        if not self.next_shape:
            return
        for x, y in self.next_shape.rotation(0):
            self.draw_cell(
                self.next_canvas,
                x + 1,
                y + 1,
                self.next_shape.color,
            )

    def update_ui(self) -> None:
        self.info_var.set(
            f"Score: {self.score}\nLines: {self.lines_cleared}\nSpeed: {self.tick_ms} ms"
        )

    def schedule_tick(self) -> None:
        if self.game_running:
            self.root.after(self.tick_ms, self.tick)

    def end_game(self) -> None:
        self.game_running = False
        self.status_var.set("Game over. Press R to restart.")
        self.root.bind("<r>", lambda _: self.restart())

    def restart(self) -> None:
        self.board = [[None for _ in range(BOARD_WIDTH)] for _ in range(BOARD_HEIGHT)]
        self.score = 0
        self.lines_cleared = 0
        self.tick_ms = TICK_MS
        self.status_var.set("")
        self.current_shape = None
        self.next_shape = self.random_shape()
        self.game_running = True
        self.root.unbind("<r>")
        self.spawn_new_piece()
        self.draw_board()
        self.schedule_tick()


def main() -> None:
    root = tk.Tk()
    TetrisApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
