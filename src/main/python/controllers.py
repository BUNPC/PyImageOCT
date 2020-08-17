import time

from PySpectralRadar import PySpectralRadar
import nidaqmx
from nidaqmx import _task_modules
from nidaqmx.stream_writers import AnalogMultiChannelWriter
from nidaqmx.constants import LineGrouping, Edge, AcquisitionType
import numpy as np
from copy import deepcopy
from collections import deque
from PyIMAQ import PyIMAQ
from PyScanPattern import ScanPattern
import numba

import matplotlib.pyplot as plt

# Size of line camera
ALINE_SIZE = 2048

# Controller modes
SCANNING = 1
READY = 0
NOT_READY = -1


class Controller:
    """
    Base class for interfacing GUI with OCT hardware.
    """

    def initialize(self):
        """
        Allocate memory and initialize objects for control of hardware
        :return: 0 on success
        """
        raise NotImplementedError()

    def close(self):
        """
        Close interface objects and free memory
        :return: 0 on success
        """
        raise NotImplementedError()

    def start_scan(self):
        """
        Launch a thread which sets up and starts scanning, acquisition, fill frame_buffer
        :return: 0 on success
        """
        raise NotImplementedError()

    def grab(self):
        """
        Grab a frame and return it
        :return: OCT data
        """

    def stop_scan(self):
        """
        Stop the scan and acquisition thread
        :return: 0 on success
        """
        raise NotImplementedError()

    def configure(self, cfg_path):
        """
        Load a .cfg file by name and use it to configure API
        :return: 0 on success
        """
        raise NotImplementedError()

    def set_scanpattern(self, scan_pattern):
        raise NotImplementedError()
        """
        Takes a scan pattern object and configures scanning system
        """


class SpectralRadarController:
    """
    Interfaces with SpectralRadar API for control of Thorlabs OCT systems
    """

    def __init__(self, cfg=None):
        # SpectralRadar handles
        self._config = cfg
        self._device = None
        self._probe = None
        self._proc = None
        self._scanpattern = None
        self._triggertype = None
        self._acquisitiontype = None
        self._trigger_timeout = None
        self._rawdatahandle = None
        self._rawdatadim = 0  # Size of raw data array

        self.mode = NOT_READY

    def initialize(self):
        """
        Initializes device, probe, processing device with default settings.
        :return: 0 if successful, -1 on fail
        """
        self._device = PySpectralRadar.initDevice()
        self._probe = PySpectralRadar.initProbe(self._device, self._config)
        self._proc = PySpectralRadar.createProcessingForDevice(self._device)
        PySpectralRadar.setCameraPreset(self._device, self._probe, self._proc, 0)  # 0 is the main camera
        self._triggertype = PySpectralRadar.Device_TriggerType.Trigger_FreeRunning  # Default
        self._trigger_timeout = 5  # Number from old labVIEW program
        self._acquisitiontype = PySpectralRadar.AcquisitionType.Acquisition_AsyncContinuous
        PySpectralRadar.setTriggerMode(self._device, self._triggertype)
        PySpectralRadar.setTriggerTimeoutSec(self._device, self._trigger_timeout)

        print('SpectralRadarController: Telesto initialized successfully.')
        if self._scanpattern is not None:
            self.mode = READY
        else:
            self.mode = NOT_READY

        return 0

    def close(self):
        """
        Safely releases most of SpectralRadar object memory.
        :return: 0 if successful
        """
        PySpectralRadar.clearScanPattern(self._scanpattern)
        PySpectralRadar.closeProcessing(self._proc)
        PySpectralRadar.closeProbe(self._probe)
        PySpectralRadar.closeDevice(self._device)
        self.mode = NOT_READY
        return 0

    def configure(self, config_file_name):
        """
        Sets .cfg file by name (located in Thorlabs directory) and reinitializes probe
        :param config_file_name: Name of .txt file in the Thorlabs directory to be used
        :return: 0 if successful
        """
        self._config = config_file_name
        self._probe = PySpectralRadar.initProbe(self._device, self._config)
        PySpectralRadar.setCameraPreset(self._device, self._probe, self._proc, 0)  # 0 is the main camera
        return 0

    def set_scanpattern(self, scanpatternhandle):
        """
        Directly sets the current SpectralRadar scan pattern handle
        :param scanpatternhandle: SpectralRadar scan pattern handle object
        :return: 0 if successful
        """
        self._scanpattern = scanpatternhandle
        return 0

    def create_freeform_scanpattern(self, positions, size_x, size_y, apodization):
        """
        By default, uses createFreeformScanPattern to generate and store a scan pattern object.
        Returns a handle to it also
        :return: Handle to the scanpattern object if successful
        """
        self._scanpattern = PySpectralRadar.createFreeformScanPattern(self._probe, positions, size_x, size_y,
                                                                      apodization)
        return self._scanpattern

    def clear_scanpattern(self):
        """
        Clears SpectralRadar scan pattern object.
        :return: 0 if successful
        """
        PySpectralRadar.clearScanPattern(self._scanpattern)
        self._scanpattern = None

        return 0

    def start_scan(self):
        """
        Begins scanning, launches frame grab thread
        :return: 0 if successfully started scanning
        """
        self._rawdatahandle = PySpectralRadar.createRawData()
        PySpectralRadar.startMeasurement(self._device, self._scanpattern, self._acquisitiontype)

        self.mode = SCANNING

        return 0

    def stop_scan(self):
        """
        Stops scanning, stops frame grab thread
        :return: 0 if successful
        """
        self._rawdatadim = 0
        PySpectralRadar.stopMeasurement(self._device)
        PySpectralRadar.clearRawData(self._rawdatahandle)

        self.mode = READY

        return 0

    def grab(self):
        """
        Grabs a raw data frame from the current Telesto device
        :return: numpy array of frame. Memory managed by Python
        """
        PySpectralRadar.getRawData(self._device, self._rawdatahandle)
        frame = np.empty(self._rawdatadim, dtype=np.uint16)
        PySpectralRadar.copyRawDataContent(self._rawdatahandle, frame)
        return frame


class NIController(Controller):

    def __init__(self,
                 camera_name,
                 daq_name,
                 cam_trig_ch_name,
                 x_ch_name,
                 y_ch_name,
                 dac_sample_rate=40000,
                 imaq_buffer_size=32):
        """
        For use with CameraLink line camera controlled via National Instruments IMAQ software (with PyIMAQ
        wrapper) and scan signal output via National Instruments DAQmx software (w/ pynidaqmx wrapper)
        :param camera_name: Name of camera i.e. img0
        :param daq_name: Name of DAQ card for scanning signal output i.e. Dev1
        :param cam_trig_ch_name: Name of channel for line camera triggering
        :param x_ch_name: Name of channel for x galvo
        :param y_ch_name: Name of channel for y galvo
        :param dac_sample_rate: Sample rate for scan samples to be written
        :param imaq_buffer_size: Size of IMAQ's ring buffer
        """
        super().__init__()
        self._camera_name = camera_name
        self._daq_channel_ids = [
            daq_name + '/' + cam_trig_ch_name,
            daq_name + '/' + x_ch_name,
            daq_name + '/' + y_ch_name
        ]
        self._imaq_buffer_size = imaq_buffer_size
        self._dac_sample_rate = dac_sample_rate
        self._bytes_per_frame = 0
        self._frame_size = 0
        self._buffer_size_alines = 0
        self._buffer_size_blines = 0
        self._buffer_size_total = 0
        self._scan_task = None
        self._timing = None
        self._scan_writer = None

        # TODO implement calibration params
        self._max_galvo_voltage = 4  # Volts
        self._trigger_gain = -2
        self._x_volts_to_mm = 1 / 0.092 * 1 / 1.056  # ~92 um/V, sq aspect  (calibrated 8/6/2020)
        self._y_volts_to_mm = 1 / 0.092 * 1 / 1.288  # ~92 um/V, sq aspect

        self._cam_trig = []  # Camera trigger pulse train
        self._x = []  # Slow axis galvo signal
        self._y = []  # Fast axis galvo signal
        self._dc = np.zeros(ALINE_SIZE, dtype=np.float)  # Reference spectrum

        self.mode = NOT_READY

    def initialize(self, scanpattern=None):

        if scanpattern is not None:
            print('Initializing with scan pattern')
            self.set_scanpattern(scanpattern)

        # Open the camera interface. PyMAQ environment affords only one camera interface at a time
        PyIMAQ.imgShowErrorMsg(PyIMAQ.imgOpen(self._camera_name))
        start = time.time()

        print((0, 0, self._buffer_size_alines, ALINE_SIZE))
        PyIMAQ.imgShowErrorMsg(PyIMAQ.imgSetAttributeROI(0, 0, self._buffer_size_alines, ALINE_SIZE))
        PyIMAQ.imgShowErrorMsg(PyIMAQ.imgInitBuffer(self._imaq_buffer_size))

        self._bytes_per_frame = PyIMAQ.imgShowErrorMsg(PyIMAQ.imgGetBufferSize())
        self._frame_size = PyIMAQ.imgGetFrameSize()  # Should be same as bytes per frame / 2 for uint16 data

        elapsed = time.time() - start
        print('NIController: Initialized camera', elapsed, 's')

        print('NIController: Buffer size:', int(PyIMAQ.imgGetBufferSize() / 2))

        start = time.time()
        # Create the DAQmx task
        self._scan_task = nidaqmx.Task()
        self._timing = nidaqmx.task.Timing(self._scan_task)

        for ch_name in self._daq_channel_ids:
            self._scan_task.ao_channels.add_ao_voltage_chan(ch_name)

        self._scan_writer = AnalogMultiChannelWriter(self._scan_task.out_stream)

        elapsed = time.time() - start
        print('NIController: DAQmx initialized', elapsed, 's')

        # Once IMAQ stuff, scan task and scan writer are set up, prescan to acquire reference spectrum
        self._prescan()

        self._scan_task.timing.cfg_samp_clk_timing(self._dac_sample_rate,
                                                   source="",
                                                   active_edge=Edge.RISING,
                                                   sample_mode=AcquisitionType.CONTINUOUS)
        self.mode = READY

        return 0

    def start_scan(self):
        if len(self._x) == 0 or len(self._y) == 0 or len(self._cam_trig) == 0:
            # No scan pattern defined
            print('NIController: Cannot start scanning without a scan pattern!')
            self.mode = NOT_READY
            return -1
        else:
            # Begin scan

            self._write_scansignal(np.array([-self._trigger_gain * np.array(self._cam_trig),
                                             self._x_volts_to_mm * self._x,
                                             self._y_volts_to_mm * self._y]))

            PyIMAQ.imgShowErrorMsg(PyIMAQ.imgStartAcq())

            self._scan_task.start()

            self._bytes_per_frame = PyIMAQ.imgGetBufferSize()
            self._frame_size = PyIMAQ.imgGetFrameSize()  # Should be same as bytes per frame / 2 for uint16 data

            self.mode = SCANNING

            return 0

    def stop_scan(self):
        start = time.time()
        self._scan_task.stop()
        print('NIController: DAQmx task stopped elapsed', time.time() - start)
        PyIMAQ.imgShowErrorMsg(PyIMAQ.imgStopAcq())
        print('NIController: IMAQ acq stopped elapsed', time.time() - start)
        self.mode = READY

        return 0

    def close(self):
        self.stop_scan()
        self._scan_task.close()
        self._scan_task = None
        PyIMAQ.imgShowErrorMsg(PyIMAQ.imgStopAcq())  # TODO this might fail
        PyIMAQ.imgShowErrorMsg(PyIMAQ.imgClose())

        self.mode = NOT_READY
        return 0

    def set_scanpattern(self, scanpattern):
        self._cam_trig = scanpattern.get_trigger()  # TODO ensure proper polarity
        self._x = scanpattern.get_x()
        self._y = scanpattern.get_y()
        self._dac_sample_rate = scanpattern.get_sample_rate()
        self._buffer_size_alines = scanpattern.get_raster_dimensions()[0]  # A-lines per B
        self._buffer_size_blines = scanpattern.get_raster_dimensions()[1]  # B-lines per C
        self._buffer_size_total = self._buffer_size_alines * self._buffer_size_blines
        return 0

    def set_scan_scale(self, scanpattern):
        self._cam_trig = scanpattern.get_trigger()
        self._x = scanpattern.get_x()
        self._y = scanpattern.get_y()
        self._write_scansignal(np.array([-self._trigger_gain * np.array(self._cam_trig),
                                         self._x_volts_to_mm * self._x,
                                         self._y_volts_to_mm * self._y]))

    def grab_current(self):
        """
        Grabs frame most recently acquired by IMAQ by locking it out briefly and copying it to returned array
        :return: OCT frame, IMAQ buffer number
        """
        fbuff = np.empty(self._frame_size, dtype=np.uint16)
        PyIMAQ.imgGetCurrentFrame(fbuff)
        return fbuff

    def grab(self, buffer_ids, buffer_ids_len):
        """
        Grabs the frames by id listed in buffer_ids and returns 2D array with buffers along first axis and
        buffer numbers along 2nd axis
        :return: OCT frame, IMAQ buffer number
        """
        fbuff = np.empty(self._frame_size * buffer_ids_len, dtype=np.uint16)
        for i, bid in enumerate(buffer_ids):
            PyIMAQ.imgCopyBuffer(bid, fbuff[i * self._frame_size:i * self._frame_size + self._frame_size])
        return fbuff

    def configure(self, cfg_path):
        self._reinitialize()  # TODO implemenet configure(cfg)

    def get_dc(self):
        return self._dc.astype(np.float32)

    def _prescan(self):
        # Prescan

        MAX_POS = 4  # volts

        PyIMAQ.imgShowErrorMsg(PyIMAQ.imgStartAcq())

        start = time.time()
        print('Prescanning...')

        self._scan_task.timing.cfg_samp_clk_timing(self._dac_sample_rate,
                                                   sample_mode=AcquisitionType.FINITE)

        # Ramp galvo to corner
        self._write_scansignal(np.array([np.zeros(int(self._dac_sample_rate / 4)),
                                         np.linspace(0, MAX_POS, int(self._dac_sample_rate / 4)),
                                         np.linspace(0, MAX_POS, int(self._dac_sample_rate / 4))]))
        self._scan_task.start()
        self._scan_task.wait_until_done()
        self._scan_task.stop()

        # Acquire fully vignetted image
        self._scan_task.timing.cfg_samp_clk_timing(self._dac_sample_rate,
                                                   sample_mode=AcquisitionType.CONTINUOUS)

        self._write_scansignal(np.array([-self._trigger_gain * np.array(self._cam_trig),
                                         MAX_POS * np.ones(len(self._cam_trig)),
                                         MAX_POS * np.ones(len(self._cam_trig))]))
        self._scan_task.start()

        time.sleep(1)  # Galvos settling time before frame grab

        # Acquire reference/dc spectra
        dc_buffer = self.grab(np.arange(self._buffer_size_blines), self._buffer_size_blines)
        # dc_buffer = self.grab_current()
        dc_alines = np.split(dc_buffer, self._buffer_size_alines * self._buffer_size_blines)
        self._dc = np.mean(dc_alines, axis=0).astype(np.float)

        self._scan_task.stop()
        print('Grabbed reference spectra...')

        self._scan_task.timing.cfg_samp_clk_timing(self._dac_sample_rate,
                                                   sample_mode=AcquisitionType.FINITE)

        # Ramp galvo to center
        self._write_scansignal(np.array([np.zeros(int(self._dac_sample_rate / 4)),
                                         np.linspace(MAX_POS, 0, int(self._dac_sample_rate / 4)),
                                         np.linspace(MAX_POS, 0, int(self._dac_sample_rate / 4))]))
        self._scan_task.start()
        self._scan_task.wait_until_done()
        self._scan_task.stop()

        print('DC spectrum acquired via prescan routine elapsed', time.time() - start)

        # Stop the prescan acquisition
        PyIMAQ.imgShowErrorMsg(PyIMAQ.imgStopAcq())

    def _write_scansignal(self, scansignal3d):
        if np.max(np.abs(scansignal3d)) > self._max_galvo_voltage:
            print('NIController: Cannot exceed user-defined maximum galvo voltage of', self._max_galvo_voltage, 'V !')
            return -1
        else:
            self._scan_writer.write_many_sample(scansignal3d)
