import curses
import threading
import time
from collections import deque
from Fisher import Fisher

# Queue size is multiplied by max frame rate
PERFORMANCE_QUEUE_SIZE = 10
INFO_QUEUE_SIZE = 3

ANALYSE_INTERVAL = 20


class ConsoleWriter:
    def __init__(self, mode):
        self.mode = mode
        self.buffer = []
        self.stdCrs = curses.initscr()

    def write(self, message):
        for line in message.splitlines():
            self.buffer.append(line)

    def flush(self):
        self.stdCrs.clear()
        self.stdCrs.addstr("\n".join(self.buffer))
        self.stdCrs.refresh()
        self.buffer.clear()

    def display_info(self, performanceInfo, calibrationInfo=None):
        if self.mode == "calibrate":
            self.write("========================================")
            self.write("Current Ticks {0}".format(performanceInfo["lastTick"]))
            self.write("DELTA CALIBRATION (target: {0:.2f} ± {1:.2f})".format(calibrationInfo["target"],
                                                                              calibrationInfo["error"]))
            self.write("----------------------------------------")
            self.write("FPS_DELTA: {0:.6f}".format(calibrationInfo["delta"]))
            self.write("Calibre: ({0:.6f} - {1:.6f})".format(calibrationInfo["low"], calibrationInfo["high"]))
            self.write(
                "Middle value: ({0:.6f}, {1:.6f})".format(calibrationInfo["leftMidVal"],
                                                          calibrationInfo["rightMidVal"]))
            self.write("----------------------------------------")
            self.write("Current tick rate: {0:.6f}".format(performanceInfo["tickRate"]))
            self.write("========================================")
            self.flush()
        elif self.mode == "performance":
            self.write("========================================")
            self.write("PERFORMANCE ANALYSIS (last {0} frames)".format(performanceInfo["ticks"]))
            self.write("From {0:.6f} to {1:.6f}".format(performanceInfo["beginTime"], performanceInfo["endTime"]))
            self.write("Last tick: {:d}".format(performanceInfo["lastTick"]))
            self.write("----------------------------------------")
            self.write("Performance: {0:.6f} ticks/s".format(performanceInfo["tickRate"]))
            self.write("Milliseconds per tick: {0:.6f} ms".format(performanceInfo["millisecondsPerTick"]))
            self.write("========================================")
            self.flush()


class DeltaCalibrator:
    def __init__(self, low, high, target, error=0.5):
        self.low = low
        self.high = high
        self.target = target
        self.error = error

        self.mid = (self.low + self.high) / 2
        self.lMid = (self.low + self.mid) / 2
        self.rMid = (self.mid + self.high) / 2

        self.lMidVal = 0
        self.rMidVal = 0

        self.prevMode = None

    def update(self, fps):
        # Use a ternary search to correct the delta
        if self.prevMode == "r":
            self.lMidVal = fps
            self.prevMode = 'l'
            return self.rMid
        elif self.prevMode == "l":
            self.rMidVal = fps

            lDiff = self.target - self.lMidVal
            rDiff = self.rMidVal - self.target

            if abs(lDiff) < self.error and abs(rDiff) < self.error:
                self.prevMode = None
                return self.mid

            if lDiff < rDiff:
                self.high = self.rMid
                self.mid = (self.low + self.high) / 2
                self.lMid = (self.low + self.mid) / 2
                self.rMid = (self.mid + self.high) / 2
            else:
                self.low = self.rMid
                self.mid = (self.low + self.high) / 2
                self.lMid = (self.low + self.mid) / 2
                self.rMid = (self.mid + self.high) / 2

            self.prevMode = 'r'
            return self.lMid
        else:
            if abs(fps - self.target) < self.error:
                return self.mid

            self.lMidVal = fps
            self.prevMode = 'l'
            return self.lMid


class PerformanceMonitor:
    def __init__(self, maxFrameRate, analyzeInterval, handler=None):

        self.maxFrameRate = maxFrameRate
        self.handler = handler
        self.analyzeInterval = analyzeInterval

        self.onStop = threading.Event()
        self.onStop.clear()
        self.performanceQueue = deque(maxlen=PERFORMANCE_QUEUE_SIZE * self.maxFrameRate)
        self.queueLock = threading.Lock()

        self.mainThread = threading.Thread(target=self.performance_loop)
        self.mainThread.start()

    def stop_running(self):
        self.onStop.set()
        self.mainThread.join()

    def performance_loop(self):
        accumulatedTicks = 0
        accumulatedTickTime = 0
        FirstTickTime = None

        nextAnalyzeTime = time.perf_counter() + self.analyzeInterval
        accumulatingInterval = min(self.analyzeInterval, PERFORMANCE_QUEUE_SIZE - 1) * 0.5

        while not self.onStop.is_set():
            if len(self.performanceQueue) > 0:
                with self.queueLock:
                    accumulatedTicks += len(self.performanceQueue)
                    accumulatedTickTime += sum([x[2] - x[1] for x in self.performanceQueue])
                    lastTickTime = self.performanceQueue[-1][2]
                    lastTick = self.performanceQueue[-1][0]

                    if FirstTickTime is None:
                        FirstTickTime = self.performanceQueue[0][1]

                    self.performanceQueue.clear()

                if time.perf_counter() > nextAnalyzeTime:
                    tickedTime = lastTickTime - FirstTickTime
                    tickRate = accumulatedTicks / tickedTime
                    millisecondsPerTick = accumulatedTickTime / accumulatedTicks * 1000

                    if self.handler is not None:
                        self.handler({
                            "time": time.perf_counter(),
                            "beginTime": FirstTickTime,
                            "endTime": lastTickTime,
                            "lastTick": lastTick,
                            "tickedTime": tickedTime,
                            "ticks": accumulatedTicks,
                            "tickRate": tickRate,
                            "millisecondsPerTick": millisecondsPerTick
                        })

                    accumulatedTicks = 0
                    accumulatedTickTime = 0
                    FirstTickTime = None
                    nextAnalyzeTime += self.analyzeInterval

            self.onStop.wait(accumulatingInterval)

    def add_tick(self, tickingInfo):
        with self.queueLock:
            self.performanceQueue.append((tickingInfo["ticks"], tickingInfo["beginTime"], tickingInfo["endTime"]))


class FisherMonitoring(Fisher):
    def __init__(self, inputX, inputY, shift, threshold, sensitivity, potionKey, potionChecked, potionDelay,
                 maxFrameRate=66, infoUploader=None):
        self.infoUploader = infoUploader
        self.performanceMonitor = PerformanceMonitor(maxFrameRate, ANALYSE_INTERVAL, self.performance_handler)
        self.consoleWriter = ConsoleWriter(mode="performance")

        super().__init__(inputX, inputY, shift, threshold, sensitivity, potionKey, potionChecked, potionDelay,
                         maxFrameRate, self.performanceMonitor.add_tick)

        self.calibrator = DeltaCalibrator(0.0, 0.01, maxFrameRate)
        self.fpsDelta = 0.001401

        self.infoQueue = deque(maxlen=INFO_QUEUE_SIZE * maxFrameRate)
        self.queueLock = threading.Lock()

        self.onStop = threading.Event()
        self.working = threading.Event()

        self.infoThread = threading.Thread(target=self.info_loop)
        self.infoThread.start()

    def performance_handler(self, performanceInfo):
        with self.queueLock:
            self.infoQueue.append(performanceInfo)
        self.working.set()

    def stop_running(self):
        super().stop_running()
        self.performanceMonitor.stop_running()
        self.onStop.set()
        self.working.set()
        self.infoThread.join()

    def info_loop(self):
        while not self.onStop.is_set():
            self.working.wait()
            self.working.clear()

            performanceInfo = {}
            with self.queueLock:
                if len(self.infoQueue) > 0:
                    performanceInfo = self.infoQueue.pop()
                    self.infoQueue.clear()

            if performanceInfo:
                # self.fpsDelta = self.calibrator.update(performanceInfo["tickRate"])
                calibrationInfo = {
                    "target": self.calibrator.target,
                    "error": self.calibrator.error,
                    "low": self.calibrator.low,
                    "high": self.calibrator.high,
                    "leftMid": self.calibrator.lMid,
                    "rightMid": self.calibrator.rMid,
                    "leftMidVal": self.calibrator.lMidVal,
                    "rightMidVal": self.calibrator.rMidVal,
                    "delta": self.fpsDelta
                }

                self.consoleWriter.display_info(performanceInfo, calibrationInfo)

                if self.infoUploader is not None:
                    self.infoUploader(performanceInfo["time"], performanceInfo["tickRate"])

    def get_ticking_info(self):
        return {
            "ticks": self.processTicks,
            "beginTime": self.beginTime,
            "endTime": self.endTime
        }
