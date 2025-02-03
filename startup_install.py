import sys, os, subprocess
from pkg_resources import get_distribution, DistributionNotFound
from PyQt6 import QtWidgets, QtCore

# Konfiguration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PACKAGE_PATH = BASE_DIR
TORCH_PACKAGES = ['torch', 'torchvision', 'torchaudio']
TORCH_INDEX_URL = 'https://download.pytorch.org/whl/cu124'
REQUIRED_PACKAGES = {}
OPTIONAL_PACKAGES = [
    'ultralytics', 'bettercam', 'numpy', 'pywin32', 'screeninfo',
    'asyncio', 'onnxruntime', 'onnxruntime-gpu', 'pyserial', 'requests',
    'opencv-python', 'packaging', 'cuda_python', 'keyboard', 'mss',
    'supervision', 'dill', 'wheel', 'tensorrt'
]

def is_package_installed(package_name, log, version=None):
    try:
        dist = get_distribution(package_name)
        log(f"✅ {package_name} gefunden (v{dist.version})")
        return (version is None or dist.version == version)
    except DistributionNotFound:
        log(f"❌ {package_name} NICHT gefunden")
        return False

def get_missing_packages(log):
    missing_with, missing_without = [], []
    for pkg, ver in REQUIRED_PACKAGES.items():
        if not is_package_installed(pkg, log, ver):
            missing_with.append(f"{pkg}=={ver}")
    for pkg in OPTIONAL_PACKAGES:
        if not is_package_installed(pkg, log):
            missing_without.append(pkg)
    return missing_with, missing_without

def install_torch(log):
    log("🔍 Installiere Torch-Pakete...")
    cmd = ["pip", "install", "--target", PACKAGE_PATH, "--no-warn-script-location",
           "--index-url", TORCH_INDEX_URL] + TORCH_PACKAGES
    try:
        subprocess.check_call(cmd)
        log("✅ Torch-Pakete installiert.")
    except subprocess.CalledProcessError as e:
        log(f"❌ Fehler bei Torch-Installation: {e}")
        sys.exit(1)

def install_packages(pkgs, log):
    if not pkgs:
        return
    log(f"🔍 Installiere: {' '.join(pkgs)}")
    cmd = ["pip", "install", "--target", PACKAGE_PATH, "--no-warn-script-location", "--no-cache-dir", "--upgrade"] + pkgs
    try:
        subprocess.check_call(cmd)
        log("✅ Pakete installiert.")
    except subprocess.CalledProcessError as e:
        log(f"❌ Fehler bei Installation: {e}")
        sys.exit(1)

class InstallerWorker(QtCore.QThread):
    log = QtCore.pyqtSignal(str)
    finished = QtCore.pyqtSignal()

    def run(self):
        # Installation durchführen ohne zusätzlichen Nachfrage-Dialog
        self.log.emit("🔍 Starte Installation...")
        # Installiere Torch falls nötig
        if not all(is_package_installed(pkg, lambda m: self.log.emit(m)) for pkg in TORCH_PACKAGES):
            install_torch(lambda m: self.log.emit(m))
        # Installiere Pakete mit Versionen
        missing_with, missing_without = get_missing_packages(lambda m: self.log.emit(m))
        if missing_with:
            install_packages(missing_with, lambda m: self.log.emit(m))
        if missing_without:
            install_packages(missing_without, lambda m: self.log.emit(m))
        # Nochmals prüfen
        self.log.emit("🔄 Überprüfe Installation...")
        mw, mwo = get_missing_packages(lambda m: self.log.emit(m))
        if mw or mwo:
            self.log.emit("❌ Einige Pakete konnten nicht installiert werden.")
        else:
            self.log.emit("✅ Installation abgeschlossen.")
        self.finished.emit()

class InstallerWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Installer")
        self.resize(500, 400)
        self.text = QtWidgets.QTextEdit(self)
        self.text.setReadOnly(True)
        self.setCentralWidget(self.text)

        # Button für Installation (wird nur aktiviert, wenn Pakete fehlen)
        self.install_button = QtWidgets.QPushButton("Installation starten", self)
        self.install_button.clicked.connect(self.start_installation)
        self.install_button.setEnabled(False)
        toolbar = self.addToolBar("Aktionen")
        toolbar.addWidget(self.install_button)

        # Initialer Check (nachdem GUI angezeigt wurde)
        QtCore.QTimer.singleShot(0, self.check_initial_packages)

    def append_log(self, message):
        self.text.append(message)

    def check_initial_packages(self):
        self.append_log("🔍 Überprüfe Pakete...")
        # Temporäre Logfunktion, die direkt ins Textfeld schreibt.
        temp_log = lambda msg: self.append_log(msg)
        missing_with, missing_without = get_missing_packages(temp_log)
        if not missing_with and not missing_without:
            self.append_log("✅ Alle Pakete sind vorhanden.")
            self.launch_main_app()
        else:
            self.append_log("❌ Fehlende Pakete erkannt:")
            if missing_with:
                self.append_log("Erforderlich: " + ", ".join(missing_with))
            if missing_without:
                self.append_log("Optional: " + ", ".join(missing_without))
            self.install_button.setEnabled(True)

    def start_installation(self):
        self.install_button.setEnabled(False)
        self.worker = InstallerWorker()
        self.worker.log.connect(self.append_log)
        self.worker.finished.connect(self.post_installation)
        self.worker.start()

    def post_installation(self):
        self.append_log("🔄 Prüfe nach Installation...")
        temp_log = lambda msg: self.append_log(msg)
        missing_with, missing_without = get_missing_packages(temp_log)
        if missing_with or missing_without:
            self.append_log("❌ Einige Pakete fehlen weiterhin.")
            self.install_button.setEnabled(True)
        else:
            self.append_log("✅ Alle Pakete installiert.")
            self.launch_main_app()

    def launch_main_app(self):
        from gui_start import ConfigGUI
        main_gui = ConfigGUI()
        main_gui.show()
        self.close()
        

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    win = InstallerWindow()
    win.show()
    sys.exit(app.exec())
