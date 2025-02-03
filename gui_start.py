import sys
import configparser
import os
import threading
import keyboard  
import random
import string
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QTabWidget, QFormLayout, QLineEdit, QCheckBox, QSpinBox, QDoubleSpinBox, QTextEdit, QHBoxLayout, QGroupBox, QComboBox
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import QTimer, QProcess, pyqtSignal, QObject
from pathlib import Path
from logic.macro import MacroLoader
from logic.buttons import Buttons
import time

def setup_lib_path():
    global CONFIG_PATH, BASE_DIR
    if getattr(sys, 'frozen', False):  
        BASE_DIR = Path(sys.executable).parent  
    else:
        BASE_DIR = Path(__file__).parent 

    CONFIG_PATH = str(BASE_DIR / 'config.ini')
setup_lib_path()
MACRO_PATH = BASE_DIR / "macros"
if not MACRO_PATH.exists():
    print(f"❌ Warnung: Macro-Ordner nicht gefunden: {MACRO_PATH}")
    
venv_python = sys.executable  

if getattr(sys, 'frozen', False):
    portable_python_path = Path(BASE_DIR / "python_runtime" / "python.exe")

    if portable_python_path.exists():
        venv_python = str(portable_python_path)

class Communicate(QObject):
    toggle_visibility = pyqtSignal()

class ConfigGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("P3PEyXWb77jUCnPd")
        self.setGeometry(100, 100, 800, 500)  # Größeres Fenster für Logs
        self.config = configparser.ConfigParser()
        self.load_config()
        self.mouse = None
        self.run_module = None
        icon_path = os.path.join(os.path.dirname(__file__), "assets", "inosuke.ico")  
        self.setWindowIcon(QIcon(icon_path))

        # Kommunikationsobjekt für Signal-Slot-Mechanismus
        self.comm = Communicate()
        self.comm.toggle_visibility.connect(self.toggle_visibility)

        self.layout = QHBoxLayout()  # Hauptlayout (Horizontal für Sidebar)
        self.main_layout = QVBoxLayout()
        self.tabs = QTabWidget()
        self.create_tabs()

        # Buttons
        self.start_button = QPushButton("Start")
        self.start_button.clicked.connect(self.toggle_program)
        self.save_button = QPushButton("Save (F4)")
        self.save_button.clicked.connect(self.save_config)
        self.save_button.setVisible(True)

        # Log-Konsole (seitlich versteckt)
        self.log_console = QTextEdit()
        self.log_console.setReadOnly(True)
        self.log_console.setMaximumWidth(400) 
        self.log_console.setVisible(True) 
        self.log_console.setStyleSheet("background-color: black; color: white; font-family: monospace;")

        # Log-Toggle-Button
        self.toggle_log_button = QPushButton("Hide Logs")
        self.toggle_log_button.clicked.connect(self.toggle_log_console)

        # Layout für die Buttons
        self.button_layout = QVBoxLayout()
        self.button_layout.addWidget(self.toggle_log_button)
        self.button_layout.addWidget(self.save_button)
        self.button_layout.addWidget(self.start_button)

        # Zusammenfügen des Layouts
        self.main_layout.addWidget(self.tabs)
        self.main_layout.addLayout(self.button_layout)
        
        self.layout.addLayout(self.main_layout)
        self.layout.addWidget(self.log_console)  
        self.setLayout(self.layout)

        self.process = None  

        # Starte den globalen Hotkey-Listener in einem separaten Thread
        self.start_hotkey_listener()

        # QTimer für die Generierung zufälliger Fenstertitel
        self.title_timer = QTimer()
        self.title_timer.timeout.connect(self.generate_random_title)
        self.title_timer.setInterval(50)  # Intervall in Millisekunden (z.B. 1000 ms = 1 Sekunde)

    def load_config(self):
        self.config.read(CONFIG_PATH)

    def create_tabs(self):
        # Definiere gruppierte Tabs
        grouped_tabs = {
            "Aim | Shooting | Macro": ["Aim", "Shooting", "Macro"],
            "Mouse | Arduino": ["Mouse", "Arduino"],
            "Capture Window": ["Detection window", "Capture Methods"],
            "Overlay | Debug Window": ["overlay", "Debug window"],
        }
        
        grouped_sections = set()
            
        for tab_name, sections in grouped_tabs.items():
            tab = QWidget()
            tab_layout = QVBoxLayout()

            for section in sections:
                if section not in self.config.sections():
                    continue  # Überspringe, wenn die Sektion nicht existiert

                
                if section == "Macro":
                    macro_group = QGroupBox(section)
                    macro_layout = QFormLayout()
                    macro_loader = MacroLoader()
                    macros = macro_loader.get_all_macros()

                    # Primary Macro Dropdown
                    primary_macro_box = QComboBox()
                    primary_macro_box.addItems(macros)
                    primary_macro_box.setCurrentText(
                        self.config["Macro"].get("primary_macro", "None")
                    )
                    primary_macro_box.currentTextChanged.connect(
                        lambda val: self.config.set("Macro", "primary_macro", val)
                    )

                    # Secondary Macro Dropdown
                    secondary_macro_box = QComboBox()
                    secondary_macro_box.addItems(macros)
                    secondary_macro_box.setCurrentText(
                        self.config["Macro"].get("secondary_macro", "None")
                    )
                    secondary_macro_box.currentTextChanged.connect(
                        lambda val: self.config.set("Macro", "secondary_macro", val)
                    )

                    # Erstelle Dropdowns für Switch Key und Fire Key
                    available_keys = Buttons.KEY_CODES.keys()
                    
                    switch_key_combo = QComboBox()
                    switch_key_combo.addItems(available_keys)
                    switch_key_combo.setCurrentText(
                        self.config["Macro"].get("switch_key", "Tab")
                    )
                    switch_key_combo.currentTextChanged.connect(
                        lambda val: self.config.set("Macro", "switch_key", val)
                    )

                    fire_key_combo = QComboBox()
                    fire_key_combo.addItems(available_keys)
                    fire_key_combo.setCurrentText(
                        self.config["Macro"].get("fire_key", "MiddleMouseButton")
                    )
                    fire_key_combo.currentTextChanged.connect(
                        lambda val: self.config.set("Macro", "fire_key", val)
                    )

                    macro_layout.addRow("Primary Macro:", primary_macro_box)
                    macro_layout.addRow("Secondary Macro:", secondary_macro_box)
                    macro_layout.addRow("Switch Key:", switch_key_combo)
                    macro_layout.addRow("Fire Key:", fire_key_combo)

                    macro_group.setLayout(macro_layout)
                    tab_layout.addWidget(macro_group)
                    
                else:
                    # Allgemeine Sektionen
                    group_box = QGroupBox(section)
                    form_layout = QFormLayout()

                    for key, value in self.config[section].items():
                        widget = self.create_widget(section, key, value)
                        if widget:
                            form_layout.addRow(QLabel(key.replace('_', ' ').capitalize()), widget)

                    group_box.setLayout(form_layout)
                    tab_layout.addWidget(group_box)

                grouped_sections.add(section)    

            tab.setLayout(tab_layout)
            self.tabs.addTab(tab, tab_name)
            
        for section in self.config.sections():
            if section in grouped_sections:
                continue  # Bereits gruppiert

            if section == "Macro":
                continue  # Macro ist bereits gruppiert

            tab = QWidget()
            form_layout = QFormLayout()

            for key, value in self.config[section].items():
                widget = self.create_widget(section, key, value)
                if widget:
                    form_layout.addRow(QLabel(key.replace('_', ' ').capitalize()), widget)

            tab_layout.addStretch()
            tab.setLayout(form_layout)
            self.tabs.addTab(tab, section)

                    
    def create_widget(self, section, key, value):
        """Hilfsfunktion zur Erstellung von Widgets basierend auf dem Werttyp."""
        if value.lower() in ["true", "false"]:
            checkbox = QCheckBox()
            checkbox.setChecked(value.lower() == "true")
            checkbox.stateChanged.connect(
                lambda state, sec=section, k=key: self.update_config(sec, k, "true" if state else "false")
            )
            return checkbox

        elif self.is_number(value):
            if '.' in value:
                spinbox = QDoubleSpinBox()
                spinbox.setRange(0.0, 10000.0)
                spinbox.setSingleStep(0.1)
                spinbox.setValue(float(value)) 
            else:
                spinbox = QSpinBox()
                spinbox.setRange(0, 10000)
                spinbox.setValue(int(value))  
            spinbox.valueChanged.connect(
                lambda val, sec=section, k=key: self.update_config(sec, k, str(val))
            )
            return spinbox

        else:
            line_edit = QLineEdit(value)
            line_edit.textChanged.connect(
                lambda val, sec=section, k=key: self.update_config(sec, k, val)
            )
            return line_edit

    def is_number(self, s):
        """Prüft, ob der gegebene String eine Zahl ist."""
        try:
            float(s)
            return True
        except ValueError:
            return False

    def start_hotkey_listener(self):
        """Startet einen Listener für den globalen Hotkey (F12), um die GUI umzuschalten."""
        def listen_hotkey():
            # Definiere den Hotkey, z.B. F12
            keyboard.add_hotkey('f12', self.comm.toggle_visibility.emit)
            keyboard.wait()  # Blockiert diesen Thread und wartet auf Tastendrücke

        # Starte den Listener in einem separaten Thread
        listener_thread = threading.Thread(target=listen_hotkey, daemon=True)
        listener_thread.start()

    def toggle_visibility(self):
        """Schaltet die Sichtbarkeit der GUI um."""
        if self.isVisible():
            self.hide()
        else:
            self.show()

    def update_config(self, section, key, value):
        self.config.set(section, key, value)

    def save_config(self):
        with open(CONFIG_PATH, "w") as configfile:
            self.config.write(configfile)
        self.log_console.append("Config saved!")
        
    def toggle_program(self):
        if self.process is None:
            current_macro = self.config["Macro"].get("active_macro", "None")
            if current_macro != "None":
                self.log_console.append(f"WARNING: Active macro '{current_macro}'")
            self.save_config()
            self.log_console.append("🚀 Starte...")
            
            # Always reload the run module
            import importlib
            if self.run_module:
                importlib.reload(self.run_module)
            else:
                import run
                self.run_module = run
                
            self.process = threading.Thread(target=self.run_module.main, daemon=True, name="GUI")
            self.process.start()
            self.fetch_logs()
            self.start_button.setText("Stop")
        else:
            if self.run_module:
                self.run_module.stop()
                self.log_console.append("🛑 Stop requested!")
                if self.process.is_alive():
                    self.process.join(timeout=2.0)
            self.process = None
            self.start_button.setText("Start")




                    
    def fetch_logs(self):
        if self.run_module is None:
            return
        while not self.run_module.log_queue.empty():
            line = self.run_module.log_queue.get()
            self.log_console.append(line.rstrip())
        if self.process and self.process.is_alive():
            QTimer.singleShot(100, self.fetch_logs)



    def handle_stdout(self):
        text = self.process.readAllStandardOutput().data().decode()
        self.log_console.append(text)

    def handle_stderr(self):
        text = self.process.readAllStandardError().data().decode()
        self.log_console.append(f"<span style='color:red;'>{text}</span>")

    def toggle_log_console(self):
        self.log_console.setVisible(not self.log_console.isVisible())
        self.toggle_log_button.setText("Hide Logs" if self.log_console.isVisible() else "Show Logs")

    def generate_random_title(self):
        """Generiert einen zufälligen Titel und aktualisiert das Fenster."""
        random_title = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
        self.setWindowTitle(random_title)

    def showEvent(self, event):
        """Überlagert das showEvent, um den Timer zu starten, wenn das Fenster sichtbar wird."""
        super().showEvent(event)
        self.title_timer.start()

    def hideEvent(self, event):
        """Überlagert das hideEvent, um den Timer zu stoppen, wenn das Fenster versteckt wird."""
        super().hideEvent(event)
        self.title_timer.stop()

def main():
    app = QApplication(sys.argv)
    gui = ConfigGUI()
    gui.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
