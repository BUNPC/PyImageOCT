import PySpectralRadar as SpectralRadar
import numpy as np
from PyQt5.QtCore import QThread
from PyImage.OCT import *

class FigureEight:

    def __init__(self, plotWidget=None, scatterWidget=None, imageWidget=None, infoWidget=None):

        self.plotWidget = plotWidget
        self.scatterWidget = scatterWidget
        self.liveX = np.arange(1024)
        self.liveY = np.empty(1024)

        self.__RUNNING__ = True

    def initScan(self):
        print('Init scan')
        test = PyQtPlot2DThread(self)
        test.start(self.plotWidget)

    def displayPattern(self):
        self.scatterWidget.plot(self.X, self.Y)

    def initAcq(self):
        print('Init acq')

    def abort(self):
        print('Abort')
        self.__RUNNING__ = False

class PyQtPlot2DThread(QThread):

    def __init__(self,controller):

        QThread.__init__(self)

        self.controller = controller

    def __del__(self):
        self.wait()

    def start(self,plotWidget):
        for i in range(10000):
            while self.controller.__RUNNING__:
                liveX = np.arange(1024)
                liveY = np.random.randint(0, 2000, 1024)
                plotWidget.plot(liveX, liveY)

