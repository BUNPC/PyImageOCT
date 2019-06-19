import PySpectralRadar as SpectralRadar
import numpy as np
import collections
from PyQt5.QtCore import QObject, QThread, pyqtSignal, pyqtSlot
from PyImage.OCT import *

class FigureEight:

    def __init__(self, plotWidget=None, scatterWidget=None, imageWidget=None, infoWidget=None):

        self.plotWidget = plotWidget
        self.scatterWidget = scatterWidget
        self.liveX = np.arange(1024)
        self.liveY = np.empty(1024)

        self.__RUNNING__ = True
        self.__RAW__ = collections.deque()

    def initScan(self):

        print('Init scan')
        acquisitionThread = acqThread(self)

        acq = Acquisition(self,0)
        acq.moveToThread(acquisitionThread)
        acquisitionThread.started.connect(acq.work)
        acquisitionThread.start()

        plotter = PyQtPlot2DThread(self)
        plotter.start(self.plotWidget)

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
            while self.controller.__RUNNING__:
                if len(self.controller.__RAW__) > 5:
                    Y = self.controller.__RAW__.popleft()
                    self.controller.plotWidget.plot(np.arange(1024),Y)

class acqThread(QThread):

    def __init__(self,controller):
        QThread.__init__(self)
        self.controller = controller

    def __del__(self):
        self.wait()


class Acquisition(QObject):

    def __init__(self,controller,id: int):
        super().__init__()
        self.controller = controller
        self.__id = id
        self.__abort = False

    @pyqtSlot()
    def work(self):
        thread_name = QThread.currentThread().objectName()
        thread_id = int(QThread.currentThreadId())  # cast to int() is necessary
        for i in range(5000):
            while not self.__abort:
                self.controller.__RAW__.append(np.random.randint(0,100,1024))

    def abort(self):
        self.__abort = True


