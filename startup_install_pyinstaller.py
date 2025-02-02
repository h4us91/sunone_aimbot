import subprocess
import sys
import os
import ctypes
from pkg_resources import get_distribution, DistributionNotFound
if os.name == "nt":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, errors="replace")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, errors="replace")
# Basisverzeichnis und Package-Ordner definieren
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PACKAGE_PATH = BASE_DIR
PYTHON_PIP = os.path.join(BASE_DIR, "python_runtime", "python.exe")


TORCH_PACKAGES = ['torch', 'torchvision', 'torchaudio']
TORCH_INDEX_URL = 'https://download.pytorch.org/whl/cu124'


REQUIRED_PACKAGES = {}


OPTIONAL_PACKAGES = [
    'ultralytics',
    'bettercam',
    'numpy',
    'pywin32',
    'screeninfo',
    'asyncio',
    'onnxruntime',
    'onnxruntime-gpu',
    'pyserial',
    'requests',
    'opencv-python',
    'packaging',
    'cuda_python',
    'keyboard',
    'mss',
    'supervision',
    'PyQt6'
]

def is_package_installed(package_name, version=None):
    """
    Prüft, ob ein Paket installiert ist. Falls Version angegeben ist, wird sie überprüft.
    """
    try:
        dist = get_distribution(package_name)
        print(f"✅ Paket gefunden: {package_name} (Installiert: {dist.version}, Erwartet: {version})")

        if version is None or dist.version == version:
            return True
        else:
            print(f"⚠️ Paket `{package_name}` hat falsche Version: {dist.version} (Erwartet: {version})")
            return False

    except DistributionNotFound:
        print(f"❌ Paket NICHT gefunden: {package_name}")
        return False

def install_torch():
    """
    Installiert Torch-Pakete mit der speziellen URL.
    """
    print("🔍 Installiere Torch-Pakete...")
    cmd = [
        PYTHON_PIP, "-m", "pip", "install", "--target", PACKAGE_PATH,
        "--no-warn-script-location",
        "--index-url", TORCH_INDEX_URL
    ] + TORCH_PACKAGES

    try:
        subprocess.check_call(cmd)
        print("✅ Torch-Pakete erfolgreich installiert.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Fehler bei der Torch-Installation: {e}")
        sys.exit(1)

def get_missing_packages():
    """
    Sammelt alle Pakete, die fehlen oder eine falsche Version haben.
    """
    missing_with_version = []
    missing_without_version = []

    # Überprüfe Pakete mit fester Version
    for package, version in REQUIRED_PACKAGES.items():
        if not is_package_installed(package, version):
            missing_with_version.append(f"{package}=={version}")

    # Überprüfe Pakete ohne feste Version
    for package in OPTIONAL_PACKAGES:
        if not is_package_installed(package):
            missing_without_version.append(package)

    return missing_with_version, missing_without_version

def install_packages(packages):
    """
    Installiert Pakete mit `pip` in den `PACKAGE_PATH`.
    """
    if not packages:
        return

    print(f"🔍 Installiere folgende Pakete: {' '.join(packages)}")
    cmd = [
        PYTHON_PIP, "-m", "pip", "install",
        "--target", PACKAGE_PATH, "--no-warn-script-location"
    ] + packages

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
    Startet die GUI-Anwendung mit `gui_start.py`, falls es eingebettet ist.
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

    # Überprüfe, ob Torch fehlt
    torch_missing = not all(is_package_installed(pkg) for pkg in TORCH_PACKAGES)

    # Überprüfe fehlende optionale Pakete
    missing_with_version, missing_without_version = get_missing_packages()

    if torch_missing or missing_with_version or missing_without_version:
        if prompt_install():  # 🔥 Erst hier wird der Benutzer gefragt
            if torch_missing:
                install_torch()
            
            if missing_with_version:
                install_packages(missing_with_version)

            if missing_without_version:
                install_packages(missing_without_version)

            print("🔄 Überprüfe erneut nach Installation...")
            missing_after_with, missing_after_without = get_missing_packages()
            if missing_after_with or missing_after_without:
                print("❌ Einige Pakete konnten nicht installiert werden.")
                sys.exit(1)

    print("✅ Alle Pakete sind bereits installiert.")
    launch_gui()

if __name__ == "__main__":
    main()
