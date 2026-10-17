"""
main.py - launcher.

    python main.py              -> asks which GUI to open
    python main.py tkinter      -> tkinter version
    python main.py pygame       -> pygame version
"""
import sys


def ask():
    while True:
        try:
            raw = input("Choose GUI  [1] tkinter   [2] pygame : ").strip().lower()
        except EOFError:
            sys.exit(1)
        raw = {"1": "tkinter", "2": "pygame"}.get(raw, raw)
        if raw in ("tkinter", "pygame"):
            return raw


def main():
    choice = sys.argv[1].lower() if len(sys.argv) > 1 else ask()
    if choice not in ("tkinter", "pygame"):
        sys.exit("usage: python main.py [tkinter|pygame]")
    try:
        if choice == "tkinter":
            import gui_tkinter as gui
        else:
            import gui_pygame as gui
    except ImportError as err:
        hint = "pip install pygame" if choice == "pygame" else "install python3-tk (Linux) / reinstall Python with tcl/tk"
        sys.exit(f"Cannot start the {choice} GUI: {err}\nTry: {hint}")
    gui.main()


if __name__ == "__main__":
    main()
