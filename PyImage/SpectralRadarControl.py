import PySpectralRadar
import numpy as np
from queue import Queue
from PyQt5.QtCore import QObject, QThread, pyqtSignal, pyqtSlot
from PyImage.OCT import *

TRUE = PySpectralRadar.TRUE
FALSE = PySpectralRadar.FALSE

class FigureEight:

    def __init__(self, plotWidget=None, scatterWidget=None, imageWidget=None, infoWidget=None):

        # Arguments
        self.plotWidget = plotWidget
        self.scatterWidget = scatterWidget

        # File params
        self._fileExperimentName = None
        self._fileExperimentDirectory = None
        self._fileMaxSize = None
        self._fileType = None

        # Scan pattern params
        self._scanPatternSize = None
        self._scanPatternAlinesPerCross = None
        self._scanPatternTotalRepeats = None

        # Scan geometry
        self.scanPatternPositions = None
        self.scanPatternX = None
        self.scanPatternY = None
        self.scanPatternB1 = None
        self.scanPatternB2 = None
        self.scanPatternN = None
        self.scanPatternD = None

        # Device config
        self._imagingRate = 76000 # Rate in hz. NOT FUNCTIONAL
        self._config = "Probe" #For offline testing ONLY

        self.active = False

        self._RawQueue = Queue()
        self._ProcQueue = Queue()

        # SpectralRadar handles
        self._device = None
        self._probe = None
        self._proc = None
        self._scanPattern = None
        self._triggerType = None
        self._acquisitionType = None
        self._triggerTimeout = None

    def initializeSpectralRadar(self):
        self._device = PySpectralRadar.initDevice()
        self._probe = PySpectralRadar.initProbe(self._device,self._config)
        self._proc = PySpectralRadar.createProcessingForDevice(self._device)
        PySpectralRadar.setCameraPreset(self._device,self._probe,self._proc,0) # 0 is the main camera
        self._triggerType = PySpectralRadar.Device_TriggerType.Trigger_FreeRunning # Default
        self._triggerTimeout = 5 # Number from old labVIEW program
        self._acquisitionType = PySpectralRadar.AcquisitionType.Acquisition_AsyncContinuous
        PySpectralRadar.setTriggerMode(self._device,self._triggerType)
        PySpectralRadar.setTriggerTimeoutSec(self._device,self._triggerTimeout)
        self.updateScanPattern()
        print('Telesto initialized successfully.')

    def closeSpectralRadar(self):
        PySpectralRadar.closeDevice(self._device)
        PySpectralRadar.closeProcessing(self._proc)
        PySpectralRadar.closeProbe(self._probe)
        PySpectralRadar.clearScanPattern(self._scanPattern)

    def startMeasurement(self):
        PySpectralRadar.startMeasurement(self._device,self._scanPattern,self._acquisitionType)

    def setComplexDataOutput(self,complexDataHandle):
        PySpectralRadar.setComplexDataOutput(self._proc,complexDataHandle)

    def getRawData(self,rawDataHandle):
        PySpectralRadar.getRawData(self._device,rawDataHandle)

    def stopMeasurement(self):
        PySpectralRadar.stopMeasurement(self._device)

    def getTriggerType(self):
        return self._triggerType

    def getAcquisitionType(self):
        return self._acquisitionType

    def updateScanPattern(self):
        n = len(self.scanPatternX)*self._scanPatternTotalRepeats
        self._scanPattern =  PySpectralRadar.createFreeformScanPattern(self._probe,self.scanPatternPositions,n,1,FALSE)

    def getScanPattern(self):
       return self._scanPattern

    def getRawQueue(self):
        return self._RawQueue

    def getProcessingQueue(self):
        return self._ProcQueue

    def getRate(self):
        return self._imagingRate

    def initScan(self):

        print('Init scan')

        self.active = True

        # For scanning, acquisition occurs after each figure-8, so rpt is set to 1
        self.controller.setScanPatternParams(self._scanPatternSize,
                                             self._scanPatternAlinesPerCross,
                                             self._scanPatternAlinesPerFlyback,
                                             1)

        acquisitionThread = AcquisitionThread(self)
        acq = Acquisition(self,0)
        acq.moveToThread(acquisitionThread)
        acquisitionThread.started.connect(acq.work)
        acquisitionThread.start()

    def displayPattern(self):
        self.scatterWidget.plot2D(self.scanPatternX,self.scanPatternY)

    def initAcq(self):
        print('Init acq')

    def abort(self):
        print('Abort')
        self.active = False
        self.abortSpectralRadar()

    def setFileParams(self,experimentDirectory,experimentName,maxSize,fileType):
        self._fileExperimentDirectory = experimentDirectory
        self._fileExperimentName = experimentName
        self._fileMaxSize = maxSize
        self._fileType = fileType

    def setDeviceParams(self,rate,config):
        self._imagingRate = rate
        self._config = config

    def setScanPatternParams(self,patternSize,aLinesPerCross,aLinesPerFlyback,repeats):
        self._scanPatternSize = patternSize
        self._scanPatternAlinesPerCross = aLinesPerCross
        self._scanPatternAlinesPerFlyback = aLinesPerFlyback
        self._scanPatternTotalRepeats = repeats

        [self.scanPatternPositions,
         self.scanPatternX,
         self.scanPatternY,
         self.scanPatternB1,
         self.scanPatternB2,
         self.scanPatternN,
         self.scanPatternD] = generateIdealFigureEightPositions(patternSize,aLinesPerCross,flyback=aLinesPerFlyback,rpt=repeats)

class AcquisitionThread(QThread):
    """
    PySpectralRadar acquisition thread for use with PyQt5
    """
    def __init__(self,controller):
        QThread.__init__(self)
        self.controller = controller
        self.controller.initializeSpectralRadar()

    def __del__(self):
        self.wait()

class Acquisition(QObject):

    def __init__(self,controller,id=0):
        super().__init__()
        self.__id = id
        self.__abort = False
        self.controller = controller
        self.rawQueue = controller.getRawQueue()
        self.processingQueue = controller.getProcessingQueue()
        self.counter = 0

    @pyqtSlot()
    def work(self):

        while self.controller.active:

            thread_name = QThread.currentThread().objectName()
            thread_id = int(QThread.currentThreadId())  # cast to int() is necessary

            self.controller.startMeasurement()

            rawDataHandle = PySpectralRadar.createRawData()
            self.controller.getRawData(rawDataHandle)
            dim = PySpectralRadar.getRawDataShape(rawDataHandle)
            temp = np.empty(dim,dtype=np.uint16)

            PySpectralRadar.copyRawDataContent(rawDataHandle,temp)
            if np.size(temp) > 0:
                self.rawQueue.put(np.squeeze(temp))
                if self.counter % 10 == 0:
                    self.processingQueue.put(np.squeeze(temp))
            PySpectralRadar.clearRawData(rawDataHandle) # Might nix queued data, not sure

            self.controller.stopMeasurement()

    def abort(self):
        self.__abort = True

class DisplayBScanThread(QThread):
    """
    PySpectralRadar B-scan display thread for use with PyQt5
    """
    def __init__(self,controller):
        QThread.__init__(self)
        self.controller = controller

    def __del__(self):
        self.wait()

class DisplayBScan(QObject):

    def __init__(self,controller,id=0):
        super().__init__()
        self.__id = id
        self.__abort = False
        self.controller = controller

    @pyqtSlot()
    def work(self):

        while self.controller.active:

            thread_name = QThread.currentThread().objectName()
            thread_id = int(QThread.currentThreadId())  # cast to int() is necessary

    def abort(self):
        self.__abort = True
