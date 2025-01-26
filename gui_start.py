import sys
import configparser
import subprocess
import os
from PyQt6.QtWidgets import QComboBox,QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QTabWidget, QFormLayout, QLineEdit, QCheckBox, QSpinBox, QDoubleSpinBox, QTextEdit, QHBoxLayout
from PyQt6.QtCore import Qt, QTimer, QProcess
from PyQt6.QtGui import QGuiApplication, QKeyEvent

CONFIG_PATH = "C:/Users/H4uS/Documents/Git/sunone_aimbot/config.ini"

class ConfigGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Aimbot Config GUI")
        self.setGeometry(100, 100, 800, 500)  # Größeres Fenster für Logs
        self.config = configparser.ConfigParser()
        self.load_config()
        self.mouse = None

        
        self.layout = QHBoxLayout()  # Hauptlayout (Horizontal für Sidebar)
        self.main_layout = QVBoxLayout()
        self.tabs = QTabWidget()
        self.create_tabs()
        self.create_macros_tab()

        # Buttons
        self.start_button = QPushButton("Start")
        self.start_button.clicked.connect(self.toggle_program)
        self.save_button = QPushButton("Save (F4)")
        self.save_button.clicked.connect(self.save_config)
        self.save_button.setVisible(True)

        # Log-Konsole (seitlich versteckt)
        self.log_console = QTextEdit()
        self.log_console.setReadOnly(True)
        self.log_console.setMaximumWidth(400)  # Begrenzte Breite
        self.log_console.setVisible(False)  # Standardmäßig versteckt
        self.log_console.setStyleSheet("background-color: black; color: white; font-family: monospace;")

        # Log-Toggle-Button
        self.toggle_log_button = QPushButton("Show Logs")
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
    def load_config(self):
        self.config.read(CONFIG_PATH)

    def create_tabs(self):
        for section in self.config.sections():
            if section == "Macro":
                continue
            tab = QWidget()
            form_layout = QFormLayout()

            for key, value in self.config[section].items():
                if value.lower() in ["true", "false"]:
                    checkbox = QCheckBox()
                    checkbox.setChecked(value.lower() == "true")
                    checkbox.stateChanged.connect(lambda state, sec=section, k=key: self.update_config(sec, k, "true" if state else "false"))
                    form_layout.addRow(QLabel(key), checkbox)

                elif value.replace('.', '', 1).isdigit():
                    if '.' in value:
                        spinbox = QDoubleSpinBox()
                        spinbox.setRange(0.0, 10000.0)
                        spinbox.setSingleStep(0.1)
                        spinbox.setValue(float(value)) 
                    else:
                        spinbox = QSpinBox()
                        spinbox.setRange(0, 10000)
                        spinbox.setValue(int(value))  
                    spinbox.valueChanged.connect(lambda val, sec=section, k=key: self.update_config(sec, k, str(val)))
                    form_layout.addRow(QLabel(key), spinbox)

                else:
                    line_edit = QLineEdit(value)
                    line_edit.textChanged.connect(lambda val, sec=section, k=key: self.update_config(sec, k, val))
                    form_layout.addRow(QLabel(key), line_edit)

            tab.setLayout(form_layout)
            self.tabs.addTab(tab, section)

    def create_macros_tab(self):
        tab = QWidget()
        layout = QFormLayout()

        macros = [f for f in os.listdir("macros") if f.endswith(".xml")]
        macro_box = QComboBox()
        macro_box.addItems(macros)

        current_macro = self.config["Macro"].get("active_macro", "None")
        active_checkbox = QCheckBox("Active")
        
        if current_macro != "None" and current_macro in macros:
            macro_box.setCurrentText(current_macro)
            active_checkbox.setChecked(True)

        def on_macro_changed():
            if active_checkbox.isChecked():
                self.update_config("Macro", "active_macro", macro_box.currentText())
            else:
                self.update_config("Macro", "active_macro", "None")
        
        macro_box.currentIndexChanged.connect(on_macro_changed)
        active_checkbox.stateChanged.connect(on_macro_changed)

        hotkey_edit = QLineEdit("LeftMouseButton")
        layout.addRow("Macro:", macro_box)
        layout.addRow("Active:", active_checkbox)
        layout.addRow("Hotkey:", hotkey_edit)

        tab.setLayout(layout)
        self.tabs.addTab(tab, "Macros")


     
    
        
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
            self.process = QProcess()
            self.process.setWorkingDirectory(os.path.dirname(CONFIG_PATH))
            self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
            
            self.process.readyReadStandardOutput.connect(self.handle_stdout)
            self.process.readyReadStandardError.connect(self.handle_stderr)

            self.process.start("python", ["-u", "run.py"])
            self.start_button.setText("Stop")
        else:
            self.process.terminate()
            self.process = None
            self.log_console.clear()
            self.start_button.setText("Start")

    def handle_stdout(self):
        text = self.process.readAllStandardOutput().data().decode()
        self.log_console.append(text)

    def handle_stderr(self):
        text = self.process.readAllStandardError().data().decode()
        self.log_console.append(f"<span style='color:red;'>{text}</span>")


    
    def toggle_log_console(self):
        self.log_console.setVisible(not self.log_console.isVisible())
        self.toggle_log_button.setText("Hide Logs" if self.log_console.isVisible() else "Show Logs")

    def read_process_output(self):
        if self.process:
            output = self.process.stdout.readline()
            error = self.process.stderr.readline()

            if output:
                self.log_console.append(output.strip())
            if error:
                self.log_console.append(f"<span style='color:red;'>{error.strip()}</span>")

            QTimer.singleShot(100, self.read_process_output) 

 

    def keyPressEvent(self, event: QKeyEvent):
        """Fängt Hotkeys ab und führt die entsprechenden Aktionen aus."""
        
        if event.key() == Qt.Key_F2: 
            self.close() 
        
        elif event.key() == Qt.Key_F3:  
            print("Aimbot paused!")  

        elif event.key() == Qt.Key_F4: 
            self.save_config()  
            print("Config reloaded!")  

        
if __name__ == "__main__":
    app = QApplication(sys.argv)
    gui = ConfigGUI()
    gui.show()
    sys.exit(app.exec())