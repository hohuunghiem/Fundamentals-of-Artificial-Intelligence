# Bloxorz Solver (CSC14003 - Project 1)
## Requirements
    Python 3.13 (Won't work with 3.14 or higher)
    If have both 3.13 and 3.14: use "py -3.13" instead
## Run
    pip install -r requirements.txt     # only needed for the pygame GUI
    python main.py                      # asks: tkinter or pygame
    python main.py tkinter              # or: python main.py pygame

## Controls
Arrows / WASD roll the block - Space switches the cube when the block is split -
R restart - N next level - buttons: New Game, Restart, Solve BFS/DFS/IDS/UCS/A*, Stop.

## Files
- game.py        game rules (state, moves, fragile tiles, bridges, 3 switches, split block)
- solvers.py     BFS, DFS, IDS, UCS, A* + time / memory measurement
- gui_common.py  GUI logic shared by both frontends
- gui_tkinter.py, gui_pygame.py   the two frontends
- levels/*.json  stages (add your own: same format)
- test_*.py      unit tests: python -m unittest discover -v

## Terminal demo of the solvers
    python solvers.py levels/level2.json
