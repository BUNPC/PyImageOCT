import PySpectralRadar
import numpy as np

class SpectralRadarController:
    """
    Manages key SpectralRadar data and interfaces. The user of the class should never have to call
    SpectralRadar methods directly. Child classes should implement scan pattern and processing controls.
    """
    def __init__(self, default_probe_config='ProbeLKM10-LV'):

        self.lam_path = 'lam.npy'  # Path to chirp data array in numpy format

        # SpectralRadar handles
        self._config = default_probe_config

        self._device = None
        self._probe = None
        self._proc = None
        self._scanpattern = None
        self._triggertype = None
        self._acquisitiontype = None
        self._trigger_timeout = None
        self._lam = None  # An array of wavelength data loaded from disk
        self._rawdatahandle = None  # handle for raw data object used during acquisition

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

        print('SpectralRadarController: Telesto initialized successfully.')

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
        :param scanpatternhandle:
        """
        self._scanpattern = scanpatternhandle

    def create_scanpattern(self):
        """
        By default, uses createFreeformScanPattern to generate and store a scan pattern object.
        If a different scan pattern generator function is to be used, override this method or use
        set_scanpattern.
        :return: 0 if successful
        """


    def clear_scanpattern(self):
        """
        Clears SpectralRadar scan pattern object.
        """
        PySpectralRadar.clearScanPattern(self._scanpattern)