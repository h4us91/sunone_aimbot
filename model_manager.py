# In einer neuen Datei model_manager.py
import torch
from ultralytics import YOLO
import supervision as sv
from logic.thread_stop import stop_flag

class ModelManager:
    def __init__(self, model_path, cfg):
        self.model = YOLO(str(model_path), task="detect")
        self.cfg = cfg
        self.byte_tracker = sv.ByteTrack() if not cfg.disable_tracker else None
        self._engine = None
        
    def __del__(self):
        self.cleanup()
        
    def cleanup(self):
        if hasattr(self, 'model') and self.model is not None:
            try:
                # Warte auf alle CUDA-Operationen
                if torch.cuda.is_available():
                    torch.cuda.synchronize()
                
                # Beende TensorRT Engine falls vorhanden
                if hasattr(self.model.model, 'engine'):
                    self.model.model.engine = None
                
                # Lösche Modell
                del self.model
                self.model = None
                
                # Cache leeren
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    
            except Exception as e:
                print(f"Fehler beim Cleanup: {e}")

    def perform_detection(self, image):
        if stop_flag.is_set():
            return None
            
        try:
            if not self.cfg.disable_tracker:
                results = self.model.predict(
                    source=image,
                    cfg="logic/tracker.yaml",
                    imgsz=self.cfg.ai_model_image_size,
                    stream=True,
                    conf=self.cfg.AI_conf,
                    iou=0.5,
                    device=self.cfg.AI_device,
                    half=False if "cpu" in self.cfg.AI_device else True,
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
                    if stop_flag.is_set():
                        return None
                    detections = sv.Detections.from_ultralytics(result)
                    return self.byte_tracker.update_with_detections(detections)
            else:
                if stop_flag.is_set():
                    return None
                    
                result = next(self.model.predict(
                    source=image,
                    cfg="logic/game.yaml",
                    imgsz=self.cfg.ai_model_image_size,
                    stream=True,
                    conf=self.cfg.AI_conf,
                    iou=0.5,
                    device=self.cfg.AI_device,
                    half=False if "cpu" in self.cfg.AI_device else True,
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
                
        except Exception as e:
            print(f"Fehler in perform_detection: {e}")
            return None