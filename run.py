import sys
import os
import queue
import threading
import torch
from pathlib import Path
from ultralytics import YOLO
from logic.config_watcher import cfg
from logic.capture import capture
from logic.macro import MacroThread
from logic.overlay import overlay
from logic.visual import visuals
from logic.shooting import shooting
from logic.frame_parser import frameParser
from logic.hotkeys_watcher import hotkeys_watcher
from logic.checks import run_checks


# --- Log Queue Setup ---
log_queue = queue.Queue()
running = threading.Event()


class QueueWriter:
    def write(self, text):
        if text.strip():
            # Füge hier die Logik für farbige Warnungen ein
            if "WARNING" in text:
                text = f'<span style="color: red; font-weight: bold;">{text}</span>'
            log_queue.put(text)
    def flush(self):
        pass

sys.stdout = QueueWriter()
sys.stderr = QueueWriter()

def detect_base_dir(): 
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent 
    else:
        return Path(__file__).parent 

BASE_DIR = detect_base_dir()

class ThreadManager:
    def __init__(self):
        self.threads = []
        self.model = None
        
    def create_threads(self):
        # Reset all thread instances
        capture.__init__()
        shooting.__init__()
        visuals.__init__()
        hotkeys_watcher.__init__()
        if cfg.show_overlay:
            overlay.__init__()
            
        # Create thread list
        self.threads = [capture, shooting, visuals, hotkeys_watcher]
        if cfg.primary_macro or cfg.secondary_macro:
            self.threads.append(MacroThread())
        if cfg.show_overlay:
            self.threads.append(overlay)
    
    def start_threads(self):
        for thread in self.threads:
            if thread == overlay:
                thread.start()
            else:
                thread.start()
                
    def stop_threads(self):
            # Erst alle Threads stoppen
            for thread in self.threads:
                if thread.is_alive():
                    thread.stop() 
            
            # Dann auf alle Threads warten
            for thread in self.threads:
                if thread.is_alive():
                    thread.join(timeout=2.0)  
                    
            self.threads.clear()

thread_manager = ThreadManager()

# Init ByteTrack
if cfg.disable_tracker == False:
    import supervision as sv
    byte_tracker = sv.ByteTrack()
    
@torch.inference_mode()
def perform_detection(model, image, tracker=None):
    if tracker is not None:
        results = model.predict(
            source=image,
            cfg="logic/tracker.yaml",
            imgsz=cfg.ai_model_image_size,
            stream=True,
            conf=cfg.AI_conf,
            iou=0.5,
            device=cfg.AI_device,
            half=False if "cpu" in cfg.AI_device else True,
            max_det=20,
            agnostic_nms=False,
            augment=False,
            vid_stride=False,
            visualize=False,
            verbose=False,
            show_boxes=False,
            show_labels=False,
            show_conf=False,
            save=False,
            show=False)
        
        for result in results:
            # Convert results to detections
            detections = sv.Detections.from_ultralytics(result)
            tracked_detections = byte_tracker.update_with_detections(detections)
            return tracked_detections
    else:
        result = next(model.predict(
            source=image,
            cfg="logic/game.yaml",
            imgsz=cfg.ai_model_image_size,
            stream=True,
            conf=cfg.AI_conf,
            iou=0.5,
            device=cfg.AI_device,
            half=False if "cpu" in cfg.AI_device else True,
            max_det=20,
            agnostic_nms=False,
            augment=False,
            vid_stride=False,
            visualize=False,
            verbose=False,
            show_boxes=False,
            show_labels=False,
            show_conf=False,
            save=False,
            show=False))
        
        return result
    
def init():
    running.set()
    run_checks()
    model_path = BASE_DIR / "models" / cfg.AI_model_name
    
    thread_manager.create_threads()
    thread_manager.start_threads()
        
    if not model_path.exists():
        print(f"Fehler: Modell nicht gefunden: {model_path}")
        return  

    try:
        model = YOLO(str(model_path), task="detect")
    except Exception as e:
        print("Fehler beim Laden des AI-Modells:\n", e)
        return  
    
    try:
        while running.is_set():
            image = capture.get_new_frame()
            if image is not None:
                if cfg.circle_capture:
                    image = capture.convert_to_circle(image)
                if cfg.show_window or cfg.show_overlay:
                    visuals.queue.put(image)

                result = perform_detection(model, image, byte_tracker)
                if result is not None and cfg.aim_active and hotkeys_watcher.app_pause == 0:
                    frameParser.parse(result)
                 
    finally:
        # Cleanup
        if 'model' in locals():
            if torch.cuda.is_available():
                torch.cuda.synchronize()
                torch.cuda.empty_cache()
            del model
            
        thread_manager.stop_threads()

def main():
    running.set()
    init()

def stop():
    running.clear()
    if torch.cuda.is_available():
        torch.cuda.synchronize()

if __name__ == "__main__":
    main()