from PyQt5 import QtWidgets
from widgets.plot import SpectrumPlot, BScanPlot

from spectralradarcontroller import SpectralRadarController

class OCTAController(SpectralRadarController):

    def __init__(self, mainwindow):

        super().__init__()


