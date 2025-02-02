import time
from logic.macro import MacroManager

def test_macro_manager():
    macro_manager = MacroManager()
    print("[INFO] Starte Makro-Test...")

    try:
        current_macro = macro_manager.current_macro
        print(f"[INFO] Aktives Makro: {current_macro}")
        
        while True:
            macro_manager.check_keys()
            
            if macro_manager._is_key_pressed(macro_manager.switch_key):
                macro_manager._switch_macro()
                current_macro = macro_manager.current_macro
                print(f"[INFO] Makro gewechselt zu: {current_macro}")
                time.sleep(0.3)  # Kurze Pause, um mehrfaches Umschalten zu vermeiden
            
            if macro_manager._is_key_pressed(macro_manager.fire_key):
                print(f"[INFO] Führe Makro aus: {current_macro}")
                macro_manager._execute_macro()
                time.sleep(0.3)  # Kurze Pause nach dem Ausführen des Makros
            
            time.sleep(0.1)  # Verhindert CPU-Überlastung
    except KeyboardInterrupt:
        print("[INFO] Test beendet.")

if __name__ == "__main__":
    test_macro_manager()    