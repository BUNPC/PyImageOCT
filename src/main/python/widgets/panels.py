import glob
import os
from datetime import datetime

from PyQt5 import uic
from PyQt5.QtCore import pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import QGroupBox, QLineEdit, QComboBox, QToolButton, QFileDialog, QSpinBox, QDoubleSpinBox, \
    QCheckBox, QPushButton

FILETYPES = [
    ".npy",
    ".mat"
]

FILESIZES = [
    "250 MB",
    "500 MB",
    "1 GB",
    "2 GB",
    "4 GB"
]

RATES = {
    "76 kHz": 76000,
    "146 kHz": 146000
}

# ControlPanel modes
BUSY = -1
IDLE = 0
SCANNING = 1
ACQUIRING = 2


class ControlPanel(QGroupBox):
    """
    Can go from IDLE into SCANNING or ACQUIRING, and from SCANNING into ACQUIRING. Can only go from BUSY to IDLE
    """

    def __init__(self):
        super(QGroupBox, self).__init__()
        ui = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) + "\\ui\\control.ui"
        uic.loadUi(ui, self)

        self._scan_button = self.findChild(QPushButton, "pushScan")
        self._acq_button = self.findChild(QPushButton, "pushAcquire")
        self._stop_button = self.findChild(QPushButton, "pushStop")

        self._buttons = [self._scan_button, self._acq_button, self._stop_button]

        self._scan_button.released.connect(self._scan_released)
        self._acq_button.released.connect(self._acq_released)
        self._stop_button.released.connect(self._stop_released)

        # Public
        self.mode = IDLE

    def connect_to_scan(self, slot):
        self._scan_button.released.connect(slot)

    def connect_to_acq(self, slot):
        self._acq_button.released.connect(slot)

    def connect_to_stop(self, slot):
        self._stop_button.released.connect(slot)

    def set_busy(self):
        """
        Disables GUI entirely
        :return: 0 on success
        """
        self.mode = BUSY
        for button in self._buttons:
            button.setEnabled(False)
        return 0

    def set_idle(self):
        """
        GUI is ready to begin another scan/acq session
        :return: 0 on success
        """
        self.mode = IDLE
        self._scan_button.setEnabled(True)
        self._acq_button.setEnabled(True)
        self._stop_button.setEnabled(False)
        return 0

    def _scan_released(self):
        self._set_scanning()

    def _acq_released(self):
        self._set_acquiring()

    def _stop_released(self):
        # Parent must reenable GUI when processing/saving/displaying is complete
        self.set_busy()

    def _set_scanning(self):
        self.mode = SCANNING
        self._scan_button.setEnabled(False)
        self._acq_button.setEnabled(True)
        self._stop_button.setEnabled(True)

    def _set_acquiring(self):
        self.mode = ACQUIRING
        self._scan_button.setEnabled(True)
        self._acq_button.setEnabled(False)
        self._stop_button.setEnabled(True)


class ScanPanelOCTA(QGroupBox):

    changed = pyqtSignal()

    def __init__(self):

        super(QGroupBox, self).__init__()
        ui = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) + "\\ui\\scan_octa.ui"  # Double escape dir
        uic.loadUi(ui, self)

        self.indefinite_check = self.findChild(QCheckBox, "checkIndefinite")
        self.indefinite_check.stateChanged.connect(self._indefinite_check_changed)

        self.equal_aspect_check = self.findChild(QCheckBox, "checkEqualAspect")
        self.equal_aspect_check.stateChanged.connect(self._equal_aspect_check_changed)

        self.scan_number_spin = self.findChild(QSpinBox, "spinScanNumber")

        self.x_roi_spin = self.findChild(QDoubleSpinBox, "spinROIWidth")
        self.x_count_spin = self.findChild(QSpinBox, "spinACount")
        self.x_spacing_spin = self.findChild(QDoubleSpinBox, "spinFastAxisSpacing")

        self.x_roi_spin.valueChanged.connect(self._roi_changed)
        self.x_count_spin.valueChanged.connect(self._count_changed)
        self.x_spacing_spin.valueChanged.connect(self._x_spacing_changed)
        self.x_spacing_spin.valueChanged.connect(self._spacing_changed)

        self.y_roi_spin = self.findChild(QDoubleSpinBox, "spinROIHeight")
        self.y_count_spin = self.findChild(QSpinBox, "spinBCount")
        self.y_spacing_spin = self.findChild(QDoubleSpinBox, "spinSlowAxisSpacing")

        self.y_roi_spin.valueChanged.connect(self._roi_changed)
        self.y_spacing_spin.valueChanged.connect(self._spacing_changed)
        self.y_count_spin.valueChanged.connect(self._count_changed)

        self.preview_button = self.findChild(QPushButton, "previewButton")
        self.commit_button = self.findChild(QPushButton, "commitButton")

    def _count_changed(self):
        # Need to block signals so that update functions arent recursive
        self.x_roi_spin.blockSignals(True)
        self.y_roi_spin.blockSignals(True)

        try:
            self.x_roi_spin.setValue((self.x_spacing_spin.value() / 1000) * (self.x_count_spin.value() - 0))
            self.y_roi_spin.setValue((self.y_spacing_spin.value() / 1000) * (self.y_count_spin.value() - 0))
        except ZeroDivisionError:
            pass

        # Unblock them
        self.x_roi_spin.blockSignals(False)
        self.y_roi_spin.blockSignals(False)
        self.changed.emit()

    def _spacing_changed(self):
        self.x_roi_spin.blockSignals(True)
        self.y_roi_spin.blockSignals(True)

        try:
            self.x_roi_spin.setValue((self.x_spacing_spin.value() / 1000) * (self.x_count_spin.value() - 0))
            self.y_roi_spin.setValue((self.y_spacing_spin.value() / 1000) * (self.y_count_spin.value() - 0))
        except ZeroDivisionError:
            pass

        self.x_roi_spin.blockSignals(False)
        self.y_roi_spin.blockSignals(False)
        self.changed.emit()

    def _roi_changed(self):
        self.x_spacing_spin.blockSignals(True)
        self.y_spacing_spin.blockSignals(True)

        try:
            self.x_spacing_spin.setValue((self.x_roi_spin.value() * 1000) / self.x_count_spin.value())
            self.y_spacing_spin.setValue((self.y_roi_spin.value() * 1000) / self.y_count_spin.value())
        except ZeroDivisionError:
            pass

        self.x_spacing_spin.blockSignals(False)
        self.y_spacing_spin.blockSignals(False)
        self.changed.emit()

    def _indefinite_check_changed(self):
        if self.indefinite_check.isChecked():
            self.scan_number_spin.setEnabled(False)
        else:
            self.scan_number_spin.setEnabled(True)
        self.changed.emit()

    def _equal_aspect_check_changed(self):
        if self.equal_aspect_check.isChecked():
            self.y_spacing_spin.setValue(self.x_spacing_spin.value())
            self.y_spacing_spin.setEnabled(False)
        else:
            self.y_spacing_spin.setEnabled(True)
        self.changed.emit()

    def _x_spacing_changed(self):
        if self.equal_aspect_check.isChecked():
            self.y_spacing_spin.setValue(self.x_spacing_spin.value())


class ConfigPanel(QGroupBox):

    def __init__(self):
        super(QGroupBox, self).__init__()
        ui = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) + "\\ui\\config.ui"  # Double escape dir
        uic.loadUi(ui, self)

        self.configdir = "C:\\ThorLabs\\SpectralRadar\\config"  # TODO set this intelligently on startup
        self.configpaths = glob.glob(self.configdir + "/*.ini")
        print(self.configpaths)

        self.config_combo = self.findChild(QComboBox, "comboConfig")
        for path in self.configpaths:
            self.config_combo.addItem(os.path.basename(path).split(".")[0])  # Just get name of file w/o extension

        self.rate_combo = self.findChild(QComboBox, "comboRate")
        self.apod_combo = self.findChild(QComboBox, "comboApodization")

        self.bitness_check = self.findChild(QCheckBox, "check32")
        self.fft_check = self.findChild(QCheckBox, "checkFFT")
        self.interp_check = self.findChild(QCheckBox, "checkInterpolation")

    def get_proc_stream(self):
        """
        Returns a list of 3 booleans: [fft, interp, 32bit or 64bit]
        """
        return [self.fft_check.checked(), self.interp_check.checked(), self.bitness_check.checked()]

    def get_config(self):
        return self.config_combo.text()

    def get_rate(self):
        return RATES[self.rate_combo.text()]

    def get_apod(self):
        return self.apod_combo.text()


class RepeatsPanel(QGroupBox):

    def __init__(self):

        super(QGroupBox, self).__init__()
        ui = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) + "\\ui\\repeats.ui"  # Double escape dir
        uic.loadUi(ui, self)

        self.a_repeat_spin = self.findChild(QSpinBox, "spinARepeat")
        self.b_repeat_spin = self.findChild(QSpinBox, "spinBRepeat")
        self.avg_check = self.findChild(QCheckBox, "checkAveraging")

    def get_a_repeat(self):

        if self.isEnabled():
            return self.a_repeat_spin.value()
        else:
            return 1

    def get_b_repeat(self):

        if self.isEnabled():
            return self.b_repeat_spin.value()
        else:
            return 1

    def averaging(self):

        if self.isEnabled():
            return self.avg_check.checked()
        else:
            return False


class FilePanel(QGroupBox):

    def __init__(self):
        super(QGroupBox, self).__init__()

        ui = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) + "\\ui\\filePanel.ui"  # Double escape dir
        uic.loadUi(ui, self)

        self.exp_dir_line = self.findChild(QLineEdit, "lineExp")
        self.trial_name_line = self.findChild(QLineEdit, "lineFileName")
        self.file_type_combo = self.findChild(QComboBox, "comboFileType")
        self.file_size_combo = self.findChild(QComboBox, "comboFileSize")

        self.file_browse_button = self.findChild(QToolButton, "buttonBrowse")
        self.file_browse_button.clicked.connect(self.browse_for_file)

        self.file_dialog = QFileDialog()

        # Defaults.  All fields managed by Qt elements themselves for now

        self.default_exp_dir = os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))) + "\\exp-" + datetime.today().strftime('%Y-%m-%d')
        self.exp_dir_line.setText(self.default_exp_dir)

        self.default_trial_name = "rec01"
        self.trial_name_line.setText(self.default_trial_name)

        self.file_type_combo.setCurrentIndex(0)

        self.file_type_combo.setCurrentIndex(1)

    def browse_for_file(self):
        #  Uses QFileDialog to select a directory to save in
        self.exp_dir_line.setText(self.file_dialog.getExistingDirectory(self, "Select Directory"))

    # Getters

    def get_experiment_directory(self):
        return self.exp_dir_line.text()

    def get_trial_name(self):
        return self.trial_name_line.text()

    def get_file_type(self):
        return str(self.file_type_combo.curentText())

    def get_file_size(self):
        return str(self.file_size_combo.curentText())
