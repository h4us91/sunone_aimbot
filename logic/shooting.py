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
    

class Shooting(threading.Thread):
    def __init__(self):
        super(Shooting, self).__init__()
        self.queue = queue.Queue(maxsize=1)
        self.daemon = True
        self._running = True
        self.name = 'Shooting'
        self.button_pressed = False
        
        self.ghub = gHub
        self.kernel_bypass = cfg.kernel_bypass
        if cfg.mouse_rzr:
            dll_name = "rzctl.dll"
            script_directory = os.path.dirname(os.path.abspath(__file__))
            dll_path = os.path.join(script_directory, dll_name)
            self.rzr = RZCONTROL(dll_path)
            if not self.rzr.init():
                print("Failed to initialize rzctl")
        
        if self.kernel_bypass:
            from logic.driver.driver_logic import KernelDriver
            self.driver = KernelDriver()


    def run(self):
        while self._running:
            try:
                bScope, shooting_state = self.queue.get(timeout=0.1)  # Timeout hinzufügen
                self.shoot(bScope, shooting_state)
            except queue.Empty:
                continue  # Keine neuen Aufgaben, fortfahren
            
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
        elif self.kernel_bypass:
            self.driver.click_mouse_down()
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
        elif self.kernel_bypass:
            self.driver.click_mouse_up()
        else:
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        self.button_pressed = False

    def stop(self):
        self._running = False
        if cfg.mouse_rzr and hasattr(self, 'rzr'):
            self.rzr.cleanup()
        # Weitere Aufräumarbeiten hier
        self.join()
        
shooting = Shooting()