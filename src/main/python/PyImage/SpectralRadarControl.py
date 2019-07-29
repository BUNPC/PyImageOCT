import os
import threading
from copy import deepcopy
from queue import Queue, Full

import h5py
from PyQt5.QtWidgets import QWidget, QGridLayout
from pyqtgraph.Qt import QtGui

from src.main.python import PySpectralRadar
from src.main.python.PyImage import Widgets
from src.main.python.PyImage.OCT import *

class FigureEight:

    def __init__(self, parent):

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
        self._scanPatternAngle = None
        self._scanPatternFlybackAngle = None

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

        self._RawQueue = Queue(maxsize=10)
        self._ProcQueue = Queue(maxsize=1000)

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

        # --------------------------------------------------------------------------------------------------------------

        # QWidget for GUI tab
        self.tab = QWidget(parent=parent)
        self.tabGrid = QGridLayout()
        self.tab.setLayout(self.tabGrid)

        # Real-time plot widget for display of raw spectral data
        self.plotSpectrum = Widgets.PlotWidget2D(name="Raw Spectrum", type='curve')
        self.plotSpectrum.setMaximumHeight(250)
        self.tabGrid.addWidget(self.plotSpectrum, 0, 2, 2, 1)
        self.plotSpectrum.setXRange(0, 2048)
        self.plotSpectrum.setYRange(0, 6000)

        # Real-time scatter plot widget for display of scan pattern
        self.plotPattern = Widgets.PlotWidget2D(name="Scan Pattern Preview", type='scatter', aspectLocked=True)
        self.plotPattern.setMaximumHeight(250)
        self.tabGrid.addWidget(self.plotPattern, 0, 3, 2, 1)
        self.plotPattern.labelAxes('mm', '')

        # Real-time image display for B-scan
        self.plotBScan = Widgets.BScanViewer()
        self.tabGrid.addWidget(self.plotBScan, 0, 0, 3, 2)

        # File I/O properties interface
        self.file = Widgets.FileGroupBox('File', self)
        self.tabGrid.addWidget(self.file, 2, 2, 1, 1)

        # Main OCT device settings
        self.params = Widgets.ParamsGroupBox('OCT Imaging Parameters', self)
        self.tabGrid.addWidget(self.params, 3, 2, 2, 1)

        # Fig 8 scan pattern parameters
        self.scanParameters = Widgets.Fig8GroupBox('Scan Pattern', self)
        self.tabGrid.addWidget(self.scanParameters, 2, 3, 3, 1)

        # Motion quant parameters
        self.quantParameters = Widgets.QuantGroupBox('Motion Quantification', self)
        self.tabGrid.addWidget(self.quantParameters, 5, 2, 2, 1)

        # Master scan/acquire/stop buttons
        self.controlButtons = Widgets.ControlGroupBox('Control', self)
        self.tabGrid.addWidget(self.controlButtons, 3, 0, 2, 2)

        # --------------------------------------------------------------------------------------------------------------

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

    def getRawQueue(self):
        return self._RawQueue

    def getProcessingQueue(self):
        return self._ProcQueue

    def setDisplayAxis(self, axis):
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

    def initScan(self):
        print('Init scan')

        self.active = True

        # For scanning, acquisition occurs after each figure-8, so rpt is set to 1
        self.setScanPatternParams(self._scanPatternSize,
                                  self._scanPatternAlinesPerCross,
                                  self._scanPatternAlinesPerFlyback,
                                  1,
                                  self._scanPatternFlybackAngle,
                                  self._scanPatternAngle)

        self.initializeSpectralRadar()
        scan = threading.Thread(target=self.scan)
        disp = threading.Thread(target=self.display)
        self._threads.append(scan)
        self._threads.append(disp)

        for thread in self._threads:
            thread.daemon = True
            thread.start()

    def initAcq(self):
        print('Init acq')

        self.active = True

        self.initializeSpectralRadar()
        acq = threading.Thread(target=self.acquire)
        exp = threading.Thread(target=self.export_npy)
        self._threads.append(acq)
        self._threads.append(exp)

        for thread in self._threads:
            thread.start()

    def process8(self, A, B1, ROI, B2=np.zeros(1)):

        Nx = self._scanPatternAlinesPerCross
        N = self.scanPatternN
        interpIndices = np.linspace(min(self._lam), max(self._lam), 2048)

        if B2.any() != 0:

            processed = np.empty([1024, Nx, 2], dtype=np.complex64)
            Bs = [B1, B2]

            for b in range(len(Bs)):
                B = Bs[b]
                interpolated = np.empty([2048, Nx])
                preprocessed = preprocess8(A, N, B, Nx, self.getApodWindow())

                for n in np.arange(Nx):
                    k = interp1d(self._lam, preprocessed[:, n])
                    interpolated[:, n] = k(interpIndices)
                    processed[:, n, b] = np.fft.ifft(interpolated[:, n])[0:1024].astype(np.complex64)

        else:

            processed = np.zeros([1024, Nx], dtype=np.complex64)

            interpolated = np.empty([2048, Nx])
            preprocessed = preprocess8(A, N, B1, Nx, self.getApodWindow())

            for n in np.arange(Nx):
                k = interp1d(self._lam, preprocessed[:, n])
                interpolated[:, n] = k(interpIndices)
                processed[:, n] = np.fft.ifft(interpolated[:, n])[1024:2048].astype(np.complex64)

        return processed[ROI[0]:ROI[1], :]

    def display(self):

        running = True
        processingQueue = self.getProcessingQueue()
        Bs = [self.scanPatternB1, self.scanPatternB2]

        while running and self.active:
            B = Bs[self._displayAxis]
            try:
                raw = processingQueue.get()
                spec = raw.flatten()[0:2048]  # First spectrum of the B-scan only is plotted

                bscan = self.process8(raw, B, ROI=(620, 1020))

                self.plotWidget.plot1D(spec)
                self.imageWidget.update(20 * np.log10(np.abs(np.transpose(bscan))))
                QtGui.QGuiApplication.processEvents()

            except Full:
                pass

    def scan(self):

        running = True
        processingQueue = self.getProcessingQueue()
        counter = 0

        # Set number of frames to process based on predicted speed
        interval = 30

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

                    new = deepcopy(temp)

                    try:

                        processingQueue.put(new)

                    except Full:

                        pass

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

            new = deepcopy(temp)

            try:

                rawQueue.put(new)

            except Full:

                pass

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
        try:
            os.mkdir(self._fileExperimentDirectory)
        except FileExistsError:
            pass
        root = self.getFilepath() + '.npy'
        out = np.empty([1024, self._scanPatternAlinesPerCross, 2, self._scanPatternTotalRepeats],
                       dtype=np.complex64)  # TODO: implement max file size

        for i in np.arange(self._scanPatternTotalRepeats):
            temp = q.get()

            bscan = self.process8(temp, self.scanPatternB1, ROI=(0, 1024), B2=self.scanPatternB2)

            out[:, :, :, i] = bscan

        np.save(root, out)
        print('Saving .npy complete')
        self.abort()

    def abort(self):
        print('Abort')  # TODO different function for mid-acq abort vs end of acquisition. Also write a safer one
        if self.active:
            self.active = False
            for thread in self._threads:
                thread._is_running = False
            self._threads = []
            self._RawQueue = Queue()
            self._ProcQueue = Queue()
            self.stopMeasurement()
            self.closeSpectralRadar()

    def setFileParams(self, experimentDirectory, experimentName, maxSize, fileType):
        self._fileExperimentDirectory = experimentDirectory
        self._fileExperimentName = experimentName
        self._fileMaxSize = maxSize
        self._fileType = fileType

    def getFilepath(self):
        return self._fileExperimentDirectory + '/' + self._fileExperimentName

    def setDeviceParams(self, rate, config):
        self._imagingRate = rate
        self._config = config

    def clearScanPattern(self):
        PySpectralRadar.clearScanPattern(self._scanPattern)

    def getScanPattern(self):
        return self._scanPattern

    def getAlinesPerX(self):
        return self._scanPatternAlinesPerCross

    def updateScanPattern(self):
        self._scanPattern = PySpectralRadar.createFreeformScanPattern(self._probe,
                                                                      self.scanPatternPositions,
                                                                      self.scanPatternN,
                                                                      1,  # All repeating patterns handled with loops!
                                                                      False)

        PySpectralRadar.rotateScanPattern(self._scanPattern, self._scanPatternAngle)

    def setScanPatternParams(self, patternSize, aLinesPerCross, aLinesPerFlyback, repeats, angle, flybackAngle):
        self._scanPatternSize = patternSize
        self._scanPatternAlinesPerCross = aLinesPerCross
        self._scanPatternAlinesPerFlyback = aLinesPerFlyback
        self._scanPatternTotalRepeats = repeats
        self._scanPatternAngle = angle
        self._scanPatternFlybackAngle = flybackAngle

        [self.scanPatternPositions,
         self.scanPatternX,
         self.scanPatternY,
         self.scanPatternB1,
         self.scanPatternB2,
         self.scanPatternN,
         self.scanPatternD] = generateIdealFigureEightPositions(patternSize,
                                                                aLinesPerCross,
                                                                rpt=1,  # All repeating patterns handled with loops!
                                                                flyback=aLinesPerFlyback,
                                                                flybackAngle=flybackAngle)

    def displayPattern(self):
        self.plotPattern.plot2D(self.scanPatternX, self.scanPatternY)
