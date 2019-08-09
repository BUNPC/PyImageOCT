from PyQt5.QtWidgets import QLabel
from PyQt5.QtWidgets import QLineEdit
from PyQt5.QtWidgets import QSpinBox
from PyQt5.QtWidgets import QComboBox
from PyQt5.QtWidgets import QDoubleSpinBox
from PyQt5.QtWidgets import QPushButton
from PyQt5.QtWidgets import QGroupBox
from PyQt5.QtWidgets import QGridLayout
from PyQt5.QtWidgets import QFormLayout
from PyQt5.QtWidgets import QTextEdit
from PyQt5.QtWidgets import QWidget
from PyQt5.QtWidgets import QRadioButton
from PyQt5.QtWidgets import QHBoxLayout
from PyQt5.QtWidgets import QProgressBar

import pyqtgraph as PyQtG
from pyqtgraph.Qt import QtGui
from PyQt5 import QtCore

import time

from pathlib import Path

from src.main.python.PyImage.OCT import *


class FileGroupBox(QGroupBox):

    def __init__(self, name, controller):
        super().__init__(name)

        self.controller = controller

        self.layout = QFormLayout()

        defaultName = 'fig8_0'
        self.entryExpName = QLineEdit()
        self.entryExpName.setText(defaultName)
        self.entryExpName.editingFinished.connect(self.update)

        self.entryExpDir = QLineEdit()
        now = time.strftime("%d-%m-%y")
        default = now + '-PyImageOCT-exp'
        here = 'E:/PyImageOCT/Experiments/'+default  # TODO make not hardcoded
        self.entryExpDir.setText(here)
        self.entryExpDir.editingFinished.connect(self.update)

        self.entryFileSize = QComboBox()
        self.entryFileSize.addItems(["250 MB", "500 MB", "1 GB"])
        self.entryFileSize.currentIndexChanged.connect(self.update)

        self.entryFileType = QComboBox()
        self.entryFileType.addItems([".npy", ".hdf"])
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

        self.controller.setFileParams(experimentDirectory, experimentName, maxFileSize, fileType)

    def enabled(self, bool):
        self.entryExpDir.setEnabled(bool)
        self.entryExpName.setEnabled(bool)
        self.entryFileSize.setEnabled(bool)
        self.entryFileType.setEnabled(bool)

class ParamsGroupBox(QGroupBox):

    def __init__(self, name, controller):
        super().__init__(name)

        self.controller = controller

        self.layout = QFormLayout()

        self.entryImagingRate = QComboBox()
        self.entryImagingRate.addItems(["76 kHz", "146 kHz"])
        self.entryImagingRate.currentIndexChanged.connect(lambda: self.controller.setRate(str(self.entryImagingRate.currentText())))

        self.entryConfig = QComboBox()
        self.entryConfig.addItems(["10X", "5X"])  # TODO fix 2X
        self.entryConfig.currentIndexChanged.connect(lambda: self.controller.setConfig(str(self.entryConfig.currentText())))

        self.entryWindow = QComboBox()
        self.entryWindow.addItems(["Hann", "Hamming", "Blackman", "None"])
        self.entryWindow.currentIndexChanged.connect(self.update)

        self.radioBoxB = QWidget(parent=self)
        self.radioBoxB.setFixedWidth(80)
        self.radioBoxBLayout = QHBoxLayout()
        self.B1 = QRadioButton('Y')
        self.B2 = QRadioButton('X')
        self.B2.setChecked(True)
        self.B1.toggled.connect(self.update)
        self.B2.toggled.connect(self.update)
        self.radioBoxBLayout.addWidget(self.B2)
        self.radioBoxBLayout.addWidget(self.B1)
        self.radioBoxB.setLayout(self.radioBoxBLayout)

        self.layout.addRow(QLabel("Imaging rate"), self.entryImagingRate)
        self.layout.addRow(QLabel("Objective configuration"), self.entryConfig)
        self.layout.addRow(QLabel("Apodization window"), self.entryWindow)
        self.layout.addRow(QLabel("B-Scan display"), self.radioBoxB)

        self.setLayout(self.layout)

        self.update()

    def update(self):

        windowLUT = {
            "Hann" : np.hanning(2048),
            "Hamming" : np.hamming(2048),
            "Blackman" : np.blackman(2048),
            "None" : np.ones(2048)
        }

        window = windowLUT[str(self.entryWindow.currentText())]

        self.controller.setApodWindow(window)

        if self.B1.isChecked():
            self.controller.setDisplayAxis(0)
        else:
            self.controller.setDisplayAxis(1)



    def enabled(self, bool):
        self.entryImagingRate.setEnabled(bool)
        self.entryConfig.setEnabled(bool)
        self.entryWindow.setEnabled(bool)
        # self.B1.setEnabled(bool)  # For now, switching views works during scanning
        # self.B2.setEnabled(bool)


class ControlGroupBox(QGroupBox):

    def __init__(self, name, controller):
        super().__init__(name)

        self.controller = controller

        self.layout = QGridLayout()

        self.scanButton = QPushButton('SCAN')
        self.acqButton = QPushButton('ACQUIRE')
        self.trackButton = QPushButton('TRACK MOTION')
        self.abortButton = QPushButton('STOP')

        self.scanButton.clicked.connect(self.controller.initScan)
        self.acqButton.clicked.connect(self.controller.initAcq)
        self.trackButton.clicked.connect(self.controller.initTracking)
        self.abortButton.clicked.connect(self.controller.abort)

        self.scanButton.clicked.connect(self.update)
        self.acqButton.clicked.connect(self.update)
        self.trackButton.clicked.connect(self.update)
        self.abortButton.clicked.connect(self.update)

        self.layout.addWidget(self.scanButton, 0, 0)
        self.layout.addWidget(self.acqButton, 0, 1)
        self.layout.addWidget(self.trackButton, 0 ,2)
        self.layout.addWidget(self.abortButton, 0, 3)

        self.setLayout(self.layout)

    def enabled(self, bool):
        self.scanButton.setEnabled(bool)
        self.acqButton.setEnabled(bool)


class ProgressWidget(QWidget):

    def __init__(self, controller):
        super().__init__()

        self.controller = controller

        self.layout = QHBoxLayout()

        self.bar = QtGui.QProgressBar()
        self.bar.setMinimum(0)
        self.bar.setMaximum(10)
        self.bar.setValue(0)

        self.label = QLabel('')

        self.layout.addWidget(self.label)
        self.layout.addWidget(self.bar)

        self.setLayout(self.layout)

    def setText(self,s):
        self.label.setText(s)

    def setProgress(self,v):
        self.bar.setValue(v)
        QtGui.QGuiApplication.processEvents()


class Fig8GroupBox(QGroupBox):

    def __init__(self, name, controller):
        super().__init__(name)

        self.controller = controller

        self.layout = QFormLayout()

        self.spinALinesPerX = QSpinBox()
        self.spinALinesPerX.setRange(5, 400)
        self.spinALinesPerX.setValue(100)
        self.spinALinesPerX.valueChanged.connect(self.update)

        self.spinBPadding = QSpinBox()
        self.spinBPadding.setValue(20)
        self.spinBPadding.valueChanged.connect(self.update)

        self.spinFlyback = QSpinBox()
        self.spinFlyback.setRange(2, 600)
        self.spinFlyback.setValue(50)
        self.spinFlyback.valueChanged.connect(self.update)

        self.spinAngle = QSpinBox()
        self.spinAngle.setRange(0, 360)
        self.spinAngle.setValue(43)
        self.spinAngle.setSuffix('°')
        self.spinAngle.valueChanged.connect(self.update)

        self.spinFlybackAngle = QDoubleSpinBox()
        self.spinFlybackAngle.setRange(40, 120)
        self.spinFlybackAngle.setValue(74.5)
        self.spinFlybackAngle.setSingleStep(0.5)
        self.spinFlybackAngle.setDecimals(1)
        self.spinFlybackAngle.setSuffix('°')
        self.spinFlybackAngle.valueChanged.connect(self.update)

        self.spinALineSpacing = QDoubleSpinBox()
        self.spinALineSpacing.setRange(0.001, 2000)
        self.spinALineSpacing.setSuffix(' um')
        self.spinALineSpacing.setDecimals(2)
        self.spinALineSpacing.setSingleStep(0.10)
        self.spinALineSpacing.setValue(3.00)
        self.spinALineSpacing.valueChanged.connect(self.update)

        self.spinFig8Total = QSpinBox()
        self.spinFig8Total.setRange(2, 5000)
        self.spinFig8Total.setValue(500)
        self.spinFig8Total.valueChanged.connect(self.update)

        self.spinAcqTime = QSpinBox()
        self.spinAcqTime.setRange(10, 20000)
        self.spinAcqTime.setValue(1000)
        self.spinAcqTime.valueChanged.connect(self.update)

        self.textRate = QTextEdit()
        self.textRate.setReadOnly(True)
        self.textRate.setFixedHeight(24)
        self.textRate.setCursorWidth(0)
        self.textRate.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        self.textTotal = QTextEdit()
        self.textTotal.setReadOnly(True)
        self.textTotal.setFixedHeight(24)
        self.textTotal.setCursorWidth(0)
        self.textTotal.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        self.layout.addRow(QLabel("A-lines per B-scan"), self.spinALinesPerX)
        self.layout.addRow(QLabel("B-Scan padding"), self.spinBPadding)
        self.layout.addRow(QLabel("A-lines per flyback"), self.spinFlyback)
        self.layout.addRow(QLabel("Distance between A-lines in B-scan"), self.spinALineSpacing)
        self.layout.addRow(QLabel("Scan-pattern angle"), self.spinAngle)
        self.layout.addRow(QLabel("Flyback angle"), self.spinFlybackAngle)
        self.layout.addRow(QLabel("Total A-scans in each figure-8"), self.textTotal)
        self.layout.addRow(QLabel("Rate of figure-8 acquisition"), self.textRate)
        self.layout.addRow(QLabel("Total Figure-8s to acquire"), self.spinFig8Total)
        self.setLayout(self.layout)

        self.update()

    def update(self):

        self.spinBPadding.setRange(0,int((self.spinALinesPerX.value()-1)))
        self.controller.setScanPatternParams(self.spinALineSpacing.value()*10**-3,  # Convert from um to mm
                                             self.spinALinesPerX.value(),  # Do not subtract bPadding!
                                             self.spinBPadding.value(),
                                             self.spinFlyback.value(),
                                             self.spinFig8Total.value(),
                                             self.spinAngle.value() * (np.pi/180),
                                             self.spinFlybackAngle.value() * (np.pi/180)) # Conversion to rad happens here!

        self.textTotal.setText(str(self.controller.scanPatternN))

        w = 1 / (1 / self.controller.getRateValue() * self.controller.scanPatternN)
        self.textRate.setText(str(w)[0:5] + ' hz ')
        self.controller.displayPattern()

    def enabled(self, bool):
        self.spinALinesPerX.setEnabled(bool)
        self.spinFlyback.setEnabled(bool)
        self.spinALineSpacing.setEnabled(bool)
        self.spinAngle.setEnabled(bool)
        self.spinFlybackAngle.setEnabled(bool)
        self.spinAcqTime.setEnabled(bool)
        self.spinFig8Total.setEnabled(bool)
        self.spinBPadding.setEnabled(bool)


class QuantGroupBox(QGroupBox):

    def __init__(self,name,controller):
        super().__init__(name)

        self.controller = controller

        self.layout = QFormLayout()

        self.spinAxialMin = QSpinBox()
        self.spinAxialMin.setValue(8)
        self.spinAxialMin.valueChanged.connect(self.update)

        self.spinAxialMax = QSpinBox()
        self.spinAxialMax.setValue(400)
        self.spinAxialMax.valueChanged.connect(self.update)

        self.axialBoxLayout = QHBoxLayout()
        self.axialBoxLayout.addWidget(self.spinAxialMin)
        self.axialBoxLayout.addWidget(self.spinAxialMax)

        self.layout.addRow(QLabel('Axial ROI top-bottom'), self.axialBoxLayout)

        self.setLayout(self.layout)

        self.update()

    def update(self):

        self.spinAxialMax.setRange(self.spinAxialMin.value()+1, 1024)

        axial = (self.spinAxialMin.value(), self.spinAxialMax.value())

        self.controller.setROI(axial)

    def enabled(self, bool):
        # For now, ROI change during scan works fine.
        pass


class PlotPatternWidget(PyQtG.PlotWidget):

    def __init__(self, name, aspectLocked=True):

        super().__init__(name=name)

        self.setTitle(title=name)
        self.setAspectLocked(aspectLocked)
        self.showGrid(x=1, y=1)
        fbBrush = PyQtG.mkBrush(color=(255,255,255))
        roiBrush = PyQtG.mkBrush(color=(150,150,200))
        fbPen = PyQtG.mkPen(color=(255,255,255,0))
        roiPen = PyQtG.mkPen(color=(255,255,255,0))
        self.flyback = PyQtG.ScatterPlotItem(pen=fbPen, brush=fbBrush, symbol='+')
        self.roi = PyQtG.ScatterPlotItem(pen=roiPen, brush=roiBrush)
        self.addItem(self.flyback)
        self.addItem(self.roi)

    def labelAxes(self, xlabel, ylabel):
        self.setLabels(left=ylabel, bottom=xlabel)

    def plotFigEight(self,fbx,fby,roix=None,roiy=None):
        self.flyback.clear()
        self.roi.clear()
        self.flyback.setData(fbx,fby)
        self.roi.setData(roix,roiy)

    def enabled(self, bool):
        pass


class PlotWidget2D(PyQtG.PlotWidget):

    def __init__(self, type='curve', name=None, xaxis=np.arange(2048), aspectLocked=False):

        super().__init__(name=name)

        if type == 'curve':
            self.item = PyQtG.PlotCurveItem()
        elif type == 'scatter':
            self.item = PyQtG.ScatterPlotItem()
        else:
            raise Exception('Invalid type for PyQtGraph item. Only "curve" and "scatter" are supported.')

        self.setTitle(title=name)
        self.setAspectLocked(aspectLocked)
        self.X = xaxis
        self.showGrid(x=1, y=1)
        self.addItem(self.item)

    def labelAxes(self, xlabel, ylabel):
        self.setLabels(left=ylabel, bottom=xlabel)

    def plot1D(self, Y):
        self.item.clear()
        self.item.setData(x=self.X, y=Y)

    def plot2D(self, X, Y):
        self.item.clear()
        self.item.setData(x=X, y=Y)

    def enabled(self, bool):
        pass


class BScanViewer(PyQtG.ImageView):

    def __init__(self):

        super().__init__()

        self.ui.histogram.hide()
        self.ui.roiBtn.hide()
        self.ui.menuBtn.hide()

    def update(self,data):
        self.clear()
        self.setImage(data, autoLevels=False, levels=(-100, -2))

    def enabled(self, bool):
        pass