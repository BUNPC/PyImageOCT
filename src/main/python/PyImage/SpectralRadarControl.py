import PySpectralRadar as SpectralRadar
import numpy as np
import numba
from PyQt5.QtCore import QThread
from OCT import all

class FigureEight:

    def __init__(self, plotWidget=None, scatterWidget=None, imageWidget=None, infoWidget=None):

        self.plotWidget = plotWidget
        self.scatterWidget = scatterWidget
        self.liveX = np.arange(1024)
        self.liveY = np.empty(1024)

    def initScan(self):
        print('Init scan')
        pos, X, Y = generateIdealFigureEightPositions
        scatterWidget.plot(X,Y)
        test = PyQtPlot2DThread()
        test.start(self.plotWidget)

    def initAcq(self):
        print('Init acq')

    def abort(self):
        print('Abort')

class PyQtPlot2DThread(QThread):

    def __init__(self):

        QThread.__init__(self)

    def __del__(self):
        self.wait()

    def start(self,plotWidget):
        for i in range(10000):
            liveX = np.arange(1024)
            liveY = np.random.randint(0, 2000, 1024)
            plotWidget.plot(liveX, liveY)

