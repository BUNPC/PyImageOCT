from src.main.python import PySpectralRadar
from queue import Queue
import threading
from PyQt5.QtCore import QObject, QThread, pyqtSlot

from src.main.python.PyImage.OCT import *
from copy import deepcopy
import h5py
from pathlib import Path

TRUE = True
FALSE = False


class FigureEight:

    def __init__(self, plotWidget=None, scatterWidget=None, imageWidget=None, infoWidget=None):
        # Arguments/child widgets
        self.plotWidget = plotWidget
        self.scatterWidget = scatterWidget
        self.imageWidget = imageWidget

        # Control widgets
        self.controlWidget = None

        # File params
        self._fileExperimentName = None
        self._fileExperimentDirectory = None
        self._fileMaxSize = None
        self._fileType = None

        # Scan pattern params
        self._scanPatternSize = None
        self._scanPatternAlinesPerCross = None
        self._scanPatternAlinesPerFlyback = None
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
        self._imagingRate = 76000  # Rate in hz. NOT FUNCTIONAL
        self._config = "ProbeLKM10-LV"  # TODO implement as real parameter from GUI
        self._apodWindow = None
        self._displayAxis = 0

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
        self._lam = None

        self._threads = []

    def initializeSpectralRadar(self):  # TODO Need to thread this eventually, long hang time for GUI
        self._device = PySpectralRadar.initDevice()
        self._probe = PySpectralRadar.initProbe(self._device, self._config)
        self._proc = PySpectralRadar.createProcessingForDevice(self._device)
        PySpectralRadar.setCameraPreset(self._device, self._probe, self._proc, 0)  # 0 is the main camera
        self._triggerType = PySpectralRadar.Device_TriggerType.Trigger_FreeRunning  # Default
        self._triggerTimeout = 5  # Number from old labVIEW program
        self._acquisitionType = PySpectralRadar.AcquisitionType.Acquisition_AsyncContinuous
        PySpectralRadar.setTriggerMode(self._device, self._triggerType)
        PySpectralRadar.setTriggerTimeoutSec(self._device, self._triggerTimeout)
        self.updateScanPattern()
        try:
            self._lam = np.load('lam.npy')
        except FileNotFoundError:
            self._lam = np.empty(2048)
            for y in np.arange(2048):
                self._lam[y] = PySpectralRadar.getWavelengthAtPixel(self._device, y)
            np.save('lam', self._lam)

        print('Telesto initialized successfully.')

    def closeSpectralRadar(self):
        PySpectralRadar.clearScanPattern(self._scanPattern)
        PySpectralRadar.closeProcessing(self._proc)
        PySpectralRadar.closeProbe(self._probe)
        PySpectralRadar.closeDevice(self._device)

    def startMeasurement(self):
        PySpectralRadar.startMeasurement(self._device, self._scanPattern, self._acquisitionType)

    def setComplexDataOutput(self, complexDataHandle):
        PySpectralRadar.setComplexDataOutput(self._proc, complexDataHandle)

    def getRawData(self, rawDataHandle):
        PySpectralRadar.getRawData(self._device, rawDataHandle)

    def stopMeasurement(self):
        PySpectralRadar.stopMeasurement(self._device)

    def getTriggerType(self):
        return self._triggerType

    def getAcquisitionType(self):
        return self._acquisitionType

    def getFilepath(self):
        return self._fileExperimentDirectory

    def getRawQueue(self):
        return self._RawQueue

    def getProcessingQueue(self):
        return self._ProcQueue

    def setDisplayAxis(self,axis):
        self._displayAxis = axis

    def setRate(self, rate):
        self._imagingRate = rate

    def getRate(self):
        return self._imagingRate

    def setApodWindow(self, window):
        self._apodWindow = window

    def getApodWindow(self):
        return self._apodWindow

    def getLambda(self):
        return self._lam

    def setConfig(self, config):
        self._config = config

    def setControlWidget(self, controlWidget):
        self.controlWidget = controlWidget

    def disableControlWidget(self):
        self.controlWidget.enabled(False)

    def enableControlWidget(self):
        self.controlWidget.enabled(True)

    def initScan(self):
        print('Init scan')

        self.active = True
        self.disableControlWidget()

        # For scanning, acquisition occurs after each figure-8, so rpt is set to 1
        self.setScanPatternParams(self._scanPatternSize,
                                  self._scanPatternAlinesPerCross,
                                  self._scanPatternAlinesPerFlyback,
                                  1,
                                  self._scanPatternAngle)

        self.initializeSpectralRadar()
        scan = threading.Thread(target=self.scan)
        disp = threading.Thread(target=self.display)
        self._threads.append(scan)
        self._threads.append(disp)

        for thread in self._threads:
            thread.start()

    def initAcq(self):
        print('Init acq')

        self.active = True
        self.disableControlWidget()

        self.initializeSpectralRadar()
        acq = threading.Thread(target=self.acquire)
        exp = threading.Thread(target=self.export_npy)
        self._threads.append(acq)
        self._threads.append(exp)

        for thread in self._threads:
            thread.start()

    def process8(self, A, B1, B2=None, ROI=np.arange(14,400)):

        Nx = self._scanPatternAlinesPerCross
        N = self.scanPatternN
        interpIndices = np.linspace(min(self._lam),max(self._lam),2048)

        if B2 != None:

            processed = np.empty([1024,Nx,2], dtype=np.complex64)
            Bs = [B1,B2]

            for b in range(len(Bs)):
                B = Bs[b]
                interpolated = np.empty([2048, Nx])
                preprocessed = preprocess8(A,N,B,Nx,self.getApodWindow())

                for n in np.arange(Nx):

                    k = interp1d(self._lam,preprocessed)
                    interpolated[:,n] = k(interpIndices)
                    processed[:,n,b] = np.fft.ifft(interpolated[:,n])[0:1024].astype(np.complex64)

        else:

            processed = np.empty([1024,Nx], dtype=np.complex64)

            interpolated = np.empty([2048, Nx])
            preprocessed = preprocess8(A, N, B1, Nx, self.getApodWindow())

            for n in np.arange(Nx):
                k = interp1d(self._lam, preprocessed)
                interpolated[:, n] = k(interpIndices)
                processed[:, n] = np.fft.ifft(interpolated[:, n])[0:1024].astype(np.complex64)

        return processed

    def display(self):

            running = True
            self.imageWidget.initialize()
            processingQueue = self.getProcessingQueue()
            # Loads necessary scan pattern properties for data processing
            N = self.scanPatternN
            Bs = [self.scanPatternB1,self.scanPatternB2]
            B = Bs[self._displayAxis]

            AperX = self._scanPatternAlinesPerCross

            while running and self.active:
                raw = processingQueue.get()
                spec = raw.flatten()[0:2048]  # First spectrum of the B-scan only is plotted

                bscan = fig8ToBScan(raw,
                                    N,
                                    B,
                                    AperX,
                                    self.getApodWindow(),
                                    ROI=400,
                                    lam=self.getLambda())

                self.plotWidget.plot1D(spec)
                self.imageWidget.update(20*np.log10(np.abs(bscan)))

    def scan(self):

        running = True
        processingQueue = self.getProcessingQueue()
        counter = 0

        # Set number of frames to process based on predicted speed
        if self._scanPatternAlinesPerCross > 80:
            interval = 30
        elif self._scanPatternAlinesPerCross < 10:
            interval = 10
        else:
            interval = 20

        rawDataHandle = PySpectralRadar.createRawData()

        self.getRawData(rawDataHandle)

        self.startMeasurement()

        while running and self.active:

            self.getRawData(rawDataHandle)

            dim = PySpectralRadar.getRawDataShape(rawDataHandle)

            temp = np.empty(dim, dtype=np.uint16)

            PySpectralRadar.copyRawDataContent(rawDataHandle, temp)

            if np.size(temp) > 0:

                if counter % interval == 0:
                    processingQueue.put(deepcopy(temp))

            counter += 1

        self.stopMeasurement()
        PySpectralRadar.clearRawData(rawDataHandle)

    def acquire(self):

        rawQueue = self.getRawQueue()

        rawDataHandle = PySpectralRadar.createRawData()

        self.getRawData(rawDataHandle)

        self.startMeasurement()

        for i in np.arange(self._scanPatternTotalRepeats):
            self.getRawData(rawDataHandle)

            dim = PySpectralRadar.getRawDataShape(rawDataHandle)

            temp = np.empty(dim, dtype=np.uint16)

            PySpectralRadar.copyRawDataContent(rawDataHandle, temp)

            rawQueue.put(temp)

            del temp

        self.stopMeasurement()
        PySpectralRadar.clearRawData(rawDataHandle)

        print('Acquisition complete')

    def export_hdf(self):  # TODO fix this

        q = self.getRawQueue()

        root = h5py.File(self.getFilepath(), 'w')

        root.create_group("scan")
        root.create_dataset("scan/positions", data=np.concatenate([self.scanPatternX, self.scanPatternY]))
        root.create_dataset("scan/N", data=self.scanPatternN)
        root.create_dataset("scan/D", data=self.scanPatternD)

        rawshape = [2048, self._scanPatternAlinesPerCross, 2, self._scanPatternTotalRepeats]
        raw = root.create_dataset("raw", rawshape, dtype=np.uint16)

        while not q.empty():

            for i in np.arange(self._scanPatternTotalRepeats):
                temp = q.get()

                raw[:, :, :, i] = reshape8(temp,
                                           self.scanPatternN,
                                           self._scanPatternAlinesPerCross,
                                           self.scanPatternB1,
                                           self.scanPatternB2)

        root.close()
        print('Saving .hdf complete')

    def export_npy(self):

        q = self.getRawQueue()
        root = self.getFilepath() + '.npy'
        out = np.empty([2048,self._scanPatternAlinesPerCross,2,self._scanPatternTotalRepeats],dtype=np.uint16)  # TODO: implement max file size

        for i in np.arange(self._scanPatternTotalRepeats):

            temp = q.get()

            reshaped = reshape8(temp,
                                self.scanPatternN,
                                self._scanPatternAlinesPerCross,
                                self.scanPatternB1,
                                self.scanPatternB2)

            out[:,:,:,i] = reshaped

        np.save(root,out)
        print('Saving .npy complete')
        self.abort()

    def abort(self):
        print('Abort') # TODO different function for mid-acq abort vs end of acquisition
        self.stopMeasurement()
        for thread in self._threads:
            thread._is_running = False
        self._threads = []
        self.active = False
        self.enableControlWidget()
        self.closeSpectralRadar()

    def setFileParams(self, experimentDirectory, experimentName, maxSize, fileType):
        self._fileExperimentDirectory = experimentDirectory
        self._fileExperimentName = experimentName
        self._fileMaxSize = maxSize
        self._fileType = fileType

    def setDeviceParams(self, rate, config):
        self._imagingRate = rate
        self._config = config

    def clearScanPattern(self):
        PySpectralRadar.clearScanPattern(self._scanPattern)

    def getScanPattern(self):
        return self._scanPattern

    def updateScanPattern(self):
        self._scanPattern = PySpectralRadar.createFreeformScanPattern(self._probe,
                                                                      self.scanPatternPositions,
                                                                      self.scanPatternN,
                                                                      1,  # All repeating patterns handled with loops!
                                                                      False)

        PySpectralRadar.rotateScanPattern(self._scanPattern, self._scanPatternAngle)

    def setScanPatternParams(self, patternSize, aLinesPerCross, aLinesPerFlyback, repeats, angle):
        self._scanPatternSize = patternSize
        self._scanPatternAlinesPerCross = aLinesPerCross
        self._scanPatternAlinesPerFlyback = aLinesPerFlyback
        self._scanPatternTotalRepeats = repeats
        self._scanPatternAngle = angle

        [self.scanPatternPositions,
         self.scanPatternX,
         self.scanPatternY,
         self.scanPatternB1,
         self.scanPatternB2,
         self.scanPatternN,
         self.scanPatternD] = generateIdealFigureEightPositions(patternSize,
                                                                aLinesPerCross,
                                                                rpt=1,  # All repeating patterns handled with loops!
                                                                flyback=aLinesPerFlyback)

    def displayPattern(self):
        self.scatterWidget.plot2D(self.scanPatternX, self.scanPatternY)
