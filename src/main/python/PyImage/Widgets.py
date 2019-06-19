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
from pyqtgraph.Qt import QtGui

import time

from pathlib import Path

import numpy as np

class FileGroupbox(QGroupBox):

    def __init__(self, name, controller):
        super().__init__(name)

        self.controller = controller

        self.layout = QFormLayout()

        self.setFixedWidth(700)

        self.formFile = QGroupBox("File")
        self.fileLayout = QFormLayout()

        self.entryExpName = QLineEdit()
        now = time.strftime("%y-%m-%d")
        default = now + '-PyImageOCT-exp'
        self.entryExpName.setText(default)
        self.entryExpName.editingFinished.connect(self.update)

        self.entryExpDir = QLineEdit()
        here = str(Path.home()) + '\\PyImageOCT\\Experiments\\' + default
        self.entryExpDir.setText(here)
        self.entryExpDir.editingFinished.connect(self.update)

        self.entryFileSize = QComboBox()
        self.entryFileSize.addItems(["250 MB", "500 MB", "1 GB"])
        self.entryFileSize.currentIndexChanged.connect(self.update)

        self.entryFileType = QComboBox()
        self.entryFileType.addItems([".npy", ".csv"])
        self.entryFileType.currentIndexChanged.connect(self.update)

        self.layout.addRow(QLabel("Experiment name"), self.entryExpName)
        self.layout.addRow(QLabel("Experiment directory"), self.entryExpDir)
        self.layout.addRow(QLabel("Maximum file size"), self.entryFileSize)
        self.layout.addRow(QLabel("File type"), self.entryFileType)

        self.setLayout(self.layout)

        self.update()

    def update(self):

        self.controller.experimentName = self.entryExpName.text()
        self.controller.experimentDirectory = self.entryExpDir.text()
        self.controller.maxFileSize = str(self.entryFileSize.currentText())
        self.controller.fileType = str(self.entryFileType.currentText())

class ControlGroupbox(QGroupBox):

    def __init__(self, name, controller):
        super().__init__(name)

        self.controller = controller

        self.layout = QGridLayout()

        self.scanButton = QPushButton('SCAN')
        self.acqButton = QPushButton('ACQUIRE')
        self.abortButton = QPushButton('STOP')

        self.scanButton.clicked.connect(self.controller.initScan)
        self.acqButton.clicked.connect(self.controller.initAcq)
        self.abortButton.clicked.connect(self.controller.abort)

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

class plotWidget2D(PyQtG.PlotWidget):

    def __init__(self,type='curve',name=None):

        super().__init__(name=name)

        if type == 'curve':
            self.item = PyQtG.PlotCurveItem()
        elif type == 'scatter':
            self.item = PyQtG.ScatterPlotItem()
        else:
            raise Exception('Invalid type for PyQtGraph item. Only "curve" and "scatter" are supported.')

        self.addItem(self.item)

    def plot(self,X,Y):
        '''
        Plot
        '''
        self.item.clear()
        self.item.setData(x=X,y=Y)
        QtGui.QApplication.processEvents()


