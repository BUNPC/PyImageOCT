from PySpectralRadar import PySpectralRadar
from PyIMAQ import *
import nidaqmx
from nidaqmx import _task_modules
from nidaqmx.stream_writers import AnalogMultiChannelWriter
from nidaqmx.constants import LineGrouping, Edge, AcquisitionType
import numpy as np
from copy import deepcopy
from collections import deque


class Controller:
    """
    Base class for interfacing GUI with OCT hardware.
    """

    def __init__(self, buffer_size=256):
        self._buffer = deque(maxlen=buffer_size)

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

    def __init__(self):
        # SpectralRadar handles
        self._config = None
        self._device = None
        self._probe = None
        self._proc = None
        self._scanpattern = None
        self._triggertype = None
        self._acquisitiontype = None
        self._trigger_timeout = None
        self._rawdatahandle = None
        self._rawdatadim = 0  # Size of raw data array

        # Flag set true upon initialization. No two controllers can be online simultaneously.
        self._online = False

    def initialize(self):
        """
        Initializes device, probe, processing device with default settings.
        :return: 0 if successful, -1 otherwise
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

        self._online = True

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

        self._online = False

        return 0

    def configure(self, config_file_name):
        """
        Sets config file. Note that this will not take effect until the probe is reinitialized
        :param config_file_name: Name of .txt file in the Thorlabs directory to be used
        """
        self._config = config_file_name
        self._probe = PySpectralRadar.initProbe(self._device, self._config)
        PySpectralRadar.setCameraPreset(self._device, self._probe, self._proc, 0)  # 0 is the main camera

    def set_scanpattern(self, scanpatternhandle):
        """
        Directly sets the current SpectralRadar scan pattern handle
        :param scanpatternhandle: SpectralRadar scan pattern handle object
        """
        self._scanpattern = scanpatternhandle

    def create_scanpattern(self, positions, size_x, size_y, apodization):
        """
        By default, uses createFreeformScanPattern to generate and store a scan pattern object.
        If a different scan pattern generator function is to be used, override this method or use
        set_scanpattern.
        :return: 0 if successful
        """
        self._scanpattern = PySpectralRadar.createFreeformScanPattern(self._probe, positions, size_x, size_y,
                                                                      apodization)

    def clear_scanpattern(self):
        """
        Clears SpectralRadar scan pattern object.
        """
        PySpectralRadar.clearScanPattern(self._scanpattern)
        self._scanpattern = None

    def start_scan(self):
        self._rawdatahandle = PySpectralRadar.createRawData()
        PySpectralRadar.startMeasurement(self._device, self._scanpattern, self._acquisitiontype)

    def stop_scan(self):
        self._rawdatadim = 0
        PySpectralRadar.stopMeasurement(self._device)
        PySpectralRadar.clearRawData(self._rawdatahandle)

    def grab_rawdata(self):
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
        self._daq_sample_rate = daq_sample_rate
        self._scan_task = None
        self._scan_writer = None

    def initialize(self):
        # Open the camera interface. PyMAQ environment affords only one camera interface at a time
        imgShowErrorMsg(imgOpen(self._camera_name))
        imgShowErrorMsg(imgInitBuffer(self._imaq_buffer_size))
        # TODO buffer size based on scan pattern
        self._imaq_frame_size = imgShowErrorMsg(imgGetFrameSize())
        self._bytes_per_frame = imgShowErrorMsg(imgGetBufferSize())

        # Create the DAQmx task
        self._scan_task = nidaqmx.Task()
        for id in self._daq_channel_ids:
            self._scan_task.ao_channels.add_ao_voltage_chan(id)

        self._scan_task.timing.cfg_samp_clk_timing(self._daq_sample_rate,
                                                   source="",
                                                   active_edge=Edge.RISING,  # TODO implemenet parameters
                                                   sample_mode=AcquisitionType.CONTINUOUS)

        self._scan_writer = AnalogMultiChannelWriter(self._scan_task.out_stream)
