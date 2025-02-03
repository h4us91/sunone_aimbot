import sys, os, subprocess
from pkg_resources import get_distribution, DistributionNotFound
from PyQt6 import QtWidgets, QtCore

# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PACKAGE_PATH = BASE_DIR

TORCH_PACKAGES = ['torch', 'torchvision', 'torchaudio']
TORCH_INDEX_URL = 'https://download.pytorch.org/whl/cu124'

# TensorRT installation details (versioned)
TENSORRT_PACKAGES = [
    'tensorrt_cu12_libs==10.8.0.43',
    'tensorrt_cu12_bindings==10.8.0.43',
    'tensorrt==10.8.0.43'
]
TENSORRT_INDEX_URL = 'https://pypi.nvidia.com'

# All packages are now considered optional
REQUIRED_PACKAGES = [
    'ultralytics', 'bettercam', 'numpy', 'pywin32', 'screeninfo',
    'asyncio', 'onnxruntime', 'onnxruntime-gpu', 'pyserial', 'requests',
    'opencv-python', 'packaging', 'cuda_python', 'keyboard', 'mss',
    'supervision', 'dill'
]

def is_package_installed(package_name, log, version=None):
    """
    Check if a package is installed. If version is provided, it checks for an exact match.
    """
    try:
        dist = get_distribution(package_name)
        log(f"✅ {package_name} found (v{dist.version})")
        if version is None:
            return True
        return dist.version == version
    except DistributionNotFound:
        log(f"❌ {package_name} NOT found")
        return False

def get_missing_packages(log):
    missing = []
    for pkg in REQUIRED_PACKAGES:
        if not is_package_installed(pkg, log):
            missing.append(pkg)
    return missing

def install_torch(log):
    log("🔍 Installing Torch packages...")
    cmd = ["pip", "install", "--target", PACKAGE_PATH, "--no-warn-script-location",
           "--index-url", TORCH_INDEX_URL] + TORCH_PACKAGES
    try:
        subprocess.check_call(cmd)
        log("✅ Torch packages installed.")
    except subprocess.CalledProcessError as e:
        log(f"❌ Error installing Torch packages: {e}")
        sys.exit(1)

def install_tensorrt(log):
    log("🔍 Installing TensorRT packages...")
    cmd = ["pip", "install", "--target", PACKAGE_PATH, "--no-warn-script-location",
           "--index-url", TENSORRT_INDEX_URL] + TENSORRT_PACKAGES
    try:
        subprocess.check_call(cmd)
        log("✅ TensorRT packages installed.")
    except subprocess.CalledProcessError as e:
        log(f"❌ Error installing TensorRT packages: {e}")
        sys.exit(1)

def install_packages(pkgs, log):
    if not pkgs:
        return
    log(f"🔍 Installing: {' '.join(pkgs)}")
    cmd = ["pip", "install", "--target", PACKAGE_PATH, "--no-warn-script-location", "--no-cache-dir"] + pkgs
    try:
        subprocess.check_call(cmd)
        log("✅ Packages installed.")
    except subprocess.CalledProcessError as e:
        log(f"❌ Error installing packages: {e}")
        sys.exit(1)

class InstallerWorker(QtCore.QThread):
    log = QtCore.pyqtSignal(str)
    finished = QtCore.pyqtSignal()

    def run(self):
        self.log.emit("🔍 Starting installation...")
        # Install Torch packages if necessary
        for pkg in TORCH_PACKAGES:
            if not is_package_installed(pkg, lambda m: self.log.emit(m)):
                install_torch(lambda m: self.log.emit(m))
                break  # Install all at once, so break after calling install_torch

        # Check and install TensorRT packages if needed
        if not is_package_installed("tensorrt", lambda m: self.log.emit(m)):
            install_tensorrt(lambda m: self.log.emit(m))

        # Get missing optional packages
        missing_optional = get_missing_packages(lambda m: self.log.emit(m))
        if missing_optional:
            install_packages(missing_optional, lambda m: self.log.emit(m))

        # Final verification
        self.log.emit("🔄 Verifying installation...")
        missing_optional = get_missing_packages(lambda m: self.log.emit(m))
        if missing_optional:
            self.log.emit("❌ Some packages could not be installed: " + ", ".join(missing_optional))
        else:
            self.log.emit("✅ Installation complete.")
        self.finished.emit()

class InstallerWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Installer")
        self.resize(500, 400)
        self.text = QtWidgets.QTextEdit(self)
        self.text.setReadOnly(True)
        self.setCentralWidget(self.text)
        self.install_button = QtWidgets.QPushButton("Start Installation", self)
        self.install_button.clicked.connect(self.start_installation)
        self.install_button.setEnabled(False)
        toolbar = self.addToolBar("Actions")
        toolbar.addWidget(self.install_button)
        QtCore.QTimer.singleShot(0, self.check_initial_packages)

    def append_log(self, message):
        self.text.append(message)

    def check_initial_packages(self):
        self.append_log("🔍 Checking packages...")
        missing_optional = get_missing_packages(lambda msg: self.append_log(msg))
        if not missing_optional and is_package_installed("tensorrt", lambda m: self.append_log(m)):
            self.append_log("✅ All packages are present.")
            self.launch_main_app()
        else:
            self.append_log("❌ Missing packages detected:")
            if missing_optional:
                self.append_log("Optional: " + ", ".join(missing_optional))
            if not is_package_installed("tensorrt", lambda m: self.append_log(m)):
                self.append_log("TensorRT is missing.")
            self.install_button.setEnabled(True)

    def start_installation(self):
        self.install_button.setEnabled(False)
        self.worker = InstallerWorker()
        self.worker.log.connect(self.append_log)
        self.worker.finished.connect(self.post_installation)
        self.worker.start()

    def post_installation(self):
        self.append_log("🔄 Verifying installation post-installation...")
        missing_optional = get_missing_packages(lambda msg: self.append_log(msg))
        if missing_optional or not is_package_installed("tensorrt", lambda m: self.append_log(m)):
            self.append_log("❌ Some packages are still missing.")
            self.install_button.setEnabled(True)
        else:
            self.append_log("✅ All packages installed.")
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
