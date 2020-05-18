from PyQt5 import uic
from PyQt5.QtWidgets import QGroupBox, QLineEdit, QComboBox, QToolButton, QFileDialog, QSpinBox, QDoubleSpinBox, QCheckBox, QPushButton
from datetime import datetime
import os
import glob

FileTypes = [
    ".npy",
    ".mat"
]


FileSizes = [
    "250 MB",
    "500 MB",
    "1 GB",
    "2 GB",
    "4 GB"
]


Rates = {
    "76 kHz": 76000,
    "146 kHz": 146000
}


class ScanPanelOCTA(QGroupBox):

    def __init__(self):

        super(QGroupBox, self).__init__()
        ui = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))+"\\ui\\scan_octa.ui"  # Double escape dir
        uic.loadUi(ui, self)

        self.indefinite_check = self.findChild(QCheckBox, "checkIndefinite")
        self.indefinite_check.stateChanged.connect(self.indefinite_check_changed)

        self.equal_aspect_check = self.findChild(QCheckBox, "checkEqualAspect")
        self.equal_aspect_check.stateChanged.connect(self.equal_aspect_check_changed)

        self.scan_number_spin = self.findChild(QSpinBox, "spinScanNumber")

        self.x_roi_spin = self.findChild(QDoubleSpinBox, "spinROIWidth")
        self.x_count_spin = self.findChild(QSpinBox, "spinACount")
        self.x_spacing_spin = self.findChild(QDoubleSpinBox, "spinFastAxisSpacing")

        self.y_roi_spin = self.findChild(QDoubleSpinBox, "spinROIHeight")
        self.y_count_spin = self.findChild(QSpinBox, "spinBCount")
        self.y_spacing_spin = self.findChild(QDoubleSpinBox, "spinSlowAxisSpacing")

        self.preview_button = self.findChild(QPushButton, "previewButton")

        self.x_spacing_spin.valueChanged.connect(self.x_spacing_changed)

        self.x_roi_spin.valueChanged.connect(self.roi_changed)
        self.y_roi_spin.valueChanged.connect(self.roi_changed)

        self.x_spacing_spin.valueChanged.connect(self.spacing_changed)
        self.y_spacing_spin.valueChanged.connect(self.spacing_changed)

        self.x_count_spin.valueChanged.connect(self.count_changed)
        self.y_count_spin.valueChanged.connect(self.count_changed)

        self.show()

    def count_changed(self):
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

    def spacing_changed(self):
        self.x_roi_spin.blockSignals(True)
        self.y_roi_spin.blockSignals(True)

        try:
            self.x_roi_spin.setValue((self.x_spacing_spin.value() / 1000) * (self.x_count_spin.value() - 0))
            self.y_roi_spin.setValue((self.y_spacing_spin.value() / 1000) * (self.y_count_spin.value() - 0))
        except ZeroDivisionError:
            pass

        self.x_roi_spin.blockSignals(False)
        self.y_roi_spin.blockSignals(False)

    def roi_changed(self):
        self.x_spacing_spin.blockSignals(True)
        self.y_spacing_spin.blockSignals(True)

        try:
            self.x_spacing_spin.setValue((self.x_roi_spin.value() * 1000) / self.x_count_spin.value())
            self.y_spacing_spin.setValue((self.y_roi_spin.value() * 1000) / self.y_count_spin.value())
        except ZeroDivisionError:
            pass

        self.x_spacing_spin.blockSignals(False)
        self.y_spacing_spin.blockSignals(False)

    def indefinite_check_changed(self):
        if self.indefinite_check.isChecked():
            self.scan_number_spin.setEnabled(False)
        else:
            self.scan_number_spin.setEnabled(True)

    def equal_aspect_check_changed(self):
        if self.equal_aspect_check.isChecked():
            self.y_spacing_spin.setValue(self.x_spacing_spin.value())
            self.y_spacing_spin.setEnabled(False)
        else:
            self.y_spacing_spin.setEnabled(True)

    def x_spacing_changed(self):
        if self.equal_aspect_check.isChecked():
            self.y_spacing_spin.setValue(self.x_spacing_spin.value())


class ConfigPanel(QGroupBox):

    def __init__(self):

        super(QGroupBox, self).__init__()
        ui = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))+"\\ui\\config.ui"  # Double escape dir
        uic.loadUi(ui, self)

        self.configdir = "C:\\ThorLabs\\SpectralRadar\\config"  # TODO set this intelligently on startup
        self.configpaths = glob.glob(self.configdir+"/*.ini")
        print(self.configpaths)

        self.config_combo = self.findChild(QComboBox, "comboConfig")
        for path in self.configpaths:
            self.config_combo.addItem(os.path.basename(path).split(".")[0])  # Just get name of file w/o extension

        self.rate_combo = self.findChild(QComboBox, "comboRate")
        self.apod_combo = self.findChild(QComboBox, "comboApodization")

        self.bitness_check = self.findChild(QCheckBox, "check32")
        self.fft_check = self.findChild(QCheckBox, "checkFFT")
        self.interp_check = self.findChild(QCheckBox, "checkInterpolation")

        self.show()

    def get_proc_stream(self):
        """
        Returns a list of 3 booleans: [fft, interp, 32bit or 64bit]
        """
        return [self.fft_check.checked(), self.interp_check.checked(), self.bitness_check.checked()]

    def get_config(self):
        return self.config_combo.text()

    def get_rate(self):
        return Rates[self.rate_combo.text()]

    def get_apod(self):
        return self.apod_combo.text()

class RepeatsPanel(QGroupBox):

    def __init__(self):

        super(QGroupBox, self).__init__()
        ui = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))+"\\ui\\repeats.ui"  # Double escape dir
        uic.loadUi(ui, self)

        self.a_repeat_spin = self.findChild(QSpinBox, "spinARepeat")
        self.b_repeat_spin = self.findChild(QSpinBox, "spinBRepeat")
        self.avg_check = self.findChild(QCheckBox, "checkAveraging")

        self.show()

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

        ui = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))+"\\ui\\filePanel.ui"  # Double escape dir
        uic.loadUi(ui, self)

        self.exp_dir_line = self.findChild(QLineEdit, "lineExp")
        self.trial_name_line = self.findChild(QLineEdit, "lineFileName")
        self.file_type_combo = self.findChild(QComboBox, "comboFileType")
        self.file_size_combo = self.findChild(QComboBox, "comboFileSize")

        self.file_browse_button = self.findChild(QToolButton, "buttonBrowse")
        self.file_browse_button.clicked.connect(self.browse_for_file)

        self.file_dialog = QFileDialog()

        # Defaults.  All fields managed by Qt elements themselves for now

        self.default_exp_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "\\exp-" + datetime.today().strftime('%Y-%m-%d')
        self.exp_dir_line.setText(self.default_exp_dir)

        self.default_trial_name = "rec01"
        self.trial_name_line.setText(self.default_trial_name)

        self.file_type_combo.setCurrentIndex(0)

        self.file_type_combo.setCurrentIndex(1)

        self.show()

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