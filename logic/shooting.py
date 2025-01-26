import queue
import threading
import os
import win32con, win32api
from logic.ghub import gHub
from logic.config_watcher import cfg


if cfg.mouse_rzr:
    from logic.rzctl import RZCONTROL, MOUSE_CLICK

if cfg.arduino_move or cfg.arduino_shoot:
    from logic.arduino import arduino

# Falls wir den Kernel Bypass verwenden:
if cfg.kernel_bypass:
    import ctypes
    from logic.driver.driver_logic import IOCTL_MOUSE_MOVE, Request
    def send_mouse_move(handle, x, y, button_flags=0):
        request = Request(int(x), int(y), button_flags)
        bytes_returned = ctypes.c_ulong(0)
        return ctypes.windll.kernel32.DeviceIoControl(
            handle,
            IOCTL_MOUSE_MOVE,
            ctypes.byref(request),
            ctypes.sizeof(request),
            ctypes.byref(request),
            ctypes.sizeof(request),
            ctypes.byref(bytes_returned),
            None
        )

class Shooting(threading.Thread):
    def __init__(self):
        super(Shooting, self).__init__()
        self.queue = queue.Queue(maxsize=1)
        self.daemon = True
        self.name = 'Shooting'
        self.button_pressed = False
        self.ghub = gHub
        self.start()

        if cfg.mouse_rzr:
            dll_name = "rzctl.dll"
            script_directory = os.path.dirname(os.path.abspath(__file__))
            dll_path = os.path.join(script_directory, dll_name)
            self.rzr = RZCONTROL(dll_path)
            if not self.rzr.init():
                print("Failed to initialize rzctl")
        
        # Kernel-Handle ggf. aus mouse.py holen (z.B. MouseThread().handle)


    def run(self):
        while True:
            bScope, shooting_state = self.queue.get()
            self.shoot(bScope, shooting_state)
            
    def shoot(self, bScope, shooting_state):
        # Bedingung: auto_shoot/triggerbot + bScope
        if cfg.auto_shoot and not cfg.triggerbot:
            self.handle_autoshoot(bScope, shooting_state)
        if cfg.auto_shoot and cfg.triggerbot and bScope or cfg.mouse_auto_aim and bScope:
            self.press_button()
        if cfg.auto_shoot and cfg.triggerbot and not bScope:
            self.release_button()

    def handle_autoshoot(self, bScope, shooting_state):
        if shooting_state and bScope or cfg.mouse_auto_aim and bScope:
            if not self.button_pressed:
                self.press_button()
        if (not shooting_state and self.button_pressed) or (not bScope and self.button_pressed):
            self.release_button()

    def press_button(self):
        if cfg.mouse_rzr:
            self.rzr.mouse_click(MOUSE_CLICK.LEFT_DOWN)
        elif cfg.mouse_ghub:
            self.ghub.mouse_down()
        elif cfg.arduino_shoot:
            arduino.press()
        elif cfg.kernel_bypass and self.kernel_handle:
            send_mouse_move(self.kernel_handle, 0, 0, 0x01)  # Button down
        else:
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        self.button_pressed = True

    def release_button(self):
        if cfg.mouse_rzr:
            self.rzr.mouse_click(MOUSE_CLICK.LEFT_UP)
        elif cfg.mouse_ghub:
            self.ghub.mouse_up()
        elif cfg.arduino_shoot:
            arduino.release()
        elif cfg.kernel_bypass and self.kernel_handle:
            send_mouse_move(self.kernel_handle, 0, 0, 0x02)  # Button up
        else:
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        self.button_pressed = False

shooting = Shooting()
