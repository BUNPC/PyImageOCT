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

        self._prescan()

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

    def _prescan(self):
        """
        Pre-scan routine which determines necessary buffer size
        :return: Returns the raw data size. It is stored as a private member also, however
        """
        self.start_measurement()
        PySpectralRadar.getRawData(self._device, self._rawdatahandle)
        self._rawdatadim = PySpectralRadar.getRawDatasShape(self._rawdatadim)
        self.stop_measurement()

        return self._rawdatadim


class NIController(Controller):

    def __init__(self,
                 camera_name,
                 daq_name,
                 cam_trig_ch_name,
                 x_ch_name,
                 y_ch_name,
                 daq_sample_rate=40000,
                 imaq_buffer_size=32):
        """
        For use with CameraLink line camera controlled via National Instruments IMAQ software (with PyIMAQ
        wrapper) and scan signal output via National Instruments DAQmx software (w/ pynidaqmx wrapper)
        :param camera_name: Name of camera i.e. img0
        :param daq_name: Name of DAQ card for scanning signal output i.e. Dev1
        :param cam_trig_ch_name: Name of channel for line camera triggering
        :param x_ch_name: Name of channel for x galvo
        :param y_ch_name: Name of channel for y galvo
        :param daq_sample_rate: Sample rate for scan samples to be written
        :param imaq_buffer_size: Size of IMAQ's ring buffer
        """
        self._camera_name = camera_name
        self._daq_channel_ids = [
            daq_name + '/' + cam_trig_ch_name,
            daq_name + '/' + x_ch_name,
            daq_name + '/' + y_ch_name
        ]
        self._imaq_buffer_size = imaq_buffer_size
        self._imaq_frame_size = 0
        self._bytes_per_frame = 0
        self._buffer_size_alines = 0
        self._aline_size = 0
        self._daq_sample_rate = daq_sample_rate
        self._scan_task = None
        self._scan_writer = None

        self._cam_trig = []
        self._x = []
        self._y = []

    def initialize(self, scan_pattern=None):
        # Open the camera interface. PyMAQ environment affords only one camera interface at a time

        PyIMAQ.imgShowErrorMsg(PyIMAQ.imgOpen(self._camera_name))
        PyIMAQ.imgShowErrorMsg(PyIMAQ.imgSetAttributeROI(0, 0, self._buffer_size_alines, self._aline_size))
        PyIMAQ.imgShowErrorMsg(PyIMAQ.imgInitBuffer(self._imaq_buffer_size))

        self._aline_size = ALINE_SIZE
        self._imaq_frame_size = PyIMAQ.imgShowErrorMsg(PyIMAQ.imgGetFrameSize())
        self._bytes_per_frame = PyIMAQ.imgShowErrorMsg(PyIMAQ.imgGetBufferSize())

        # Create the DAQmx task
        self._scan_task = nidaqmx.Task()
        for ch_name in self._daq_channel_ids:
            self._scan_task.ao_channels.add_ao_voltage_chan(ch_name)

        self._scan_task.timing.cfg_samp_clk_timing(self._daq_sample_rate,
                                                   source="",
                                                   active_edge=Edge.RISING,  # TODO implemenet parameters
                                                   sample_mode=AcquisitionType.CONTINUOUS)

        self._scan_writer = AnalogMultiChannelWriter(self._scan_task.out_stream)

        print('NIController: IMAQ and DAQmx initialized')
        print('Buffer size init', PyIMAQ.imgGetBufferSize())

        if scan_pattern is not None:
            self.set_scanpattern(scan_pattern)

        if len(self._x) > 0 and len(self._y) > 0 and len(self._cam_trig) > 0:
            self.mode = READY
        else:
            self.mode = NOT_READY

        return 0

    def start_scan(self):
        if len(self._x) == 0 or len(self._y) == 0 or len(self._cam_trig) == 0:
            # No scan pattern defined
            print('NO SCAN PAT', self._cam_trig, self._x)
            self.mode = NOT_READY
            return -1
        else:
            PyIMAQ.imgShowErrorMsg(PyIMAQ.imgStartAcq())
            self._scan_writer.write_many_sample(np.array([4*self._cam_trig,
                                                          0.2*self._x,
                                                          0.2*self._y]))
            self._scan_task.start()

            self._imaq_frame_size = PyIMAQ.imgGetFrameSize()

            self.mode = SCANNING

            return 0

    def stop_scan(self):
        self._scan_task.stop()
        PyIMAQ.imgStopAcq()

        self.mode = READY

        return 0

    def close(self):
        self.stop_scan()
        self._scan_task.close()
        self._scan_task = None
        PyIMAQ.imgShowErrorMsg(PyIMAQ.imgAbortAcq())  # TODO this might fail
        PyIMAQ.imgShowErrorMsg(PyIMAQ.imgClose())

        self.mode = NOT_READY
        return 0

    def set_scanpattern(self, scan_pattern):
        self._cam_trig = scan_pattern.get_trigger()
        self._x = scan_pattern.get_x()
        self._y = scan_pattern.get_y()
        self._daq_sample_rate = scan_pattern.get_sample_rate()
        self._buffer_size_alines = scan_pattern.get_number_of_alines()
        self._reinitialize()

    def grab(self):
        """
        Grabs frame most recently acquired by IMAQ by locking it out briefly and copying it to returned array
        :return: OCT frame, IMAQ buffer number
        """
        if self.mode is SCANNING:  # This acts as an external flag because this method is called from a thread
            self._bytes_per_frame = PyIMAQ.imgGetBufferSize()
            fbuff = np.empty(self._bytes_per_frame, dtype=np.uint16)
            PyIMAQ.imgGetCurrentFrame(fbuff)
            return fbuff

    def configure(self, cfg_path):
        self._reinitialize()  # TODO implemenet configure(cfg)

    def _reinitialize(self):
        rescan = False
        if self.mode is SCANNING:
            self.stop_scan()
            self.mode = NOT_READY
            rescan = True

        PyIMAQ.imgShowErrorMsg(PyIMAQ.imgSetAttributeROI(0, 0, self._buffer_size_alines, self._aline_size))
        self._scan_task.timing.cfg_samp_clk_timing(self._daq_sample_rate,
                                                   source="",
                                                   active_edge=Edge.RISING,  # TODO implemenet parameters
                                                   sample_mode=AcquisitionType.CONTINUOUS)

        if PyIMAQ.imgSessionConfigure() is 0:
            if rescan:
                self.start_scan()  # DAQ scan buffers are updated here
            else:
                self.mode = READY







