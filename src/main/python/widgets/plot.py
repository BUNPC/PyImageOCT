import os

import numpy as np
import pyqtgraph
from PyQt5 import uic
from PyQt5.QtWidgets import QWidget, QRadioButton, QCheckBox, QSlider, QLabel
from PyQt5.QtCore import QTimer


class SpectrumPlotWidget(pyqtgraph.PlotWidget):

    def __init__(self):

        super(pyqtgraph.PlotWidget, self).__init__()


class OCTViewer(pyqtgraph.GraphicsLayoutWidget):

    def __init__(self):

        super().__init__()

        self._viewbox = self.addViewBox(row=1, col=1)
        self._viewbox.setAspectLocked()
        self.image = pyqtgraph.ImageItem()
        self._viewbox.addItem(self.image)

    def setImage(self, img):
        self.image.setImage(img)

    def setLevels(self, levels):
        self.image.setLevels(levels)


class SpectrumView(QWidget):

    def __init__(self):

        super(QWidget, self).__init__()
        ui = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) + "\\ui\\spectrumplotter.ui"
        uic.loadUi(ui, self)

        plotwidget_placeholder = self.findChild(QWidget, "widgetSpec")
        plotwidget_placeholder_layout = plotwidget_placeholder.parent().layout()
        self.plotWidget = SpectrumPlotWidget()
        plotwidget_placeholder_layout.replaceWidget(plotwidget_placeholder, self.plotWidget)

    def update(self):
        print("SpectrumView update")


class BScanView(QWidget):

    def __init__(self):

        super(QWidget, self).__init__()
        ui = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) + "\\ui\\bscanplotter.ui"  # Double escape dir
        uic.loadUi(ui, self)

        viewer_placeholder = self.findChild(QWidget, "widget3D")
        viewer_placeholder_layout = viewer_placeholder.parent().layout()
        self.viewer = OCTViewer()
        viewer_placeholder_layout.replaceWidget(viewer_placeholder, self.viewer)

        self.enface_radio = self.findChild(QRadioButton, "radioEnface")
        self.enface_radio.toggled.connect(self.set_orientation)

        self.scan_check = self.findChild(QCheckBox, "checkScanThrough")
        self.scan_check.toggled.connect(self.set_scan_mode)

        self.db_check = self.findChild(QCheckBox, "dbCheck")

        self.slice_slider = self.findChild(QSlider, "sliderSlice")
        self.slice_slider.valueChanged.connect(self.slider_change)

        self.slice_label = self.findChild(QLabel, "sliceLabel")

        self.data = []
        self.dim = []
        self.current_slice = None

        self.set_data(np.random.random([1024, 400, 500]))  # For testing only!
        self.set_slice(1)  # Slice 1 is index 0!

        self.timer = QTimer()
        self.timer.timeout.connect(self.slice_thru_advance)

        self.enface = True

    def slice_thru_advance(self):
        print("Slicey slicey!")

    def update(self):
        print("BScanViewer update")

    def set_scan_mode(self):

        self.set_slice(1)
        if self.scan_check.isChecked():
            self.slice_slider.setEnabled(False)
            self.timer.start(100)
            print("Automatic scan")

        else:
            self.slice_slider.setEnabled(True)
            self.timer.stop()
            print("Manual control")

    def set_orientation(self):
        if self.enface_radio.isChecked():
            self.enface = True
        else:
            self.enface = False
        print(self.enface)

    def set_slice(self, index):
        self.current_slice = index
        self.slice_label.setText(str(index)+"/"+str(self.dim[2]))

    def slider_change(self):
        self.set_slice(self.slice_slider.value())

    def set_data(self, data_array):
        """
        Gives the widget 3D data to work with
        """
        self.data = data_array
        self.dim = np.shape(data_array)
        self.slice_slider.setMaximum(self.dim[2])  # TODO implement enface vs B view

    def display_slice(self):
        if self.enface:
            img = self.data[:, self.current_slice, :]
        else:
            img = self.data[:, :, self.current_slice]
        if self.db_check.isChecked():
            self.viewer.setImage(20*np.log10(img))
        else:
            self.viewer.setImage(img)