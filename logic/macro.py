# logic/macro.py

import xml.etree.ElementTree as ET
from logic.config_watcher import cfg
import win32api
import win32con
import time
import os

class Macro:
    def __init__(self, mouse_thread, macro_name=None):
        self.mouse_thread = mouse_thread  # Referenz zur MouseThread-Instanz
        if macro_name is None:
            macro_name = cfg.active_macro

        if not macro_name or macro_name.lower() == "none":
            raise ValueError("No active macro specified.")

        self.macro_file = os.path.join("macros", f"{macro_name}")
        if not os.path.exists(self.macro_file):
            raise FileNotFoundError(f"Macro file '{self.macro_file}' does not exist.")

        print(f"[DEBUG] Loading macro file: {self.macro_file}")  # Debug-Ausgabe

        self.tree = ET.parse(self.macro_file)
        self.root = self.tree.getroot()
        self.node = self.root.find(".//DefaultMacro")
        if self.node is None:
            raise ValueError("No <DefaultMacro> found in XML.")

        self.major = self._get_text("./Major")
        self.description = self._get_text("./Description")
        self.syntax_key_down = self._get_text("./KeyDown/Syntax")
        self.syntax_key_up = self._get_text("./KeyUp/Syntax")
        self.hotkey = self._get_text("./Hotkey")
        self.software = self._get_text("./Software")

    def _get_text(self, xpath):
        el = self.node.find(xpath)
        return el.text.strip() if el is not None and el.text else ""

    def run_key_down(self, stop_event=None):
        print("[DEBUG] Executing KeyDown syntax")
        self._run_syntax(self.syntax_key_down, stop_event)

    def run_key_up(self, stop_event=None):
        print("[DEBUG] Executing KeyUp syntax")
        self._run_syntax(self.syntax_key_up, stop_event)

    def _run_syntax(self, syntax, stop_event=None):
        lines = [l.strip() for l in syntax.splitlines() if l.strip()]
        for line in lines:
            if stop_event and stop_event.is_set():
                print("[DEBUG] Stop event set, exiting macro execution.")
                break
            print(f"[DEBUG] Running command: {line}")  # Debug-Ausgabe
            if line.startswith("LeftDown"):
                self.mouse_thread.click_mouse_down()
            elif line.startswith("LeftUp"):
                self.mouse_thread.click_mouse_up()
            elif line.startswith("MoveR"):
                parts = line.split()
                if len(parts) != 3:
                    print(f"[ERROR] Invalid MoveR command: {line}")
                    continue
                _, x, y = parts
                try:
                    x = int(x)
                    y = int(y)
                    self.mouse_thread.move_mouse_relative(x, y)
                except ValueError:
                    print(f"[ERROR] Invalid coordinates for MoveR: {x}, {y}")
            elif line.startswith("Delay"):
                parts = line.split()
                if len(parts) < 2:
                    print(f"[ERROR] Invalid Delay command: {line}")
                    continue
                try:
                    ms = int(parts[1])
                    print(f"[DEBUG] Sleeping for {ms} ms")  # Debug-Ausgabe vor der Pause
                    total_sleep = ms / 1000.0
                    sleep_interval = 0.01  # 10 ms
                    slept = 0
                    while slept < total_sleep:
                        if stop_event and stop_event.is_set():
                            print("[DEBUG] Stop event set during sleep, exiting macro execution.")
                            return
                        time.sleep(min(sleep_interval, total_sleep - slept))
                        slept += sleep_interval
                except ValueError:
                    print(f"[ERROR] Invalid time for Delay: {parts[1]}")
            else:
                print(f"[WARN] Unknown command: {line}")
