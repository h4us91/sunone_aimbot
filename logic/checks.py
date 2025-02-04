import torch
import os
from logic.config_watcher import cfg
import sys

def convert_onnx_to_fp16():
    import onnx
    from onnxconverter_common import float16
    
    model = onnx.load(f"models/{cfg.AI_model_name}")
    model_fp16 = float16.convert_float_to_float16(model)
    new_model_name = cfg.AI_model_name.replace(".onnx", "_fp16.onnx")
    onnx.save(model_fp16, f"models/{new_model_name}")
    
    print(f"Converted model saved as 'models/{new_model_name}'.\n"
          f"Please change the ai_model_name option to the converted version of the model ({new_model_name}).")
    
def check_model_fp16():
    try:
        import onnx
        from onnxconverter_common import float16
    except ModuleNotFoundError:
        os.system("pip install onnx onnxconverter-common")
    
    model = onnx.load(f"models/{cfg.AI_model_name}")
    
    graph = model.graph
    
    for input_tensor in graph.input:
        tensor_type = input_tensor.type.tensor_type
        if tensor_type.elem_type == onnx.TensorProto.FLOAT16:
            return True
    
    for output_tensor in graph.output:
        tensor_type = output_tensor.type.tensor_type
        if tensor_type.elem_type == onnx.TensorProto.FLOAT16:
            return True
    
    return False

def Warnings():
        print("------------------------------------------------------------------------------------") 
        print("This is an external program, making bans less likely compared to internal cheats. For the safest experience, Arduino-based bypasses are recommended for anti-cheats like Vanguard and FACEIT. `win32api` can work for Fortnite and some EAC/BE-protected games but may be detected. Kernel bypass uses an unsigned IOCTL driver with kdmapper—only use it for older games with kernel-level anti-cheat. Use all methods at your own risk!")
        print("------------------------------------------------------------------------------------") 
        if ".pt" in cfg.AI_model_name:
            print("WARNING: Export the model to `.engine` for better performance!\nHOW TO EXPORT TO ENGINE: 'https://github.com/SunOner/sunone_aimbot_docs/blob/main/ai_models/ai_models.md'")
        if cfg.show_window:
            print("WARNING: An open debug window can affect performance.")
        if cfg.bettercam_capture_fps >= 120:
            print("WARNING: A large number of frames per second can affect the behavior of automatic aiming. (Shaking).")
        if cfg.detection_window_width >= 600:
            print("WARNING: The object detector window is more than 600 pixels wide, and a large object detector window can have a bad effect on performance.")
        if cfg.detection_window_height >= 600:
            print("WARNING: The object detector window is more than 600 pixels in height, a large object detector window can have a bad effect on performance.")
        if cfg.AI_conf <= 0.15:
            print("WARNING: A small value of `AI_conf ` can lead to a large number of false positives.")
               # tracker
        if cfg.disable_tracker == True:
            print("ultralytics tracking system causes more overhead compute power, might cause performance issues")
        # mouse
        if cfg.mouse_ghub == False and cfg.arduino_move == False and cfg.arduino_shoot == False and cfg.kernel_bypass == False:
            print("WARNING: win32api is detected in some games.")
        if cfg.mouse_ghub and cfg.arduino_move == False and cfg.arduino_shoot == False:
            print("WARNING: ghub is detected in some games.")
        if cfg.arduino_move == False:
            print("WARNING: Using standard libraries for mouse moving such as `win32` or `Ghub driver` without bypassing, for example, how Arduino can speed up the account blocking process, use it at your own risk.")
        if cfg.arduino_shoot == False and cfg.auto_shoot:
            print("WARNING: Using standard libraries for mouse shooting such as `win32` or `Ghub driver` without bypassing, for example, how Arduino can speed up the account blocking process, use it at your own risk.")
        if cfg.kernel_bypass:
            print("WARNING: Kernel Bypass is enabled. Ensure that the driver is correctly loaded using mapper.exe!")

        selected_methods = sum([cfg.arduino_move, cfg.mouse_ghub, cfg.mouse_rzr, cfg.kernel_bypass])
        if selected_methods > 1:
            print("WARNING: Multiple mouse input methods are enabled. This can cause conflicts and unexpected behavior. Please check the mouse settings tab and select only one preferred input method for optimal performance.")
            sys.exit(1)
            
        
def run_checks():
    if torch.cuda.is_available() is False:
        print("No CUDA-compatible GPU detected. If you're using a laptop, ensure your dedicated GPU is active and not running on integrated graphics.")
        sys.exit(1)
        
    if + cfg.mss_capture + cfg.Bettercam_capture + cfg.Obs_capture < 1:
        print("Use at least one image capture method.\nSet the value to `True` in the `bettercam_capture` option or in the `obs_capture` option or in the `mss_capture` option.")
        sys.exit(1)
        
    if  cfg.mss_capture + cfg.Bettercam_capture + cfg.Obs_capture > 1:
        print("Only one capture method is possible.\nSet the value to `True` in the `bettercam_capture` option or in the `obs_capture` option or in the `mss_capture` option.")
        sys.exit(1)

    if not os.path.exists(f"models/{cfg.AI_model_name}"):
        print(f"The AI model {cfg.AI_model_name} has not been found! Check the correctness of the model name in the AI_model_name option.")
        sys.exit(1)
    
    if cfg.AI_model_name.endswith(".onnx"):
        fp16 = check_model_fp16()
        if fp16 == False:
            check_converted_model = cfg.AI_model_name.replace(".onnx", "_fp16.onnx")
            if not os.path.exists(f"models/{check_converted_model}"):
                print(f"The current AI format of the '{cfg.AI_model_name}' model is fp32. Converting model to fp16...")
                convert_onnx_to_fp16()
                sys.exit(1)
            else:
                print(f"Please, use converted model - '{check_converted_model}'.\nChange in config.ini 'AI_model_name = {check_converted_model}'")
                sys.exit(1)
    Warnings()