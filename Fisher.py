import time
import threading
from collections import deque

import cv2

import Controller
from FisherStateMachine import FisherStateMachine
from Visual import Visual

# Queue size is multiplied by max frame rate
MESSAGE_QUEUE_SIZE = 5

# Disable Controller action when debugging
IN_DISABLE_ACTION = False

IN_SINGLE_RUN = False


class Fisher:
    def __init__(self, inputX, inputY, shift, threshold, sensitivity, potionKey, potionChecked, potionDelay,
                 maxFrameRate=66, tickingUploader=None):
        self.potionDelay = potionDelay
        self.potionChecked = potionChecked
        self.potionKey = potionKey
        self.potionDrinkTime = None
        self.maxFrameRate = maxFrameRate
        self.tickingUploader = tickingUploader
        self.fpsDelta = 0.001401

        self.state = None
        self.actionController = Controller.ActionController(self.potionKey, IN_DISABLE_ACTION)
        self.visual = Visual(inputX, inputY, shift, threshold, sensitivity)

        self.onStop = threading.Event()
        self.onStop.clear()

        self.messageQueue = deque(maxlen=MESSAGE_QUEUE_SIZE * self.maxFrameRate)
        self.processTicks = 0

        if not IN_SINGLE_RUN:
            self.mainThread = threading.Thread(target=self.main_loop)
            self.mainThread.start()

    def start_fishing(self):
        self.state = FisherStateMachine(self.actionController.click)
        self.potionDrinkTime = time.time()

    def stop_fishing(self):
        self.state = None
        self.potionDrinkTime = None

    def in_fishing(self):
        return self.state is not None

    def stop_running(self):
        self.onStop.set()
        self.mainThread.join()

    def get_graphical_info(self):
        if len(self.messageQueue) > 0:
            return self.messageQueue[-1]
        else:
            return None

    def get_state_description(self):
        if self.state:
            return self.state.state.description
        else:
            return None

    def get_potion_drinking_in(self):
        if self.potionDrinkTime:
            drinkingIn = int(self.potionDrinkTime + self.potionDelay.value() - time.time())
            return drinkingIn
        else:
            return None

    def fps_limiter(self, lastFrameTime):
        if lastFrameTime:
            waitTime = max(0.0, 1 / self.maxFrameRate - (time.perf_counter() - lastFrameTime) - self.fpsDelta)
            self.onStop.wait(waitTime)
        return time.perf_counter()

    def main_loop(self):
        lastFrameTime = time.perf_counter()
        while not self.onStop.is_set():
            self.processTicks += 1
            beginTime = time.perf_counter()
            if self.potionChecked.isChecked() and self.potionDrinkTime:
                drinkingIn = self.get_potion_drinking_in()
                if drinkingIn < 0:
                    self.potionDrinkTime = self.actionController.drink_potion()

            try:
                image, preview = self.visual.get_image()
            except cv2.error:
                continue
            sense = self.visual.get_sense(preview)

            if self.state:
                self.state.update(sense)

            self.messageQueue.append((image, preview, sense, beginTime))

            finishTime = time.perf_counter()
            if self.tickingUploader:
                self.tickingUploader({
                    "ticks": self.processTicks,
                    "beginTime": beginTime,
                    "endTime": finishTime
                })

            lastFrameTime = self.fps_limiter(lastFrameTime)
