import subprocess
import sys
import os
import ctypes
from pkg_resources import get_distribution, DistributionNotFound

# Stelle sicher, dass das portable Python genutzt wird
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PYTHON_EXE = os.path.join(BASE_DIR, "portable_python", "python.exe")

# Prüfe, ob die portable Python-Version existiert
if not os.path.exists(PYTHON_EXE):
    print(f"Fehler: Portable Python wurde nicht gefunden unter {PYTHON_EXE}")
    sys.exit(1)

# Liste der erforderlichen Pakete mit spezifischen Versionen
REQUIRED_PACKAGES = {
    'cuda-python': '12.8.0',
    'bettercam': '1.0.0'
}

# Torch-Pakete mit spezifischem Index-URL und Versionen
TORCH_PACKAGES = {
    'torch',
    'torchvision',
    'torchaudio'
}
TORCH_INDEX_URL = 'https://download.pytorch.org/whl/cu124'

# Installationspfad für Packages
PACKAGE_PATH = os.path.join(BASE_DIR, "python_runtime", "Lib", "site-packages")

def is_package_installed(package_name, version=None):
    """
    Prüft, ob ein Paket installiert ist. Wenn eine Version angegeben ist, wird sie überprüft.
    """
    try:
        dist = get_distribution(package_name)
        return True if version is None else dist.version == version
    except DistributionNotFound:
        return False

def get_missing_packages():
    """
    Sammelt alle Pakete, die fehlen oder eine falsche Version haben.
    """
    missing = []
    for package, version in REQUIRED_PACKAGES.items():
        if not is_package_installed(package, version):
            missing.append(f"{package}=={version}")
    
    for package in TORCH_PACKAGES:
        if not is_package_installed(package):  # Keine Versionsprüfung für Torch-Pakete
            missing.append(package)
    
    return missing


def install_pip():
    """
    Installiert `pip`, falls es nicht verfügbar ist.
    """
    try:
        subprocess.check_call([PYTHON_EXE, "-m", "ensurepip"])
        subprocess.check_call([PYTHON_EXE, "-m", "pip", "install", "--upgrade", "pip"])
    except subprocess.CalledProcessError:
        print("Fehler beim Installieren von `pip`.")
        sys.exit(1)

def install_packages(packages, index_url=None):
    """
    Installiert Pakete mit `pip` in den `PACKAGE_PATH`.
    """
    if not packages:
        return
    
    print(f"Installiere: {' '.join(packages)}")
    cmd = [PYTHON_EXE, "-m", "pip", "install", "--target", PACKAGE_PATH, "--no-warn-script-location"]
    
    if index_url:
        cmd += ["--index-url", index_url]
    
    cmd += packages
    
    try:
        subprocess.check_call(cmd)
    except subprocess.CalledProcessError as e:
        print(f"Fehler bei der Installation: {e}")
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
        print("Starte GUI...")
        import gui_start  # Direkt importieren und ausführen
        gui_start.main()  # Falls `main()` die Hauptfunktion ist
    except Exception as e:
        print(f"Fehler beim Starten der GUI: {e}")
        sys.exit(1)
        
def close_console():
        """Schließt die Konsole nach dem Setup, wenn das Programm im Fenster-Modus läuft."""
        if os.name == 'nt':  # Nur für Windows
            ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)

def main():
    """
    Hauptfunktion zur Überprüfung und Installation der Abhängigkeiten.
    """
    # Sicherstellen, dass `pip` vorhanden ist
    #install_pip()

    missing_packages = get_missing_packages()
    
    if missing_packages:
        print("Fehlende oder veraltete Pakete:")
        for pkg in missing_packages:
            print(f"- {pkg}")
        
        if prompt_install():
            # Trenne Torch-Pakete von den anderen Paketen
            torch_to_install = [pkg for pkg in missing_packages if pkg.split("==")[0] in TORCH_PACKAGES]
            other_packages = [pkg for pkg in missing_packages if pkg.split("==")[0] not in TORCH_PACKAGES]
            
            # Installiere reguläre Pakete
            install_packages(other_packages)
            
            # Installiere Torch-Pakete mit spezifischem Index-URL
            if torch_to_install:
                install_packages(torch_to_install, index_url=TORCH_INDEX_URL)
            
            print("Alle Abhängigkeiten installiert.")
            
            # Überprüfe erneut auf fehlende Pakete
            missing_after_install = get_missing_packages()
            if missing_after_install:
                print("Einige Pakete konnten nicht installiert werden:")
                for pkg in missing_after_install:
                    print(f"- {pkg}")
                sys.exit(1)

    else:
        print("Alle Pakete sind bereits installiert.")
    
    close_console()
 
    launch_gui()

if __name__ == "__main__":
    main()
