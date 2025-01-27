import torch
import win32con, win32api
import torch.nn as nn
import time
import math
import os
import ctypes
import ctypes.wintypes
import supervision as sv
import subprocess
from logic.config_watcher import cfg
from logic.visual import visuals
from logic.shooting import shooting
from logic.buttons import Buttons
from logic.driver.driver_logic import IOCTL_MOUSE_MOVE, Request
import threading

import atexit
from logic.macro import Macro

class Mouse_net(nn.Module):
    def __init__(self, arch):
        super().__init__()
        self.layers = nn.Sequential(
            nn.Linear(10, 128, arch),
            nn.ReLU(),
            nn.Linear(128, 128, arch),
            nn.ReLU(),
            nn.Linear(128, 64, arch),
            nn.ReLU(),
            nn.Linear(64, 2, arch)
        )

    def forward(self, x):
        return self.layers(x)

class MouseThread:
    def __init__(self):
        self.macro = None
        self.last_macro_state = False 
        self.macro_thread = None  
        self.stop_macro_event = threading.Event()
        self.simulating = False 
        if cfg.active_macro and cfg.active_macro.lower() != "none":
            try:
                self.macro = Macro(self)  
                print(f"[INFO] Aktives Makro geladen: {cfg.active_macro}")
            except Exception as e:
                print(f"[ERROR] Macro konnte nicht geladen werden: {e}")
        self.last_macro_state = False  
        self.initialize_parameters()
        self.setup_hardware()
        self.setup_ai()
        self.driver_loaded = False  
        if self.macro:
            self.macro_monitor_thread = threading.Thread(target=self.macro_monitor_loop, daemon=True)
            self.macro_monitor_thread.start()
            print("[INFO] Makro-Monitoring-Thread gestartet")      
 

    def initialize_parameters(self):
        self.dpi = cfg.mouse_dpi
        self.mouse_sensitivity = cfg.mouse_sensitivity
        self.kernel_bypass = cfg.kernel_bypass
        self.fov_x = cfg.mouse_fov_width
        self.fov_y = cfg.mouse_fov_height
        self.disable_prediction = cfg.disable_prediction
        self.prediction_interval = cfg.prediction_interval
        self.bScope_multiplier = cfg.bScope_multiplier
        self.screen_width = cfg.detection_window_width
        self.screen_height = cfg.detection_window_height
        self.center_x = self.screen_width / 2
        self.center_y = self.screen_height / 2
        self.prev_x = 0
        self.prev_y = 0
        self.prev_time = None
        self.max_distance = math.sqrt(self.screen_width**2 + self.screen_height**2) / 2
        self.min_speed_multiplier = cfg.mouse_min_speed_multiplier
        self.max_speed_multiplier = cfg.mouse_max_speed_multiplier
        self.prev_distance = None
        self.speed_correction_factor = 0.1
        self.bScope = False
        self.arch = self.get_arch()
        self.section_size_x = self.screen_width / 100
        self.section_size_y = self.screen_height / 100
        
        if self.kernel_bypass:
            self.load_kernel_driver()
            self.init_kernel_driver()
    
    def load_kernel_driver(self):
        driver_path = os.path.join(os.path.dirname(__file__), 'driver', 'driver.sys')
        mapper_path = os.path.join(os.path.dirname(__file__), 'driver', 'mapper.exe')
        try:
            result = subprocess.run([mapper_path, driver_path], capture_output=True, text=True)
            if result.returncode == 0:
                print("[INFO] Kernel Bypass: Treiber erfolgreich geladen.")
                self.driver_loaded = True
            else:
                print(f"[ERROR] Kernel Bypass: Mapper.exe konnte den Treiber nicht laden. Fehler: {result.stderr}")
                self.driver_loaded = False
        except Exception as e:
            print(f"[ERROR] Kernel Bypass: Fehler beim Starten von mapper.exe - {e}")
            self.driver_loaded = False

    def init_kernel_driver(self):
        self.handle = ctypes.windll.kernel32.CreateFileW(
            "\\\\.\\UC", 0xC0000000, 0, None, 3, 0, None
        )
        if self.handle == -1:
            print("[ERROR] Kernel Bypass: Gerät konnte nicht geöffnet werden. Überprüfe, ob der Treiber mit mapper.exe geladen wurde.")
            self.handle = None    

    def get_arch(self):
        if cfg.AI_enable_AMD:
            return f'hip:{cfg.AI_device}'
        if 'cpu' in cfg.AI_device:
            return 'cpu'
        return f'cuda:{cfg.AI_device}'

    def setup_hardware(self):
        self.ghub = None
        self.mouse_rzr = None
        self.arduino_move = None
        if cfg.mouse_ghub:
            from logic.ghub import GhubMouse
            self.ghub = GhubMouse()

        if cfg.mouse_rzr:
            dll_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rzctl.dll")
            from logic.rzctl import RZCONTROL
            self.mouse_rzr = RZCONTROL(dll_path)
            if not self.mouse_rzr:
                print("Failed to initialize rzctl")
                
        if cfg.arduino_move or cfg.arduino_shoot:
            from logic.arduino import arduino
            self.arduino_move = arduino()


    def setup_ai(self):
        if cfg.AI_mouse_net:
            self.device = torch.device(self.arch)
            self.model = Mouse_net(arch=self.arch).to(self.device)
            try:
                self.model.load_state_dict(torch.load('mouse_net.pth', map_location=self.device))
            except Exception as e:
                print(e)
                print('Please train mouse_net model, or download latest trained mouse_net.pth model from repository.')
                exit()
            self.model.eval()   
            
###############################################################################
#                                MACRO SECTION                                #
###############################################################################

    def get_macro_hotkey_state(self):
        if self.macro and self.macro.hotkey:
            key_code = Buttons.KEY_CODES.get(self.macro.hotkey.strip())
            if key_code:
                # Überprüfe, ob der Hotkey gedrückt ist und ob keine Simulation läuft
                return win32api.GetAsyncKeyState(key_code) < 0 and not self.simulating
        return False


    def macro_monitor_loop(self):
        while True:
            self.handle_macro()
            time.sleep(0.05)  # 50 ms
               

    def handle_macro(self):
        if not self.macro:
            return

        new_state = self.get_macro_hotkey_state()
        if new_state and not self.last_macro_state:
            print("[INFO] Makro Hotkey gedrückt - Starte Makro-Thread")
            self.start_macro()
        elif not new_state and self.last_macro_state:
            print("[INFO] Makro Hotkey losgelassen - Stoppe Makro-Thread")
            self.stop_macro()

        self.last_macro_state = new_state
    
    def start_macro(self):
        if self.macro_thread and self.macro_thread.is_alive():
            print("[WARN] Makro-Thread läuft bereits")
            return
        self.stop_macro_event.clear()
        self.macro_thread = threading.Thread(target=self.execute_macro, daemon=True)
        self.macro_thread.start()
    
    def stop_macro(self):
        if self.macro_thread and self.macro_thread.is_alive():
            self.stop_macro_event.set()
            self.macro_thread.join()
            print("[INFO] Makro-Thread gestoppt")  
            
    def execute_macro(self):
        print("[DEBUG] Makro-Thread gestartet")
        while not self.stop_macro_event.is_set():
            try:
                print("[DEBUG] Executing run_key_down")
                self.simulating = True  # Setze das Simulations-Flag
                self.macro.run_key_down(self.stop_macro_event)  # Übergabe des stop_events
            except Exception as e:
                print(f"[ERROR] Fehler beim Ausführen des Makros: {e}")
            finally:
                self.simulating = False  # Entferne das Simulations-Flag
            # Optional: Kleine Pause zur CPU-Entlastung (falls nötig)
            #time.sleep(0.01)
        print("[DEBUG] Makro-Thread beendet")


    def click_mouse_down(self):
        if self.kernel_bypass and self.handle:
            # Kernel Bypass Methode für LeftDown
            request = Request(0, 0, 1)  # Beispiel: 1 für LeftDown
            bytes_returned = ctypes.c_ulong(0)
            result = ctypes.windll.kernel32.DeviceIoControl(
                self.handle, IOCTL_MOUSE_MOVE, ctypes.byref(request), ctypes.sizeof(request),
                None, 0, ctypes.byref(bytes_returned), None
            )
            if result == 0:
                print("[ERROR] Kernel Bypass: DeviceIoControl LeftDown fehlgeschlagen.")
        else:
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0)

    def click_mouse_up(self):
        if self.kernel_bypass and self.handle:
            # Kernel Bypass Methode für LeftUp
            request = Request(0, 0, 2)  # Beispiel: 2 für LeftUp
            bytes_returned = ctypes.c_ulong(0)
            result = ctypes.windll.kernel32.DeviceIoControl(
                self.handle, IOCTL_MOUSE_MOVE, ctypes.byref(request), ctypes.sizeof(request),
                None, 0, ctypes.byref(bytes_returned), None
            )
            if result == 0:
                print("[ERROR] Kernel Bypass: DeviceIoControl LeftUp fehlgeschlagen.")
        else:
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0)

    def move_mouse_relative(self, x, y):
        if self.kernel_bypass and self.handle:
            # Kernel Bypass Methode für Bewegung
            request = Request(x, y, 0)  # Beispiel: 0 für Bewegung
            bytes_returned = ctypes.c_ulong(0)
            result = ctypes.windll.kernel32.DeviceIoControl(
                self.handle, IOCTL_MOUSE_MOVE, ctypes.byref(request), ctypes.sizeof(request),
                None, 0, ctypes.byref(bytes_returned), None
            )
            if result == 0:
                print("[ERROR] Kernel Bypass: DeviceIoControl MoveR fehlgeschlagen.")
        else:
            win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, x, y, 0, 0)
   
###############################################################################
#                             END MACRO SECTION                                #
###############################################################################            
    
    def process_data(self, data):
        if isinstance(data, sv.Detections):
            target_x, target_y = data.xyxy.mean(axis=1)
            target_w, target_h = data.xyxy[:, 2] - data.xyxy[:, 0], data.xyxy[:, 3] - data.xyxy[:, 1]
            target_cls = data.class_id[0] if data.class_id.size > 0 else None
        else:
            target_x, target_y, target_w, target_h, target_cls = data

        self.visualize_target(target_x, target_y, target_cls)
        self.bScope = self.check_target_in_scope(target_x, target_y, target_w, target_h, self.bScope_multiplier) if cfg.auto_shoot or cfg.triggerbot else False
        self.bScope = cfg.force_click or self.bScope

        if not self.disable_prediction:
            current_time = time.time()
            if not isinstance(data, sv.Detections):
                target_x, target_y = self.predict_target_position(target_x, target_y, current_time)
            self.visualize_prediction(target_x, target_y, target_cls)

        move_x, move_y = self.calc_movement(target_x, target_y, target_cls)
        
        self.visualize_history(target_x, target_y)
        shooting.queue.put((self.bScope, self.get_shooting_key_state()))
        self.move_mouse(move_x, move_y)

    
    def predict_target_position(self, target_x, target_y, current_time):
        if self.prev_time is None:
            self.prev_time = current_time
            self.prev_x = target_x
            self.prev_y = target_y
            self.prev_velocity_x = 0
            self.prev_velocity_y = 0
            return target_x, target_y

        delta_time = current_time - self.prev_time
        velocity_x = (target_x - self.prev_x) / delta_time
        velocity_y = (target_y - self.prev_y) / delta_time
        acceleration_x = (velocity_x - self.prev_velocity_x) / delta_time
        acceleration_y = (velocity_y - self.prev_velocity_y) / delta_time

        prediction_interval = delta_time * self.prediction_interval
        current_distance = math.sqrt((target_x - self.prev_x)**2 + (target_y - self.prev_y)**2)
        proximity_factor = max(0.1, min(1, 1 / (current_distance + 1)))

        speed_correction = 1 + (abs(current_distance - (self.prev_distance or 0)) / self.max_distance) * self.speed_correction_factor if self.prev_distance is not None else .0001

        predicted_x = target_x + velocity_x * prediction_interval * proximity_factor * speed_correction + 0.5 * acceleration_x * (prediction_interval ** 2) * proximity_factor * speed_correction
        predicted_y = target_y + velocity_y * prediction_interval * proximity_factor * speed_correction + 0.5 * acceleration_y * (prediction_interval ** 2) * proximity_factor * speed_correction

        self.prev_x, self.prev_y = target_x, target_y
        self.prev_velocity_x, self.prev_velocity_y = velocity_x, velocity_y
        self.prev_time = current_time
        self.prev_distance = current_distance

        return predicted_x, predicted_y



    def calculate_speed_multiplier(self, target_x, target_y, distance):
        # Ensure target_x and target_y are valid numbers
        if math.isnan(target_x) or math.isnan(target_y):
            return 1  # Return default multiplier to prevent crashing

        normalized_distance = min(distance / self.max_distance, 1)
        base_speed = self.min_speed_multiplier + (self.max_speed_multiplier - self.min_speed_multiplier) * (1 - normalized_distance)

        try:
                if self.section_size_x == 0 or self.section_size_y == 0:
                    return 1  # Verhindere Division durch Null
                
                target_x_section = int((target_x - self.center_x + self.screen_width / 2) / max(self.section_size_x, 1e-6))
                target_y_section = int((target_y - self.center_y + self.screen_height / 2) / max(self.section_size_y, 1e-6))
        except (ValueError, OverflowError):
                return 1  # Verhindere Absturz bei ungültigen Werten


        distance_from_center = max(abs(50 - target_x_section), abs(50 - target_y_section))

        if distance_from_center == 0:
            return 1
        elif 5 <= distance_from_center <= 10:
            return self.max_speed_multiplier
        else:
            speed_reduction = min(distance_from_center - 10, 45) / 100.0
            speed_multiplier = base_speed * (1 - speed_reduction)

        if self.prev_distance is not None:
            speed_adjustment = 1 + (abs(distance - self.prev_distance) / self.max_distance) * self.speed_correction_factor
            return speed_multiplier * speed_adjustment
        
        return speed_multiplier

    def calc_movement(self, target_x, target_y, target_cls):
        if not cfg.AI_mouse_net:
            offset_x = target_x - self.center_x
            offset_y = target_y - self.center_y
            distance = math.sqrt(offset_x**2 + offset_y**2)
            speed_multiplier = self.calculate_speed_multiplier(target_x, target_y, distance)

            degrees_per_pixel_x = self.fov_x / self.screen_width
            degrees_per_pixel_y = self.fov_y / self.screen_height

            mouse_move_x = offset_x * degrees_per_pixel_x
            mouse_move_y = offset_y * degrees_per_pixel_y

            # Apply smoothing
            alpha = 0.85
            if not hasattr(self, 'last_move_x'):
                self.last_move_x, self.last_move_y = 0, 0
            
            move_x = alpha * mouse_move_x + (1 - alpha) * self.last_move_x
            move_y = alpha * mouse_move_y + (1 - alpha) * self.last_move_y
            
            self.last_move_x, self.last_move_y = move_x, move_y

            move_x = (move_x / 360) * (self.dpi * (1 / self.mouse_sensitivity)) * speed_multiplier
            move_y = (move_y / 360) * (self.dpi * (1 / self.mouse_sensitivity)) * speed_multiplier

            return move_x, move_y
        else:
            input_data = [
                self.screen_width, self.screen_height, self.center_x, self.center_y, 
                self.dpi, self.mouse_sensitivity, self.fov_x, self.fov_y, target_x, target_y
            ]
            
            input_tensor = torch.tensor(input_data, dtype=torch.float32).to(self.device)
            with torch.no_grad():
                move = self.model(input_tensor).cpu().numpy()
                
            self.visualize_prediction(move[0] + self.center_x, move[1] + self.center_y, target_cls)
            return move[0], move[1]
    
    def get_shooting_key_state(self):
        for key_name in cfg.hotkey_targeting_list:
            key_code = Buttons.KEY_CODES.get(key_name.strip())
            if key_code and (win32api.GetKeyState(key_code) if cfg.mouse_lock_target else win32api.GetAsyncKeyState(key_code)) < 0:
                return True
        return False
                
    def move_mouse(self, x, y):

        if x == 0 and y == 0:
            return
        
        shooting = self.get_shooting_key_state()
        mouse_aim = cfg.mouse_auto_aim
        triggerbot = cfg.triggerbot

        # Aimer nur aktiv, wenn rechte Maustaste gedrückt wird oder Auto-Aim aktiviert ist
        if (shooting and not mouse_aim and not triggerbot) or mouse_aim:
            x, y = int(x), int(y)

            if self.kernel_bypass and self.handle:
                request = Request(int(x), int(y), 0)
                bytes_returned = ctypes.c_ulong(0)
                result = ctypes.windll.kernel32.DeviceIoControl(
                    self.handle, IOCTL_MOUSE_MOVE, ctypes.byref(request), ctypes.sizeof(request),
                    ctypes.byref(request), ctypes.sizeof(request), ctypes.byref(bytes_returned), None
                )
                if result == 0:
                    print("[ERROR] Kernel Bypass: DeviceIoControl fehlgeschlagen.")
            else:
                if not self.ghub and not self.arduino_move and not self.mouse_rzr:
                    win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, x, y, 0, 0)
                elif self.ghub:
                    self.ghub().mouse_xy(x, y)
                elif self.mouse_rzr:
                    from logic.rzctl import RZCONTROL
                    self.rzr = RZCONTROL("rzctl.dll")
                    self.rzr.mouse_move(x, y, True)
                elif self.arduino_move:
                    from logic.arduino import arduino
                    arduino.move(x, y)

  

    def check_target_in_scope(self, target_x, target_y, target_w, target_h, reduction_factor):
        reduced_w, reduced_h = target_w * reduction_factor / 2, target_h * reduction_factor / 2
        x1, x2, y1, y2 = target_x - reduced_w, target_x + reduced_w, target_y - reduced_h, target_y + reduced_h
        bScope = self.center_x > x1 and self.center_x < x2 and self.center_y > y1 and self.center_y < y2
        
        if cfg.show_window and cfg.show_bScope_box:
            visuals.draw_bScope(x1, x2, y1, y2, bScope)
        
        return bScope
    


    
    def close_driver(self):
        self.stop_macro()
        if self.kernel_bypass and self.driver_loaded:
            ctypes.windll.kernel32.CloseHandle(self.handle)
            print("Kernel Bypass Handle geschlossen.")

        
        if self.kernel_bypass and self.driver_loaded:
            print("[INFO] Versuche, den Kernel-Treiber zu entladen...")
            mapper_path = os.path.join(os.path.dirname(__file__), 'data', 'mapper.exe')
            try:
                result = subprocess.run([mapper_path, '--free'], capture_output=True, text=True)
                if result.returncode == 0:
                    print("[INFO] Kernel-Treiber erfolgreich entladen.")
                else:
                    print(f"[ERROR] Kernel-Treiber konnte nicht entladen werden. Fehler: {result.stderr}")
            except Exception as e:
                print(f"[ERROR] Fehler beim Entladen des Kernel-Treibers - {e}")
    
    def update_settings(self):
        # Update all configuration parameters here
        self.dpi = cfg.mouse_dpi
        self.mouse_sensitivity = cfg.mouse_sensitivity
        self.fov_x = cfg.mouse_fov_width
        self.fov_y = cfg.mouse_fov_height
        self.disable_prediction = cfg.disable_prediction
        self.prediction_interval = cfg.prediction_interval
        self.bScope_multiplier = cfg.bScope_multiplier
        self.screen_width = cfg.detection_window_width
        self.screen_height = cfg.detection_window_height
        self.center_x = self.screen_width / 2
        self.center_y = self.screen_height / 2

    def visualize_target(self, target_x, target_y, target_cls):
        if cfg.AI_mouse_net == False and ((cfg.show_window and cfg.show_target_line) or (cfg.show_overlay and cfg.show_target_line)):
            visuals.draw_target_line(target_x, target_y, target_cls)

    def visualize_prediction(self, target_x, target_y, target_cls):
        if cfg.AI_mouse_net == False and ((cfg.show_window and cfg.show_target_prediction_line) or (cfg.show_overlay and cfg.show_target_prediction_line)):
            visuals.draw_predicted_position(target_x, target_y, target_cls)

    def visualize_history(self, target_x, target_y):
        if (cfg.show_window and cfg.show_history_points) or (cfg.show_overlay and cfg.show_history_points):
            visuals.draw_history_point_add_point(target_x, target_y)

mouse = MouseThread()
atexit.register(mouse.close_driver)