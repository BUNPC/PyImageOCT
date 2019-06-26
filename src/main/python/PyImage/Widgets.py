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
from PyQt5.QtWidgets import QTextEdit

import pyqtgraph as PyQtG
from pyqtgraph.Qt import QtGui

import time

from pathlib import Path

import numpy as np

from PyImage.OCT import *

class FileGroupbox(QGroupBox):

    def __init__(self, name, controller, width=500):
        super().__init__(name)

        self.controller = controller

        self.layout = QFormLayout()

        # self.setFixedWidth(width)

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

        experimentName = self.entryExpName.text()
        experimentDirectory = self.entryExpDir.text()
        maxFileSize = str(self.entryFileSize.currentText())
        fileType = str(self.entryFileType.currentText())

        self.controller.setFileParams(experimentName,experimentDirectory,maxFileSize,fileType)

class ParamsGroupbox(QGroupBox):

    def __init__(self, name, controller):
        super().__init__(name)

        self.controller = controller

        self.layout = QFormLayout()

        self.entryImagingRate = QComboBox()
        self.entryImagingRate.addItems(["76 kHz","146 kHz"])
        self.entryImagingRate.currentIndexChanged.connect(self.update)

        self.entryConfig = QComboBox()
        self.entryConfig.addItems(["10X"])
        self.entryConfig.currentIndexChanged.connect(self.update)

        self.layout.addRow(QLabel("Imaging rate"), self.entryImagingRate)
        self.layout.addRow(QLabel("Objective configuration"), self.entryConfig)

        self.setLayout(self.layout)

    def update(self):

        pass



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

    def disabled(self,bool):
        self.scanButton.setEnabled(bool)
        self.acqButton.setEnabled(bool)


class Fig8Groupbox(QGroupBox):

    def __init__(self, name, controller, width=500):
        super().__init__(name)

        self.controller = controller

        self.layout = QFormLayout()

        # self.setFixedWidth(width)

        self.spinALinesPerX = QSpinBox()
        self.spinALinesPerX.setRange(5,200)
        self.spinALinesPerX.setValue(10)
        self.spinALinesPerX.valueChanged.connect(self.update)

        self.spinFig8Size = QDoubleSpinBox()
        self.spinFig8Size.setRange(0.00001,3)
        self.spinFig8Size.setValue(0.01)
        self.spinFig8Size.setSuffix(' mm')
        self.spinFig8Size.setDecimals(5)
        self.spinFig8Size.setSingleStep(0.00001)
        self.spinFig8Size.valueChanged.connect(self.update)

        self.spinFig8Total = QSpinBox()
        self.spinFig8Total.setRange(1,5000)
        self.spinFig8Total.setValue(500)
        self.spinFig8Total.valueChanged.connect(self.update)

        self.spinAcqTime = QSpinBox()
        self.spinAcqTime.setRange(10,20000)
        self.spinAcqTime.setValue(1000)
        self.spinAcqTime.valueChanged.connect(self.update)

        self.textDistance = QTextEdit()
        self.textDistance.setReadOnly(True)
        self.textDistance.setFixedHeight(30)
        self.textDistance.setCursorWidth(0)

        self.textTotal = QTextEdit()
        self.textTotal.setReadOnly(True)
        self.textTotal.setFixedHeight(30)
        self.textTotal.setCursorWidth(0)

        self.layout.addRow(QLabel("A-lines per B-scan"), self.spinALinesPerX)
        self.layout.addRow(QLabel("Figure-8 width"), self.spinFig8Size)
        self.layout.addRow(QLabel("Distance between adjacent A-scans (mm)"),self.textDistance)
        self.layout.addRow(QLabel("Total A-scans in each figure-8"),self.textTotal)
        self.layout.addRow(QLabel("Total Figure-8s to acquire"), self.spinFig8Total)
        self.layout.addRow(QLabel("Total acquisition time"), self.spinAcqTime)

        self.setLayout(self.layout)

        self.update()

    def update(self):

        self.controller.setScanPatternParams(self.spinFig8Size.value(),
                                             self.spinALinesPerX.value(),
                                             self.spinFig8Total.value())

        self.textDistance.setText(str(self.controller.scanPatternD*10**6)[0:10]+' nm')
        self.textTotal.setText(str(self.controller.scanPatternN))
        self.controller.displayPattern()

    def disabled(self,bool):
        self.spinALinesPerX.setDisabled(bool)
        self.spinFig8Size.setDisabled(bool)

class plotWidget2D(PyQtG.PlotWidget):

    def __init__(self,type='curve',name=None, xaxis=np.arange(1024), width=400):

        super().__init__(name=name)

        if type == 'curve':
            self.item = PyQtG.PlotCurveItem()
        elif type == 'scatter':
            self.item = PyQtG.ScatterPlotItem()
        else:
            raise Exception('Invalid type for PyQtGraph item. Only "curve" and "scatter" are supported.')

        self.setTitle(title=name)
        self.X = xaxis
        self.showGrid(x=1,y=1)
        self.addItem(self.item)

    def plot1D(self,Y):
        self.item.clear()
        self.item.setData(x=self.X,y=Y)
        QtGui.QApplication.processEvents()

    def plot2D(self,X,Y):
        self.item.clear()
        self.item.setData(x=X,y=Y)
        QtGui.QGuiApplication.processEvents()


