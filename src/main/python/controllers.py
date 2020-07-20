from PySpectralRadar import PySpectralRadar
import numpy as np
from copy import deepcopy


class Controller:
    """
    Base class for interfacing GUI with OCT hardware.
    """

    def __init__(self):
        pass
        # Initialize self.frame_buffer ringbuffer


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
    Manages key SpectralRadar data and interfaces. The user of the class should never have to call
    SpectralRadar methods directly. Child classes should implement scan pattern and processing controls.
    """
    def __init__(self):

        self.lam_path = 'lam.npy'  # Path to chirp data array in numpy format

        # SpectralRadar handles
        self._config = None
        self._device = None
        self._probe = None
        self._proc = None
        self._scanpattern = None
        self._triggertype = None
        self._acquisitiontype = None
        self._trigger_timeout = None
        self._lam = None  # An array of wavelength data loaded from disk
        self._rawdatahandle = None  # handle for raw data object used during acquisition
        self._rawdatadim = 0  # Size of raw data array

        # Flag set true upon initialization. No two controllers can be online simultaneously.
        self._online = False

    def initialize(self):
        """
        Initializes device, probe, processing device with default settings.
        :return: 0 if successful
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

        # Load chirp data or redownload it from device if it cannot be found
        try:
            self._lam = np.load(self.lam_path)
        except FileNotFoundError:
            self._lam = np.empty(2048)
            for y in np.arange(2048):
                self._lam[y] = PySpectralRadar.getWavelengthAtPixel(self._device, y)
            np.save(self._lam, self.lam_path)

        print('SpectralRadarController: Telesto initialized successfully.')

        self._online = True

        return 0

    def close(self):
        """
        Safely releases most of SpectralRadar object memory.
        :return: 0 if successful
        """
        PySpectralRadar.clearScanPattern(self._scanpattern)  # TODO decice if scan pattern should persist or not
        PySpectralRadar.closeProcessing(self._proc)
        PySpectralRadar.closeProbe(self._probe)
        PySpectralRadar.closeDevice(self._device)

        self._online = False

        return 0

    def set_config(self,config_file_name):
        """
        Sets config file. Note that this will not take effect until the probe is reinitialized
        :param config_file_name: Name of .txt file in the Thorlabs directory to be used
        """
        self._config = config_file_name

    def set_scanpattern(self,scanpatternhandle):
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
        self._scanpattern = PySpectralRadar.createFreeformScanPattern(self._probe, positions, size_x, size_y, apodization)

    def clear_scanpattern(self):
        """
        Clears SpectralRadar scan pattern object.
        """
        PySpectralRadar.clearScanPattern(self._scanpattern)
        self._scanpattern = None

    def start_measurement(self):
        self._rawdatahandle = PySpectralRadar.createRawData()
        PySpectralRadar.startMeasurement(self._device, self._scanpattern, self._acquisitiontype)

    def stop_measurement(self):
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
        return deepcopy(frame)  # TODO determine if this is necessary

    def prescan(self):
        """
        Pre-scan routine which determines necessary buffer size
        :return: Returns the raw data size. It is stored as a private member also, however
        """
        self.start_measurement()
        PySpectralRadar.getRawData(self._device, self._rawdatahandle)
        self._rawdatadim = PySpectralRadar.getRawDatasShape(self._rawdatadim)
        self.stop_measurement()


# class IMAQController(Controller):
#     pass