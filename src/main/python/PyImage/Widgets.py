from PyQt5.QtWidgets import QApplication
from PyQt5.QtWidgets import QWidget
from PyQt5.QtWidgets import QLabel
from PyQt5.QtWidgets import QLineEdit
from PyQt5.QtWidgets import QTabWidget
from PyQt5.QtWidgets import QSpinBox
from PyQt5.QtWidgets import QComboBox
from PyQt5.QtWidgets import QDoubleSpinBox
from PyQt5.QtWidgets import QPushButton
from PyQt5.QtWidgets import QGroupBox
from PyQt5.QtWidgets import QGridLayout
from PyQt5.QtWidgets import QFormLayout

import pyqtgraph as PyQtG

import time

from pathlib import Path

import numpy as np

class FileGroupbox(QGroupBox):

    def __init__(self, name, parent=None):
        super().__init__(name)

        self.layout = QFormLayout()

        self.setFixedWidth(700)

        self.formFile = QGroupBox("File")
        self.fileLayout = QFormLayout()

        self.entryExpName = QLineEdit()
        now = time.strftime("%y-%m-%d")
        default = now + '-PyImageOCT-exp'
        self.entryExpName.setText(default)

        self.entryExpDir = QLineEdit()
        here = str(Path.home()) + '\\PyImageOCT\\Experiments\\' + default
        self.entryExpDir.setText(here)

        self.entryFileSize = QComboBox()
        self.entryFileSize.addItems(["250 MB", "500 MB", "1 GB"])

        self.entryFileType = QComboBox()
        self.entryFileType.addItems([".npy", ".csv"])

        self.layout.addRow(QLabel("Experiment name"), self.entryExpName)
        self.layout.addRow(QLabel("Experiment directory"), self.entryExpDir)
        self.layout.addRow(QLabel("Maximum file size"), self.entryFileSize)
        self.layout.addRow(QLabel("File type"), self.entryFileType)

        self.setLayout(self.layout)


class ControlGroupbox(QGroupBox):

    def __init__(self, name, spectralRadarController=None):
        super().__init__(name)

        self.layout = QGridLayout()

        self.scanButton = QPushButton('SCAN')
        self.acqButton = QPushButton('ACQUIRE')
        self.abortButton = QPushButton('STOP')

        self.scanButton.clicked.connect(spectralRadarController.initScan)
        self.acqButton.clicked.connect(spectralRadarController.initAcq)
        self.abortButton.clicked.connect(spectralRadarController.abort)

        self.layout.addWidget(self.scanButton, 0, 0)
        self.layout.addWidget(self.acqButton, 0, 1)
        self.layout.addWidget(self.abortButton, 0, 2)

        self.setLayout(self.layout)

    def disable(self):
        self.scanButton.setEnabled(False)
        self.acqButton.setEnabled(False)

    def enable(self):
        self.scanButton.setEnabled(True)
        self.acqButton.setEnabled(True)