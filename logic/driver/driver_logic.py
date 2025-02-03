import ctypes
import os
import base64
import tempfile
import subprocess
import sys
from logic.driver.driver_data import DRIVER_SYS_B64, MAPPER_EXE_B64

FILE_DEVICE_UNKNOWN = 0x22
METHOD_BUFFERED = 0
FILE_SPECIAL_ACCESS = 0x0

def CTL_CODE(DeviceType, Function, Method, Access):
    return (DeviceType << 16) | (Access << 14) | (Function << 2) | Method

IOCTL_MOUSE_MOVE = CTL_CODE(FILE_DEVICE_UNKNOWN, 0x696, METHOD_BUFFERED, FILE_SPECIAL_ACCESS)

class Request(ctypes.Structure):
    _fields_ = [
        ("x", ctypes.c_long),
        ("y", ctypes.c_long),
        ("button_flags", ctypes.c_ushort)
    ]

class KernelDriver:
    _instance = None  # Singleton-Instanz
    _driver_loaded = False  # Treiberstatus

    def __new__(cls):
        """ Singleton-Pattern: Stellt sicher, dass nur eine Instanz existiert """
        if cls._instance is None:
            cls._instance = super(KernelDriver, cls).__new__(cls)
            cls._instance.handle = None
            cls._instance.load_kernel_driver()
            cls._instance.init_kernel_driver()
        return cls._instance


    def load_kernel_driver(self):
        """ Lädt den Kernel-Treiber nur einmal """
        if self._driver_loaded:
            return

        temp_dir = tempfile.gettempdir()
        driver_path = os.path.join(temp_dir, "driver.sys")
        
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        

        mapper_path = os.path.join(base_dir,"mapper.exe")

        try:
            # Driver aus Base64 decodieren und in temp speichern
            with open(driver_path, "wb") as f:
                f.write(base64.b64decode(DRIVER_SYS_B64))

            result = subprocess.run([mapper_path, driver_path], capture_output=True, text=True)
            if result.returncode == 0:
                print("[INFO] Kernel Bypass: Treiber erfolgreich geladen.")
                self._driver_loaded = True
            else:
                print(f"[ERROR] Kernel Bypass: Mapper.exe Fehler: {result.stderr}")

        except Exception as e:
            print(f"[ERROR] Kernel Bypass: {e}")

        finally:
            if os.path.exists(driver_path):
                os.remove(driver_path)



    def init_kernel_driver(self):
        """ Initialisiert den Treiber und speichert das Handle """
        if self.handle is None:
            self.handle = ctypes.windll.kernel32.CreateFileW(
                "\\\\.\\UC", 0xC0000000, 0, None, 3, 0, None
            )
            if self.handle == -1:
                print("[ERROR] Kernel Bypass: Gerät konnte nicht geöffnet werden. "
                      "Überprüfe, ob der Treiber mit mapper.exe geladen wurde.")
                self.handle = None

    def move_mouse(self, x, y):
        """ Bewegt die Maus relativ zu ihrer aktuellen Position """
        if self.handle is None:
            print("[ERROR] Kernel Bypass: Kein Treiber-Handle vorhanden.")
            return False

        request = Request(int(x), int(y), 0)  # button_flags = 0 für Bewegung
        bytes_returned = ctypes.c_ulong(0)

        result = ctypes.windll.kernel32.DeviceIoControl(
            self.handle, IOCTL_MOUSE_MOVE, ctypes.byref(request), ctypes.sizeof(request),
            ctypes.byref(request), ctypes.sizeof(request), ctypes.byref(bytes_returned), None
        )
        if result == 0:
            print("[ERROR] Kernel Bypass: DeviceIoControl Bewegung fehlgeschlagen.")
            return False
        return True

    def click_mouse_down(self):
        """ Führt einen Linksklick (Taste gedrückt) aus """
        return self._send_mouse_action(1)

    def click_mouse_up(self):
        """ Führt einen Linksklick (Taste loslassen) aus """
        return self._send_mouse_action(2)

    def _send_mouse_action(self, button_flag):
        """ Sendet einen Klick-Befehl (Taste drücken oder loslassen) """
        if self.handle is None:
            print("[ERROR] Kernel Bypass: Kein Treiber-Handle vorhanden.")
            return False

        request = Request(0, 0, button_flag)  
        bytes_returned = ctypes.c_ulong(0)

        result = ctypes.windll.kernel32.DeviceIoControl(
            self.handle, IOCTL_MOUSE_MOVE, ctypes.byref(request), ctypes.sizeof(request),
            ctypes.byref(request), ctypes.sizeof(request), ctypes.byref(bytes_returned), None
        )
        if result == 0:
            print(f"[ERROR] Kernel Bypass: DeviceIoControl Klick ({button_flag}) fehlgeschlagen.")
            return False
        return True
