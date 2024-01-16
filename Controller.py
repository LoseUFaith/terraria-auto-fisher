import sys
import subprocess
import time
import pyautogui
import pynput.mouse as pm


class ActionController:

    def __init__(self, potion_key, action_disabled=False):
        self.mouse = pm.Controller()
        self.potion_key = potion_key
        self.action_disabled = action_disabled

    def click(self):
        if self.action_disabled:
            print("Click triggered but action disabled")
            return

        if sys.platform == 'linux':
            subprocess.call(['xdotool', 'mousedown', '1'])
            time.sleep(0.02)
            subprocess.call(['xdotool', 'mouseup', '1'])
        elif sys.platform == 'win32':
            pyautogui.mouseDown()
            time.sleep(0.05)
            pyautogui.mouseUp()
        elif sys.platform == "darwin":
            self.mouse.press(pm.Button.left)
            time.sleep(0.05)
            self.mouse.release(pm.Button.left)
        else:
            raise RuntimeError("This system is not supported yet: {0}".format(sys.platform))

    def drink_potion(self):
        if self.action_disabled:
            print("Potion triggered but action disabled")
            return

        potionDrinkTime = time.time()
        pyautogui.keyDown(self.potion_key)
        time.sleep(0.02)
        pyautogui.keyUp(self.potion_key)

        return potionDrinkTime
