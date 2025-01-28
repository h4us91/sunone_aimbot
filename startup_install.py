import os
import sys
import subprocess
import shutil
from pathlib import Path
import configparser
from PyQt6.QtWidgets import QApplication, QMainWindow, QProgressBar, QPushButton, QVBoxLayout, QWidget, QLabel
from PyQt6.QtCore import Qt

class DependencyChecker:
    def __init__(self):
        self.base_path = Path(getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__))))
        self.libs_path = self.base_path / 'libs'
        
    def setup_structure(self):
        """Erstellt den libs Ordner falls nicht vorhanden"""
        os.makedirs(self.libs_path, exist_ok=True)

    def check_dependencies(self):
        """Prüft die Installation aller benötigten Packages"""
        required_packages = {
            # Basis Packages
            'numpy': 'numpy',
            'requests': 'requests',
            'packaging': 'packaging',
            'asyncio': 'asyncio',
            'keyboard': 'keyboard',
            
            # GUI und System
            'PyQt6': 'PyQt6',
            'win32': 'pywin32',
            'screeninfo': 'screeninfo',
            'mss': 'mss',
            'pyserial': 'pyserial',
            'bettercam': 'bettercam',
            
            # ML und Vision
            'cv2': 'opencv-python',
            'supervision': 'supervision',
            'ultralytics': 'ultralytics==8.3.40',  # Spezifische Version
            'tensorrt': 'tensorrt==10.3.0',  # TensorRT Version
            'cuda': 'cuda_python',
            'onnxruntime': 'onnxruntime-gpu'  # GPU Version direkt
        }
        
        missing_packages = []
        installed_packages = []
        
        for package, pip_name in required_packages.items():
            try:
                __import__(package)
                installed_packages.append(pip_name)
            except ImportError:
                missing_packages.append(pip_name)
        
        return missing_packages, installed_packages

    def install_missing_packages(self, packages, progress_callback=None):
        """Installiert fehlende Packages in den libs Ordner"""
        if not packages:
            return True

        total_packages = len(packages)
        
        for i, package in enumerate(packages):
            try:
                # Setze pip install command
                cmd = [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "--target",
                    str(self.libs_path),
                    package
                ]
                
                subprocess.check_call(cmd)
                
                if progress_callback:
                    progress = int(((i + 1) / total_packages) * 100)
                    progress_callback(progress, f"Installiere {package}...")
                
            except subprocess.CalledProcessError as e:
                print(f"Fehler bei Installation von {package}: {e}")
                return False
        
        # Füge libs Ordner zum Python Path hinzu
        if str(self.libs_path) not in sys.path:
            sys.path.insert(0, str(self.libs_path))
        
        return True

class LauncherWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.checker = DependencyChecker()
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle('AI Tool Launcher')
        self.setFixedSize(400, 200)
        
        # Zentrales Widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Status Label
        self.status_label = QLabel('Bereit zum Start')
        layout.addWidget(self.status_label)
        
        # Progress Bar
        self.progress = QProgressBar()
        layout.addWidget(self.progress)
        
        # Start Button
        self.start_button = QPushButton('Start AI Tool')
        self.start_button.clicked.connect(self.start_check)
        layout.addWidget(self.start_button)
        
    def update_progress(self, value, message):
        self.progress.setValue(value)
        self.status_label.setText(message)
        QApplication.processEvents()
        
    def start_check(self):
        self.start_button.setEnabled(False)
        self.checker.setup_structure()
        
        missing, installed = self.checker.check_dependencies()
        
        if missing:
            self.status_label.setText(f"Installation benötigter Packages...")
            success = self.checker.install_missing_packages(missing, self.update_progress)
            if not success:
                self.status_label.setText("Fehler bei der Installation!")
                return
        
        self.status_label.setText("Starte Anwendung...")
        self.progress.setValue(100)
        
        try:
            # Hier deine gui_start.py starten
            import gui_start
            self.close()
            gui_start.main()
        except Exception as e:
            self.status_label.setText(f"Fehler beim Start: {e}")
            self.start_button.setEnabled(True)

def main():
    app = QApplication(sys.argv)
    window = LauncherWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()