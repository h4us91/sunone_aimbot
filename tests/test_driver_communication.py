import ctypes
import ctypes.wintypes
from time import sleep

# Konstanten definieren
FILE_DEVICE_UNKNOWN = 0x22
METHOD_BUFFERED = 0
FILE_SPECIAL_ACCESS = 0x0

# CTL_CODE Makro nachbilden
def CTL_CODE(DeviceType, Function, Method, Access):
    return (DeviceType << 16) | (Access << 14) | (Function << 2) | Method

IOCTL_MOUSE_MOVE = CTL_CODE(FILE_DEVICE_UNKNOWN, 0x696, METHOD_BUFFERED, FILE_SPECIAL_ACCESS)

class Request(ctypes.Structure):
    _fields_ = [
        ("x", ctypes.c_long),
        ("y", ctypes.c_long),
        ("button_flags", ctypes.c_ushort)
    ]

def send_mouse_move(handle, x, y, button_flags):
    request = Request(x, y, button_flags)
    bytes_returned = ctypes.c_ulong(0)
    
    # Buffer für Input und Output
    buffer = Request(x, y, button_flags)
    
    result = ctypes.windll.kernel32.DeviceIoControl(
        handle,
        IOCTL_MOUSE_MOVE,
        ctypes.byref(buffer),  # lpInBuffer
        ctypes.sizeof(buffer), # nInBufferSize
        ctypes.byref(buffer),  # lpOutBuffer - wichtig: gleicher Buffer wie Input
        ctypes.sizeof(buffer), # nOutBufferSize
        ctypes.byref(bytes_returned),
        None
    )
    
    if result == 0:
        error = ctypes.get_last_error()
        print(f"Fehler bei DeviceIoControl: {error}")
    else:
        print("Mausbewegung erfolgreich")

def main():
    # Gerät öffnen
    handle = ctypes.windll.kernel32.CreateFileW(
        "\\\\.\\UC",                          # Gerätename
        0xC0000000,                           # GENERIC_READ | GENERIC_WRITE
        0,                                    # Exclusive access
        None,                                 # No security
        3,                                    # OPEN_EXISTING
        0,                                    # Normal attributes
        None                                  # No template
    )
    
    if handle == -1:
        print(f"Fehler beim Öffnen des Geräts: {ctypes.get_last_error()}")
        return
    
    print("Gerät erfolgreich geöffnet")
    
    try:
        # Maus bewegen
        send_mouse_move(handle, 100, 100, 0)
        sleep(0.1)  # Kurze Pause zwischen den Aktionen
        
        # Linksklick
        send_mouse_move(handle, 0, 0, 0x01)  # Button down
        sleep(0.1)
        send_mouse_move(handle, 0, 0, 0x02)  # Button up
        
    finally:
        # Handle schließen
        ctypes.windll.kernel32.CloseHandle(handle)
        print("Handle geschlossen")

if __name__ == "__main__":
    main()
    # Warten wie im C++-Code
    while True:
        sleep(1)