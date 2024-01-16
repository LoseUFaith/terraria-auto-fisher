import threading
from collections import deque

import numpy as np
from PyQt5.QtGui import QColor
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

from pyqtgraph import PlotWidget, mkPen, InfiniteLine
from PyQt5.QtCore import Qt

from itertools import islice


class PlotDrawer(FigureCanvas):
    def __init__(self, maxDataSize, style, scale, xLength=None, yRange=None):
        self.xData = deque(maxlen=maxDataSize)
        self.yData = deque(maxlen=maxDataSize)
        self.style = style
        self.scale = scale
        self.yRange = yRange
        self.xLength = xLength

        self.fig = Figure(figsize=scale)
        self.ax = self.fig.add_subplot(111)
        super(PlotDrawer, self).__init__(self.fig)

        self.updated = threading.Event()
        self.dataPoolSize = 8
        self.dataPool = deque(maxlen=self.dataPoolSize)

    def add_data(self, dataX, dataY):
        self.dataPool.append((dataX, dataY))

        if len(self.dataPool) == self.dataPoolSize:
            meanX = sum([data[0] for data in self.dataPool]) / self.dataPoolSize
            meanY = sum([data[1] for data in self.dataPool]) / self.dataPoolSize
            self.xData.append(meanX)
            self.yData.append(meanY)

            self.dataPool.clear()
            self.updated.set()

    def update_plot(self):
        if not self.updated.is_set():
            return
        self.updated.clear()

        if len(self.xData) == 0:
            return
        self.ax.cla()
        self.ax.plot(self.xData, self.yData, self.style)
        self.ax.axhline(66, color='g', linestyle='dashed')
        self.ax.axhline(60, color='r', linestyle='dashed')
        self.ax.axhline(1, color='y', linestyle='dashed')
        if self.yRange:
            self.ax.set_ylim(self.yRange)
        else:
            self.ax.set_ylim([None, None])

        if self.xLength:
            self.ax.set_xlim([self.xData[-1] - self.xLength, self.xData[-1]])
        else:
            self.ax.set_xlim([None, None])


class QtPlotDrawer(PlotWidget):
    def __init__(self, maxDataSize, style, scale, xLength=None, yRange=None):
        super().__init__(background='w')

        self.xData = deque(maxlen=maxDataSize)
        self.yData = deque(maxlen=maxDataSize)
        self.style = style
        self.scale = scale
        self.yRange = yRange
        self.xLength = xLength

        self.setYRange(yRange[0], yRange[1])

        self.raw = self.plot(self.xData, self.yData, pen=mkPen(QColor(Qt.darkBlue), width=2))
        # self.ma5 = self.plot(self.xData, self.yData, pen=mkPen(QColor(Qt.darkRed), width=2))

        self.addItem(InfiniteLine(pos=1, angle=0, pen=mkPen(QColor(Qt.darkGreen), width=2, style=Qt.DashLine)))

    def add_data(self, dataX, dataY):
        self.xData.append(dataX)
        self.yData.append(dataY)

        self.update_plot()

    def update_plot(self):
        self.raw.setData(self.xData, self.yData)

        # ret = np.cumsum(self.yData, dtype=float)
        # ret[5:] = ret[5:] - ret[:-5]
        # ma5 = ret[4:] / 5
        #
        # self.ma5.setData(list(islice(self.xData, 4, len(self.xData))), ma5)
        # super().setXRange(self.xData[-1] - self.xLength, self.xData[-1])
