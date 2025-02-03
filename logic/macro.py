import sys
import xml.etree.ElementTree as ET
import time
import threading
import win32api
import win32con
from logic.config_watcher import cfg
from logic.thread_stop import stop_flag
from logic.driver.driver_logic import KernelDriver
from logic.buttons import Buttons
from pathlib import Path


def detect_base_dir():
    """Ermittelt das Basisverzeichnis des Skripts"""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent.parent

BASE_DIR = detect_base_dir()

class MacroThread(threading.Thread):
    def __init__(self):
        """Thread zur kontinuierlichen Überprüfung von Hotkeys."""
        super().__init__(daemon=True, name="MacroThread")
        self.manager = MacroManager()
        self.running = True

    def run(self):
        """Überprüft dauerhaft die `switch_key` und `fire_key`."""
        print("[INFO] Makro-Thread gestartet.")
        while self.running:
            self.manager.check_keys()
            time.sleep(0.1)  # Reduziert CPU-Last
        print("[INFO] Makro-Thread gestoppt.")

    def stop(self):
        """Beendet den Makro-Thread sauber."""
        self.running = False
     


class MacroLoader:
    """Lädt und speichert alle Makros aus dem Makro-Ordner."""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MacroLoader, cls).__new__(cls)
            cls._instance._macros = cls._instance._load_macros()
        return cls._instance

    def _load_macros(self):
        """Lädt alle Makros aus dem Ordner und speichert die Inhalte."""
        macro_folder = BASE_DIR / "macros"
        macros = {}
        if not macro_folder.exists():
            print(f"[ERROR] Makro-Ordner nicht gefunden: {macro_folder}")
            return macros
        
        for macro_file in macro_folder.glob("*.xml"):
            try:
                macros[macro_file.name] = self._parse_macro(macro_file)
            except Exception as e:
                print(f"[ERROR] Fehler beim Laden von {macro_file.name}: {e}")
        
        return macros
    
    def get_all_macros(self):
        """Gibt eine Liste aller verfügbaren Makro-Dateien zurück."""
        return list(self._macros.keys())

    def _parse_macro(self, file_path):
        """Parst eine Makro-XML-Datei und gibt ein Dictionary zurück."""
        tree = ET.parse(file_path)
        root = tree.getroot()
        node = root.find(".//DefaultMacro")
        if node is None:
            raise ValueError(f"❌ Kein <DefaultMacro> in {file_path} gefunden.")
        
        return {
            "name": file_path.name,
            "syntax_key_down": node.findtext("./KeyDown/Syntax", "").strip(),
            "syntax_key_up": node.findtext("./KeyUp/Syntax", "").strip()
        }

    def get_macro(self, macro_name):
        """Gibt die Daten eines Makros zurück."""
        return self._macros.get(macro_name, None)


class Macro:
    def __init__(self, macro_name):
        """Lädt ein Makro aus `MacroLoader`."""
        self.driver = KernelDriver()
        macro_data = MacroLoader().get_macro(macro_name)

        if not macro_data:
            raise ValueError(f"❌ Makro {macro_name} nicht gefunden.")

        self.syntax_key_down = macro_data["syntax_key_down"]
        self.syntax_key_up = macro_data["syntax_key_up"]

    def execute(self, syntax, stop_event=None):
        """Führt ein Makro-Pattern aus."""
        lines = [line.strip() for line in syntax.splitlines() if line.strip()]
        for line in lines:
            if stop_event and stop_event.is_set():
                break

            if line.startswith("LeftDown"):
                self.driver.click_mouse_down()
            elif line.startswith("LeftUp"):
                self.driver.click_mouse_up()
            elif line.startswith("MoveR"):
                self._execute_move(line)
            elif line.startswith("Delay"):
                self._execute_delay(line, stop_event)
            else:
                print(f"[WARN] Unbekannter Befehl: {line}")

    def _execute_move(self, line):
        """Bewegt die Maus relativ."""
        parts = line.split()
        if len(parts) != 3:
            print(f"[ERROR] Ungültiger MoveR-Befehl: {line}")
            return
        try:
            _, x, y = parts
            self.driver.move_mouse(int(x), int(y))
        except ValueError:
            print(f"[ERROR] Ungültige Koordinaten für MoveR: {x}, {y}")

    def _execute_delay(self, line, stop_event):
        parts = line.split()
        if len(parts) < 2:
            print(f"[ERROR] Ungültiger Delay-Befehl: {line}")
            return
        try:
            ms = int(parts[1])
            total_sleep = ms / 1000.0
            sleep_interval = min(0.1, total_sleep)
            slept = 0
            while slept < total_sleep:
                if stop_event and stop_event.is_set():
                    return
                time.sleep(sleep_interval)
                slept += sleep_interval
        except ValueError:
            print(f"[ERROR] Ungültige Zeit für Delay: {parts[1]}")



class MacroManager:
    def __init__(self):
        """Verwaltet Primary/Secondary Makros und Fire/Switch Key."""
        self.primary_macro = cfg.primary_macro
        self.secondary_macro = cfg.secondary_macro
        self.current_macro = self.primary_macro
        self.fire_key = cfg.fire_key
        self.switch_key = cfg.switch_key
        self.driver = KernelDriver()

    def check_keys(self):
        """Überprüft Switch-Key und Fire-Key."""
        if self._is_key_pressed(self.switch_key):
            self._switch_macro()
            time.sleep(0.3)

        if self._is_key_pressed(self.fire_key):
            self._execute_macro()


    def _is_key_pressed(self, key):
        key_code = Buttons.KEY_CODES.get(key.strip())
        return bool(win32api.GetAsyncKeyState(key_code) & 0x8000) if key_code else False

    def _switch_macro(self):
        """Wechselt zwischen Primary und Secondary Macro."""
        self.current_macro = self.secondary_macro if self.current_macro == self.primary_macro else self.primary_macro
        print(f"[INFO] Wechsel zu Makro: {self.current_macro}")

    def _execute_macro(self):
        if not self.current_macro:
            return
        macro_inst = Macro(self.current_macro)
        # Wiederhole die Ausführung, solange der Fire-Key gedrückt ist:
        while self._is_key_pressed(self.fire_key):
            macro_inst.execute(macro_inst.syntax_key_down)
            macro_inst.execute(macro_inst.syntax_key_up)


