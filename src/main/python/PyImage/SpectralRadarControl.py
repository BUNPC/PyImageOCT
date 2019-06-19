import PySpectralRadar as SpectralRadar
import numpy as np
from PyQt5.QtCore import QThread

class FigureEight:

    def __init__(self,display):

        self.display = display
        self.liveX = np.arange(1024)
        self.liveY = np.empty(1024)

    def initScan(self):
        print('Init scan')
        test = PyQtPlot2DThread()
        test.start(self.display)

    def initAcq(self):
        print('Init acq')

    def abort(self):
        print('Abort')

class PyQtPlot2DThread(QThread):

    def __init__(self):

        QThread.__init__(self)

    def __del__(self):
        self.wait()

    def start(self,display):
        for i in range(10000):
            liveX = np.arange(1024)
            liveY = np.random.randint(0, 2000, 1024)
            display.plot2D(liveX, liveY)

