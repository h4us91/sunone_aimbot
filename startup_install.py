import subprocess
import sys
import os
import ctypes
from pkg_resources import get_distribution, DistributionNotFound


# Basisverzeichnis und Package-Ordner definieren
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PACKAGE_PATH = os.path.join(BASE_DIR)
PYTHON_PIP = os.path.join(BASE_DIR, "python_runtime", "python.exe")


REQUIRED_PACKAGES = {
    'pathlib': '1.0.1',
    'PyQt6': '6.8.0',
    'asyncio': '3.4.3',
    'bettercam': '1.0.0',
    'keyboard': '0.13.5',
    'mss': '10.0.0',
    'numpy': '2.2.2',
    'onnxruntime': '1.20.1',
    'onnxruntime-gpu': '1.20.1',
    'opencv-python': '4.11.0.86',
    'packaging': '24.2',
    'pyserial': '3.5',
    'pywin32': '308',
    'screeninfo': '0.8.1',
    'supervision': '0.25.1',
    'tensorrt': '10.8.0.43',
    'ultralytics': '8.3.68',
    'requests': '2.32.3'
}

TORCH_PACKAGES = {
    'torch',
    'torchvision',
    'torchaudio'
}
TORCH_INDEX_URL = 'https://download.pytorch.org/whl/cu124'


def is_package_installed(package_name, version=None):
    """
    Prüft, ob ein Paket installiert ist. Wenn eine Version angegeben ist, wird sie überprüft.
    """
    try:
        dist = get_distribution(package_name)
        print(f"✅ Paket gefunden: {package_name}")
        return True if version is None else dist.version == version
    except DistributionNotFound:
        print(f"❌ Paket NICHT gefunden: {package_name}")
        return False

def get_missing_packages():
    """
    Sammelt alle Pakete, die fehlen oder eine falsche Version haben.
    """
    missing = []

    # Überprüfe `REQUIRED_PACKAGES` mit fester Version
    for package, version in REQUIRED_PACKAGES.items():
        if not is_package_installed(package, version):
            missing.append(f"{package}=={version}")

    # Überprüfe `TORCH_PACKAGES` ohne feste Version
    for package in TORCH_PACKAGES:
        if not is_package_installed(package):
            missing.append(package)
    
    return missing

def install_packages(packages):
    """
    Installiert Pakete mit `pip` in den `PACKAGE_PATH`.
    """
    if not packages:
        return

    print(f"🔍 Installiere folgende Pakete: {' '.join(packages)}")
    cmd = [PYTHON_PIP, "-m", "pip", "install", "--target", PACKAGE_PATH, "--no-warn-script-location", "--no-cache-dir"]
    cmd += packages

    try:
        subprocess.check_call(cmd)
        print("✅ Paketinstallation erfolgreich.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Fehler bei der Installation: {e}")
        sys.exit(1)

def prompt_install():
    """
    Fragt den Nutzer, ob fehlende Pakete installiert werden sollen.
    """
    while True:
        choice = input("Fehlende Abhängigkeiten erkannt. Installieren? (Y/N): ").strip().lower()
        if choice == 'y':
            return True
        elif choice == 'n':
            print("Beende das Programm.")
            sys.exit(0)
        else:
            print("Bitte gib 'Y' für Ja oder 'N' für Nein ein.")

def launch_gui():
    """
    Startet die GUI-Anwendung mit `TEST.py`, falls es eingebettet ist.
    """
    try:
        print("🚀 Starte GUI...")
        import gui_start  # Direkt importieren und ausführen
        gui_start.main()  # Falls `main()` die Hauptfunktion ist
    except Exception as e:
        print(f"❌ Fehler beim Starten der GUI: {e}")
        sys.exit(1)

def close_console():
    """Schließt die Konsole nach dem Setup, wenn das Programm im Fenster-Modus läuft."""
    if os.name == 'nt':  # Nur für Windows
        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)

def main():
    """
    Hauptfunktion zur Überprüfung und Installation der Abhängigkeiten.
    """

    print("\n🔍 Starte Paketprüfung...")
    missing_packages = get_missing_packages()

    if missing_packages:
        if prompt_install():
            install_packages(missing_packages)
            print("🔄 Überprüfe erneut nach Installation...")
            missing_after_install = get_missing_packages()
            if missing_after_install:
                print("❌ Einige Pakete konnten nicht installiert werden.")
                sys.exit(1)
    print("✅ Alle Pakete sind bereits installiert.")
    launch_gui()
if __name__ == "__main__":
    main()
