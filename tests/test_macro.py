# test_macro.py
from logic.macro import Macro
import time

try:
    macro = Macro("NTEC APB")  # Ersetze "DefaultMacro" mit deinem Makronamen
    print("Macro loaded successfully:")
    print(f"Name: {macro.major}")
    print(f"Hotkey: {macro.hotkey}")

    # Test KeyDown
    print("Running KeyDown...")
    macro.run_key_down()
    time.sleep(2)  # Warte 2 Sekunden

    # Test KeyUp
    print("Running KeyUp...")
    macro.run_key_up()
except Exception as e:
    print(f"Error loading macro: {e}")
