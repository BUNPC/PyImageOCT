import PySpectralRadar as SpectralRadar
import numpy as np
import collections
from PyQt5.QtCore import QObject, QThread, pyqtSignal, pyqtSlot
from PyImage.OCT import *

class FigureEight:

    def __init__(self, plotWidget=None, scatterWidget=None, imageWidget=None, infoWidget=None):

        #GUI Inputs (setters called by update() method of Widgets)
        self._scanPatternSize = None
        self._scanPatternAlinesPerCross = None
        self._scanPatternTotalRepeats = None
        self._fileExperimentName = None
        self._fileExperimentDirectory = None
        self._fileMaxSize = None
        self._fileType = None

        #Scan Pattern
        self.scanPatternPositions = None
        self.scanPatternX = None
        self.scanPatternY = None
        self.scanPatternB1 = None
        self.scanPatternB2 = None
        self.scanPatternN = None
        self.scanPatternD = None

        self.plotWidget = plotWidget
        self.scatterWidget = scatterWidget

        self._rawSpectrum = np.empty(1024)
        self._bScan = None

        self._RAW = collections.deque()

        self.ACTIVE = True

    def initScan(self):

        print('Init scan')
        acquisitionThread = AcquisitionThread(self)

        acq = Acquisition(self,0)
        acq.moveToThread(acquisitionThread)
        acquisitionThread.started.connect(acq.work)
        acquisitionThread.start()

        plotter = PyQtPlotThread(self,self.plotWidget)
        plotter.start()

    def displayPattern(self):
        self.scatterWidget.plot(self.scanPatternY)

    def initAcq(self):
        print('Init acq')

    def abort(self):
        print('Abort')
        self.ACTIVE = False

    def setFileParams(self,experimentDirectory,experimentName,maxSize,fileType):
        self._fileExperimentDirectory = experimentDirectory
        self._fileExperimentName = experimentName
        self._fileMaxSize = maxSize
        self._fileType = fileType

    def setScanPatternParams(self,aLinesPerCross,patternSize,totalSize):
        self._scanPatternAlinesPerCross = aLinesPerCross
        self._scanPatternSize = patternSize
        self._scanPatternTotalRepeats = totalSize

        [self.scanPatternPositions,
         self.scanPatternX,
         self.scanPatternY,
         self.scanPatternB1,
         self.scanPatternB2,
         self.scanPatternN,
         self.scanPatternD] = generateIdealFigureEightPositions(patternSize,aLinesPerCross,rpt=totalSize)

class PyQtPlotThread(QThread):

    def __init__(self,controller,plotWidget):
        QThread.__init__(self)
        self.controller = controller
        self.plotWidget = plotWidget

    def __del__(self):
        self.wait()

    def start(self):
            while self.controller.ACTIVE:
                if len(self.controller._RAW) > 5:
                    Y = self.controller._RAW.popleft()
                    self.plotWidget.plot(Y)

class AcquisitionThread(QThread):

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
                self.controller._RAW.append(np.random.randint(0,100,1024))

    def abort(self):
        self.__abort = True


