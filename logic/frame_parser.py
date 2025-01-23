import torch
from logic.hotkeys_watcher import hotkeys_watcher
from logic.config_watcher import cfg
from logic.capture import capture
from logic.visual import visuals
from logic.mouse import mouse
from logic.shooting import shooting
import supervision as sv
import numpy as np
import cv2





class Target:
    def __init__(self, x, y, w, h, cls):
        self.x = x
        self.y = y if cls == 7 else (y - cfg.body_y_offset * h)
        self.w = w
        self.h = h
        self.cls = cls
        
        
        
class FrameParser:
    def __init__(self):
        self.arch = self.get_arch()

    def parse(self, result):
        image = capture.get_new_frame()  
        if image is None:
            return  
        if isinstance(result, sv.Detections):
            self._process_sv_detections(result, image)
        else:
            self._process_yolo_detections(result, image)

    def _process_sv_detections(self, detections, image):
        if detections is not None and detections.xyxy.any():
            if cfg.track_red_names_only:
                detections = self.filter_red_name_targets(detections, image)  
            if detections is not None and detections.xyxy.any(): 
                target = self.sort_targets(detections)
                self._handle_target(target)

    def _process_yolo_detections(self, results, image):
        for frame in results:
            if frame.boxes:
                if cfg.track_red_names_only:
                    red_name_targets = self.filter_red_name_targets(frame, image)  
                    if red_name_targets is not None and red_name_targets.xyxy.any():  
                        target = self.sort_targets(red_name_targets)
                        self._handle_target(target)
                else:
                    target = self.sort_targets(frame)
                    self._handle_target(target)

                self._visualize_frame(frame)

    def filter_red_name_targets(self, detections, image):
        red_targets = [i for i, box in enumerate(detections.xyxy) if self.is_red_name(image, box)]

        if not red_targets:
            return None

        return sv.Detections(
            xyxy=detections.xyxy[red_targets],
            confidence=detections.confidence[red_targets],
            class_id=detections.class_id[red_targets],
            tracker_id=detections.tracker_id[red_targets] if detections.tracker_id is not None else None,
            data={key: val[red_targets] for key, val in detections.data.items()},
            metadata=detections.metadata
        )



    def is_red_name(self, image, box, red_threshold=0.2):  # Threshold leicht gesenkt
        x1, y1, x2, y2 = box[:4].astype(int)

        # Größeren Namensbereich erfassen
        name_height = int((y2 - y1) * 0.35)  # Erhöht auf 35%
        name_y1 = max(0, y1 - name_height)  # Verhindert negative Werte
        name_region = image[name_y1:y1, x1:x2]

        if name_region.size == 0:
            return False

        hsv = cv2.cvtColor(name_region, cv2.COLOR_BGR2HSV)

        # Erweiterter Rottönungsbereich
        lower_red1 = np.array([0, 70, 50])  
        upper_red1 = np.array([10, 255, 255])
        lower_red2 = np.array([160, 70, 50])
        upper_red2 = np.array([180, 255, 255])

        mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
        mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
        mask = mask1 + mask2

        red_pixel_ratio = cv2.countNonZero(mask) / (name_region.shape[0] * name_region.shape[1])

        return red_pixel_ratio > red_threshold  # Senkt Threshold leicht auf 0.2



    def _handle_target(self, target):
        if target:
            if hotkeys_watcher.clss is None:
                hotkeys_watcher.active_classes()
            
            if cfg.third_person and target.cls == 10:
                return

            if target.cls in hotkeys_watcher.clss:
                mouse.process_data((target.x, target.y, target.w, target.h, target.cls))


    def _visualize_frame(self, frame):
        if cfg.show_window or cfg.show_overlay:
            if cfg.show_boxes or cfg.overlay_show_boxes:
                visuals.draw_helpers(frame.boxes)
            
            if cfg.show_window and cfg.show_detection_speed:
                visuals.draw_speed(frame.speed['preprocess'], frame.speed['inference'], frame.speed['postprocess'])
        
        # Handle no detections
        if not frame.boxes and (cfg.auto_shoot or cfg.triggerbot):
            shooting.shoot(False, False)
        
        if cfg.show_window or cfg.show_overlay:
            if not frame.boxes:
                visuals.clear()

    def sort_targets(self, frame):
        if isinstance(frame, sv.Detections):
            boxes_array, classes_tensor = self._convert_sv_to_tensor(frame)
        else:
            boxes_array = frame.boxes.xywh.to(self.arch)
            classes_tensor = frame.boxes.cls.to(self.arch)
        
        if not classes_tensor.numel():
            return None

        return self._find_nearest_target(boxes_array, classes_tensor)

    def _convert_sv_to_tensor(self, frame):
        xyxy = frame.xyxy
        xywh = torch.tensor([
            (xyxy[:, 0] + xyxy[:, 2]) / 2,  
            (xyxy[:, 1] + xyxy[:, 3]) / 2,  
            xyxy[:, 2] - xyxy[:, 0],        
            xyxy[:, 3] - xyxy[:, 1]        
        ], dtype=torch.float32).to(self.arch).T
        
        classes_tensor = torch.from_numpy(np.array(frame.class_id, dtype=np.float32)).to(self.arch)
        return xywh, classes_tensor

    def _find_nearest_target(self, boxes_array, classes_tensor):
        center = torch.tensor([capture.screen_x_center, capture.screen_y_center], device=self.arch)
        distances_sq = torch.sum((boxes_array[:, :2] - center) ** 2, dim=1)
        weights = torch.ones_like(distances_sq)

        if cfg.disable_headshot:
            non_head_mask = classes_tensor != 7
            weights = torch.ones_like(classes_tensor)
            weights[classes_tensor == 7] *= 0.5
            size_factor = boxes_array[:, 2] * boxes_array[:, 3]
            distances_sq = weights * (distances_sq / size_factor)

            if not non_head_mask.any():
                return None
            nearest_idx = torch.argmin(distances_sq[non_head_mask])
            nearest_idx = torch.nonzero(non_head_mask)[nearest_idx].item()
        else:
            head_mask = classes_tensor == 7
            if head_mask.any():
                nearest_idx = torch.argmin(distances_sq[head_mask])
                nearest_idx = torch.nonzero(head_mask)[nearest_idx].item()
            else:
                nearest_idx = torch.argmin(distances_sq)
        
        target_data = boxes_array[nearest_idx, :4].cpu().numpy()
        target_class = classes_tensor[nearest_idx].item()

        return Target(*target_data, target_class)

    def get_arch(self):
        if cfg.AI_enable_AMD:
            return f'hip:{cfg.AI_device}'
        elif 'cpu' in cfg.AI_device:
            return 'cpu'
        else:
            return f'cuda:{cfg.AI_device}'

frameParser = FrameParser()