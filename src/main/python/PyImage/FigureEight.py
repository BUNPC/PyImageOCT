import threading

from PyImage.processeight import ProcessEight

from PyQt5.QtWidgets import QWidget, QGridLayout

from src.main.python.PyImage import Widgets
from src.main.python.PyImage.OCT import *
from src.main.python.PySpectralRadar import PySpectralRadar


class FigureEight:

    def __init__(self, parent):

        # File params
        self._file_experimentname = None
        self._file_experimentdirectory = None
        self._file_maxsize = None
        self._filetype = None

        # Scan pattern params
        self._scanpattern_size = None
        self._scanpattern_aperb = None  # A-lines per B-scan after padding
        self._scanpattern_aperx = None  # A-lines per B-scan before padding
        self._scanpattern_aperflyback = None
        self._scanpattern_rpt = None
        self._scanpattern_angle = None
        self._scanpattern_fbangle = None

        # Scan geometry
        self.scanpattern_positions = None
        self.scanpattern_x = None
        self.scanpattern_y = None
        self.scanpattern_b1 = None
        self.scanpattern_b2 = None
        self.scanpattern_n = None
        self.scanpattern_d = None

        # ROI
        self._roi_z = (None, None)

        # Device config
        self._ratevalue = 76000  # Rate in hz. NOT FUNCTIONAL
        self._rateenum = 0
        self._config = "ProbeLKM10-LV"  # TODO un-hardcode default
        self._apodwindow = None
        self._displayaxis = 0

        # SpectralRadar handles
        self._device = None
        self._probe = None
        self._proc = None
        self._scanpattern = None
        self._triggertype = None
        self._acquisitiontype = None
        self._trigger_timeout = None
        self._lam = None  # An array of wavelength data loaded from disk

        # OS
        self._threads = []
        self.active = False
        self.Processing = None  # ProcessEight object

        # Qt
        self._widgets = []

        # ------------------------------------------------------------------------------------------------------------------

        # QWidget for GUI tab
        self.tab = QWidget(parent=parent)
        self.tabGrid = QGridLayout()
        self.tab.setLayout(self.tabGrid)

        # Real-time plot widget for display of raw spectral data
        self.plotSpectrum = Widgets.PlotWidget2D(name="Raw Spectrum", type='curve')
        self.plotSpectrum.setMaximumHeight(250)
        self.tabGrid.addWidget(self.plotSpectrum, 0, 2, 2, 1)
        self._widgets.append(self.plotSpectrum)
        self.plotSpectrum.labelAxes('Wavelength', 'ADU')
        self.plotSpectrum.setXRange(0, 2048)
        self.plotSpectrum.setYRange(0, 4500)

        # Real-time scatter plot widget for display of scan pattern
        self.plotPattern = Widgets.PlotPatternWidget(name="Scan Pattern")
        self.plotPattern.setMaximumHeight(250)
        self.tabGrid.addWidget(self.plotPattern, 0, 3, 2, 1)
        self._widgets.append(self.plotPattern)
        self.plotPattern.labelAxes('mm', '')

        # Real-time image display for B-scan
        self.plotBScan = Widgets.BScanViewer()
        self.tabGrid.addWidget(self.plotBScan, 0, 0, 3, 2)
        self._widgets.append(self.plotBScan)

        # File I/O properties interface
        self.groupFile = Widgets.FileGroupBox('File', self)
        self.tabGrid.addWidget(self.groupFile, 2, 2, 1, 1)
        self._widgets.append(self.groupFile)

        # Main OCT device settings
        self.groupParams = Widgets.ParamsGroupBox('OCT Imaging Parameters', self)
        self.tabGrid.addWidget(self.groupParams, 3, 2, 2, 1)
        self._widgets.append(self.groupParams)

        # Fig 8 scan pattern parameters
        self.groupScanParams = Widgets.Fig8GroupBox('Scan Pattern', self)
        self.tabGrid.addWidget(self.groupScanParams, 2, 3, 3, 1)
        self._widgets.append(self.groupScanParams)

        # Motion quant parameters
        self.groupQuantParams = Widgets.QuantGroupBox('Motion Quantification', self)
        self.tabGrid.addWidget(self.groupQuantParams, 5, 3, 2, 1)
        self._widgets.append(self.groupQuantParams)

        # Progress bar
        self.progressBar = Widgets.ProgressWidget(self)
        self.tabGrid.addWidget(self.progressBar, 3, 0, 1, 2)

        # Master scan/acquire/stop buttons
        self.controlButtons = Widgets.ControlGroupBox('Control', self)
        self.tabGrid.addWidget(self.controlButtons, 4, 0, 2, 2)
        self._widgets.append(self.controlButtons)

        # ------------------------------------------------------------------------------------------------------------------

        # Setup

        self.start()  # Comment out for offline testing

    def start(self):
        init = threading.Thread(target=self.initialize_spectralradar())
        init.start()
        init.join()

    def initialize_spectralradar(self):  # TODO Implement on/off switch or splash while loading
        for widget in self._widgets:
            widget.enabled(False)
        self.progressBar.setText('Init device')
        self._device = PySpectralRadar.initDevice()
        self.progressBar.setProgress(2)
        self.progressBar.setText('Init probe')
        self._probe = PySpectralRadar.initProbe(self._device, self._config)
        self.progressBar.setProgress(4)
        self._proc = PySpectralRadar.createProcessingForDevice(self._device)
        self.progressBar.setText('Init camera')
        PySpectralRadar.setCameraPreset(self._device, self._probe, self._proc, 0)  # 0 is the main camera
        self._triggertype = PySpectralRadar.Device_TriggerType.Trigger_FreeRunning  # Default
        self._trigger_timeout = 5  # Number from old labVIEW program
        self.progressBar.setProgress(6)
        self._acquisitiontype = PySpectralRadar.AcquisitionType.Acquisition_AsyncContinuous
        PySpectralRadar.setTriggerMode(self._device, self._triggertype)
        PySpectralRadar.setTriggerTimeoutSec(self._device, self._trigger_timeout)
        self._update_scanpattern()
        self.progressBar.setProgress(7)
        self.progressBar.setText('Loading chirp')
        try:
            self._lam = np.load('lam.npy')
        except FileNotFoundError:
            self.progressBar.setText('Chirp not found')
            self._lam = np.empty(2048)
            for y in np.arange(2048):
                self._lam[y] = PySpectralRadar.getWavelengthAtPixel(self._device, y)
            np.save('lam', self._lam)
        self.progressBar.setProgress(10)
        self.progressBar.setText('Done!')
        print('Telesto initialized successfully.')
        for widget in self._widgets:
            widget.enabled(True)
        self.progressBar.setProgress(0)
        self.progressBar.setText('Ready')

    def close_spectralradar(self):
        """
        Safely releases SpectralRadar objects
        """
        PySpectralRadar.clearScanPattern(self._scanpattern)
        PySpectralRadar.closeProcessing(self._proc)
        PySpectralRadar.closeProbe(self._probe)
        PySpectralRadar.closeDevice(self._device)

    def abort(self):
        """
        Stops scanning and re-enables GUI.  TODO: Make GUI manipulation thread-safe
        """
        print('Abort')

        if self.active:

            self.active = False

            for widget in self._widgets:
                widget.enabled(True)

        self.progressBar.setText('Stopped')
        self.progressBar.setProgress(0)

    def close_window(self):
        """
        Convenience function for closing of window
        """
        print('Close')
        self.abort()
        self.close_spectralradar()

    def init_scan(self):
        print('Init scan')

        processing = ProcessEight(self)

        processing.start_preprocessing(n=3)

    def init_acquisition(self):
        print('Init acq')

        pass

    def init_tracking(self):
        print('Init tracking')

        pass

    # Misc getters and setters

    def set_config(self, config):
        configLUT = {
            "10X": "ProbeLKM10-LV",
            "5X": "ProbeLKM05-LV",
            "2X": "LSM02-LV"
        }

        self.close_spectralradar()
        self._config = configLUT[config]
        self.initialize_spectralradar()

        print('config changed')

    def set_rate(self, rate):
        rateLUT = {
            "76 kHz": 0,
            "146 kHz": 1
        }
        values = [76000, 146000]  # Hz
        self._rateenum = rateLUT[rate]
        self._ratevalue = values[self._rateenum]

        self.groupScanParams.update()

        PySpectralRadar.setCameraPreset(self._device, self._probe, self._proc, self._rateenum)

    def get_ratevalue(self):
        return self._ratevalue

    def get_triggertype(self):
        return self._triggertype

    def get_acquisitiontype(self):
        return self._acquisitiontype

    def set_displayaxis(self, axis):
        self._displayaxis = axis

    def set_apodwindow(self, window):
        self._apodwindow = window

    def get_apodwindow(self):
        return self._apodwindow

    def get_lambda(self):
        return self._lam

    def set_roi(self, axial):
        self._roi_z = axial

    def set_file_params(self, directory, name, maxsize, filetype):
        self._file_experimentdirectory = directory
        self._file_experimentname = name
        self._file_maxsize = maxsize
        self._filetype = filetype

    def get_filepath(self):
        return self._file_experimentdirectory + '/' + self._file_experimentname

    def get_scanpattern(self):
        return self._scanpattern

    def get_aperb(self):
        return self._scanpattern_aperb

    def get_aperx(self):
        return self._scanpattern_aperx

    def set_scanpatternparams(self, d, aperx, b_padding, aperflyback, repeats, angle, flybackangle):
        self._scanpattern_size = d
        self._scanpattern_aperx = aperx
        self._scanpattern_aperb = aperx - b_padding  # Padding subtracted here
        self._scanPatternBPadding = b_padding
        self._scanpattern_aperflyback = aperflyback
        self._scanpattern_rpt = repeats
        self._scanpattern_angle = angle
        self._scanpattern_fbangle = flybackangle

        [self.scanpattern_positions,
         self.scanpattern_x,
         self.scanpattern_y,
         self.scanpattern_b1,
         self.scanpattern_b2,
         self.scanpattern_n,
         self.scanpattern_d] = generate_figure8(d,
                                                aperx,
                                                padB=b_padding,
                                                rpt=1,  # All repeating patterns handled with loops!
                                                angle=angle,
                                                flyback=aperflyback,
                                                flybackangle=flybackangle)

    def display_pattern(self):
        self.plotPattern.plotFigEight(self.scanpattern_x[np.invert(self.scanpattern_b1 + self.scanpattern_b2)],
                                      self.scanpattern_y[np.invert(self.scanpattern_b1 + self.scanpattern_b2)],
                                      self.scanpattern_x[self.scanpattern_b1 + self.scanpattern_b2],
                                      self.scanpattern_y[self.scanpattern_b1 + self.scanpattern_b2])

    def _update_scanpattern(self):
        self._scanpattern = PySpectralRadar.createFreeformScanPattern(self._probe,
                                                                      self.scanpattern_positions,
                                                                      self.scanpattern_n,
                                                                      1,  # All repeating patterns handled with loops!
                                                                      False)

    def _clearScanPattern(self):
        PySpectralRadar.clearScanPattern(self._scanpattern)

    '''
    The following methods are deprecated and to be replaced with thread objects defined elsewhere
    '''

    # def display(self):
    #
    #     running = True
    #     processingQueue = self.getProcessingQueue()
    #     Bs = [self.scanpattern_b1, self.scanpattern_b2]
    #
    #     while running and self.active:
    #         B = Bs[self._displayaxis]
    #         try:
    #             raw = processingQueue.get()
    #             spec = raw.flatten()[0:2048]  # First spectrum of the B-scan only is plotted
    #
    #             bscan = self.process8(raw, B, ROI=self._roi_z)
    #
    #             self.plotSpectrum.plot1D(spec)
    #             self.plotBScan.update(20 * np.log10(np.abs(np.transpose(bscan))))
    #             QtGui.QGuiApplication.processEvents()
    #
    #         except Full:
    #             pass

    # def scan(self,acq=False):
    #
    #     self.progress.setText('Scanning...')
    #
    #     rawDataHandle = PySpectralRadar.createRawData()
    #
    #     self.startMeasurement()
    #
    #     counter = 0
    #     acquired = 0  # Only stepped if acquisition argument is true
    #
    #     while self.active and acquired < self._scanPatternTotalRepeats:
    #
    #         self.getRawData(rawDataHandle)
    #
    #         dim = PySpectralRadar.getRawDataShape(rawDataHandle)
    #
    #         temp = np.empty(dim, dtype=np.uint16)
    #
    #         PySpectralRadar.copyRawDataContent(rawDataHandle, temp)
    #
    #         if np.size(temp) > 0:
    #
    #             new = deepcopy(temp)
    #
    #             try:
    #
    #                 self.Processing.put_frame(new)
    #
    #             except Full:
    #
    #                 pass
    #
    #         counter += 1
    #         if acq:
    #             acquired += 1
    #
    #     self.stopMeasurement()
    #     PySpectralRadar.clearRawData(rawDataHandle)

    # Wrappers for SpectralRadar functions that call controller members

    def _startMeasurement(self):
        PySpectralRadar.startMeasurement(self._device, self._scanpattern, self._acquisitiontype)

    def _stopMeasurement(self):
        PySpectralRadar.stopMeasurement(self._device)

    def _setComplexDataOutput(self, complexDataHandle):
        PySpectralRadar.setComplexDataOutput(self._proc, complexDataHandle)

    def _getRawData(self, rawDataHandle):
        PySpectralRadar.getRawData(self._device, rawDataHandle)
