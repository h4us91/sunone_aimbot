import threading
from typing import List
import cv2
import win32api
import os
import time

from logic.config_watcher import cfg
from logic.buttons import Buttons
from logic.capture import capture
from logic.mouse import mouse
from logic.visual import visuals
from logic.shooting import shooting

class HotkeysWatcher(threading.Thread):
    def __init__(self):
        super(HotkeysWatcher, self).__init__()
        self.daemon = True
        self.name = 'HotkeysWatcher'
        self.app_pause = 0
        self.clss = self.active_classes()
        self._running = True
        # Starte den Thread NICHT automatisch,
        # damit er über run.py kontrolliert werden kann.
        # self.start()
        
    def run(self):
        cfg_reload_prev_state = 0
        while self._running:
            cfg_reload_prev_state = self.process_hotkeys(cfg_reload_prev_state)
            time.sleep(0.01)
            # Beende die Anwendung, wenn der Exit-Hotkey gedrückt wird
            if win32api.GetAsyncKeyState(Buttons.KEY_CODES.get(cfg.hotkey_exit)) & 0xFF:
                capture.stop()
                if cfg.show_window:
                    visuals.queue.put(None)
                os._exit(0)
                
    def process_hotkeys(self, cfg_reload_prev_state):
        self.app_pause = win32api.GetKeyState(Buttons.KEY_CODES[cfg.hotkey_pause])
        app_reload_cfg = win32api.GetKeyState(Buttons.KEY_CODES[cfg.hotkey_reload_config])
        if app_reload_cfg != cfg_reload_prev_state:
            if app_reload_cfg in (1, 0):
                cfg.Read(verbose=True)
                capture.restart()
                mouse.update_settings()
                self.clss = self.active_classes()
                if not cfg.show_window:
                    cv2.destroyAllWindows()
        return app_reload_cfg

    def active_classes(self) -> List[int]:
        clss = [0.0, 1.0]
        if cfg.hideout_targets:
            clss.extend([5.0, 6.0])
        if not cfg.disable_headshot or cfg.body_y_offset == "head":
            clss.append(7.0)
        if cfg.third_person:
            clss.append(10.0)
        self.clss = clss
        return clss

    def stop(self):
        self._running = False
        self.join()

hotkeys_watcher = HotkeysWatcher()
