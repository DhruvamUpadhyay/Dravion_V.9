import pyautogui
from core.logger import log

def move_mouse(x, y, duration=0.5):
    pyautogui.moveTo(int(x), int(y), duration=duration)
    return f"Mouse moved to {x}, {y}."

def click(x=None, y=None, button='left'):
    if x is not None and y is not None:
        pyautogui.click(x=int(x), y=int(y), button=button)
        return f"Clicked {button} at {x}, {y}."
    else:
        pyautogui.click(button=button)
        return f"Clicked {button}."

def type_text(text, interval=0.01):
    pyautogui.write(text, interval=interval)
    return "Text typed successfully."

def press_key(key):
    pyautogui.press(key)
    return f"Pressed '{key}' key."

def hotkey(*keys):
    pyautogui.hotkey(*keys)
    return f"Pressed hotkey: {'+'.join(keys)}."
    
def get_mouse_position():
    x, y = pyautogui.position()
    return f"Current mouse position: {x}, {y}"
