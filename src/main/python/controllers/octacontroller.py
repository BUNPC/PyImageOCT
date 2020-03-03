from PyQt5 import QtWidgets
import pyqtgraph as pyqtg

from .spectralradarcontroller import SpectralRadarController

class OCTAController(SpectralRadarController):

    def __init__(self, mainwindow):

        super().__init__()

        widget2D = mainwindow.findChild(QtWidgets.QWidget, 'widget2D')
        widgetSpectrum = mainwindow.findChild(QtWidgets.QWidget, 'widgetSpectrum')
        layout2D = QtWidgets.QGridLayout()
        layoutSpectrum = QtWidgets.QGridLayout()
        widget2D.setLayout(layout2D)
        widgetSpectrum.setLayout(layoutSpectrum)

        self.plot2D = pyqtg.PlotWidget()
        self.plotSpectrum = pyqtg.PlotWidget()

        layout2D.addWidget(self.plot2D)
        layoutSpectrum.addWidget(self.plotSpectrum)

