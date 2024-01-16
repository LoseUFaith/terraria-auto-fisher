import cv2
import numpy as np
import sys
import mss.tools


class MovementTracker:
    def __init__(self, n):
        self.change_buffer = None
        self.size = n
        self.counter = 0

    def get_diff(self, img, threshold):
        if not self.change_buffer:
            self.change_buffer = [img for _ in range(self.size)]
        self.change_buffer[self.counter] = img
        self.counter = (self.counter + 1) % self.size
        buff = self.change_buffer[self.counter:] + self.change_buffer[:self.counter]
        return self.diff_3_img(buff[:3], threshold)

    @staticmethod
    def diff_3_img(buff, threshold):
        t0, t1, t2 = buff
        d1 = cv2.absdiff(t2, t1)
        d2 = cv2.absdiff(t1, t0)
        res = cv2.bitwise_or(d1, d2)
        t, res = cv2.threshold(res, threshold, 255, cv2.THRESH_BINARY)
        return res


class Visual:
    def __init__(self, inputX, inputY, shift, threshold, sensitivity):
        self.tracker = MovementTracker(3)
        self.inputScreenX = inputX
        self.inputScreenY = inputY
        self.shift = shift if sys.platform != 'darwin' else shift / 2
        self.threshold = threshold
        self.sensitivity = sensitivity

    def get_box(self):
        box = (
            self.inputScreenX.value() - self.shift,
            self.inputScreenY.value() - self.shift,
            self.inputScreenX.value() + self.shift,
            self.inputScreenY.value() + self.shift
        )
        return box

    def get_image(self):
        # image = ImageGrab.grab(bbox=(self.inputXStart, self.inputYStart, self.inputXEnd, self.inputYEnd))
        with mss.mss() as sct:
            monitor = self.get_box()
            image = sct.grab(monitor)

        grayImage = cv2.cvtColor(np.array(image), cv2.COLOR_BGR2GRAY)
        preview = self.tracker.get_diff(grayImage, self.threshold.value())

        return image, preview

    def get_sense(self, preview):
        count = cv2.countNonZero(preview)
        sense = count * int(self.sensitivity.value()) / ((self.shift * 2) ** 2)

        return sense
