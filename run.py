import sys
import os
import queue
import threading
import torch
from pathlib import Path
from ultralytics import YOLO
from logic.config_watcher import cfg
from logic.capture import capture
from logic.macro import macro
from logic.overlay import overlay
from logic.visual import visuals
from logic.shooting import shooting
from logic.frame_parser import frameParser
from logic.hotkeys_watcher import hotkeys_watcher
from logic.checks import run_checks
import supervision as sv
import time

# --- Log Queue Setup ---
log_queue = queue.Queue()
# Event für Thread-Kontrolle
running = threading.Event()
running.set()  # Standardmäßig läuft das Programm

class QueueWriter:
    def write(self, text):
        if text.strip():
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

@torch.inference_mode()
def perform_detection(model, image):
    if not cfg.disable_tracker: 
        byte_tracker = sv.ByteTrack()
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
            show=False
        ))
        return result

def init():
    running.set()  
    run_checks()
    model_path = BASE_DIR / "models" / cfg.AI_model_name
    
    threads = [capture, shooting, visuals, hotkeys_watcher]
    if cfg.primary_macro or cfg.secondary_macro:
        threads.append(macro)
    if cfg.show_overlay:
        threads.append(overlay)

    # Starte alle Threads
    for thread in threads:
        if thread == overlay:
            thread.start()
        else:
            thread.start()
        
    if not model_path.exists():
        print(f"Fehler: Modell nicht gefunden: {model_path}")
        return  

    try:
        model = YOLO(str(model_path), task="detect")
    except Exception as e:
        print("Fehler beim Laden des AI-Modells:\n", e)
        return  
    
    try:
        while running.is_set():  # Nutze running Event statt stop_flag
            image = capture.get_new_frame()
            if image is not None:
                if cfg.circle_capture:
                    image = capture.convert_to_circle(image)
                if cfg.show_window or cfg.show_overlay:
                    visuals.queue.put(image)

                result = perform_detection(model, image)
                if result is not None and cfg.aim_active and hotkeys_watcher.app_pause == 0:
                    frameParser.parse(result)
                 
    finally:
        # Cleanup
        if 'model' in locals():
            if torch.cuda.is_available():
                torch.cuda.synchronize()
                torch.cuda.empty_cache()
            del model
            
        for thread in threads:
            thread.stop()

def main():
    running.set()  # Setze running Event
    init()

def stop():
    running.clear()  # Clear running Event
    if torch.cuda.is_available():
        torch.cuda.synchronize()  # Warte auf CUDA-Operationen

if __name__ == "__main__":
    main()