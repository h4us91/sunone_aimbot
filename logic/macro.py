# macro.py
import xml.etree.ElementTree as ET
from logic.config_watcher import cfg
import win32api
import win32con
import time

class Macro:
    def __init__(self):
        self.active_macro = str(cfg.active_macro)
        self.macro_file = f"macros/{self.active_macro}"
        self.tree = ET.parse(self.macro_file)
        self.root = self.tree.getroot()
        
        node = self.root.find(".//DefaultMacro")
        self.hotkey = node.find("./Hotkey").text.strip() if node.find("./Hotkey") is not None else ""
        
        self.syntax_key_down = node.find("./KeyDown/Syntax").text if node.find("./KeyDown/Syntax") else ""
        self.syntax_key_up = node.find("./KeyUp/Syntax").text if node.find("./KeyUp/Syntax") else ""

    def run_key_down(self):
        self._run_syntax(self.syntax_key_down)

    def run_key_up(self):
        self._run_syntax(self.syntax_key_up)

    def _run_syntax(self, syntax):
        lines = [l.strip() for l in syntax.splitlines() if l.strip()]
        for line in lines:
            if line.startswith("LeftDown"):
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0)
            elif line.startswith("LeftUp"):
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0)
            elif line.startswith("MoveR"):
                _, x, y = line.split()
                win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, int(x), int(y))
            elif line.startswith("Delay"):
                _, ms, _ = line.split()
                time.sleep(int(ms)/1000)
