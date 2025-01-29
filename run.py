import torch
import sys
import os
from pathlib import Path
from ultralytics import YOLO
from logic.config_watcher import cfg
from logic.capture import capture
from logic.visual import visuals
from logic.frame_parser import frameParser
from logic.hotkeys_watcher import hotkeys_watcher
from logic.checks import run_checks
import supervision as sv  # Import for ByteTrack

def detect_base_dir():
    if getattr(sys, 'frozen', False):  
        return Path(sys.executable).parent 
    else:
        return Path(__file__).parent 

# Basisverzeichnis bestimmen
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
            show=False))
        
        return result

def init():
    run_checks()
    
    model_path = BASE_DIR / "models" / cfg.AI_model_name
    if not model_path.exists():
        print(f"❌ Fehler: Modell nicht gefunden: {model_path}")
        sys.exit(1)
    try:
        model = YOLO(str(model_path), task="detect")
    except Exception as e:
        print("❌ Fehler beim Laden des AI-Modells:\n", e)
        sys.exit(1)
    
    while True:
        image = capture.get_new_frame()
        
        if image is not None:
            if cfg.circle_capture:
                image = capture.convert_to_circle(image)
            
            if cfg.show_window or cfg.show_overlay:
                visuals.queue.put(image)
                
            result = perform_detection(model, image)

            if cfg.aim_active and hotkeys_watcher.app_pause == 0:
                frameParser.parse(result)

if __name__ == "__main__":
    init()
