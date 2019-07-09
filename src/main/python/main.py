from fbs_runtime.application_context.PyQt5 import ApplicationContext
from PyQt5.QtWidgets import QApplication
from PyQt5.QtWidgets import QWidget
from PyQt5.QtWidgets import QTabWidget
from PyQt5.QtWidgets import QGridLayout

import sys

from PyQt5 import QtCore

from src.main.python.PyImage import SpectralRadarControl, Widgets

#Something wrong with these-- intended to fix DPI scaling issues but they make it worse
'''
if hasattr(QtCore.Qt, 'AA_EnableHighDpiScaling'):
    PyQt5.QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)

if hasattr(QtCore.Qt, 'AA_UseHighDpiPixmaps'):
    PyQt5.QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)
'''

QtInstance = QtCore.QCoreApplication.instance()

#Supposed to allow IPython kernal to recover from closing of app
if QtInstance is None:
    QtInstance = QApplication(sys.argv)

class Main(QTabWidget):
    '''
    At the highest level, the GUI consists of tabs which organize various scanning/acquisition modes, similar to the
    OCT Imaging Freeform SDK program developed in LabView
    '''

    def __init__(self,parent=None):

        super().__init__(parent)

        self.tabFigEight = TabFigEight(parent=self)

        self.addTab(self.tabFigEight,'Figure-8 Motion Quantification')

        self.windowTitle = 'PyOCT V.0.0.1'
        self.setWindowTitle(self.windowTitle)

        self.setMinimumHeight(450)
        self.setMinimumWidth(650)


class TabFigEight(QWidget):
    '''
    Experimental scanning mode which uses figure-8 pattern to quickly measure 3D motion
    along two orthogonal B-scans.
    '''

    def __init__(self,parent=None):

        super().__init__(parent)

        self.mainGrid = QGridLayout()
        self.setLayout(self.mainGrid)

        # Real-time plot widget for display of raw spectral data
        self.plotSpectrum = Widgets.plotWidget2D(name="Raw Spectrum", type='curve', height=300, width=300)
        self.mainGrid.addWidget(self.plotSpectrum,0,0,2,2)

        # Real-time scatter plot widget for display of scan pattern
        self.plotPattern = Widgets.plotWidget2D(name="Scan Pattern Preview", type='scatter',height=250, width=300, aspectLocked=True)
        self.mainGrid.addWidget(self.plotPattern,1,4,1,1)
        self.plotPattern.labelAxes('mm','')

        # Thorlabs SpectralRadar SDK is wrapped with PySpectralRadar module.
        # Interfaces corresponding to scanning modes are defined PyImage.SpectralRadarControl
        # All display widgets must be passed to the controller!
        self.controller = SpectralRadarControl.FigureEight(plotWidget=self.plotSpectrum, scatterWidget=self.plotPattern)

        # Control GUI must be passed the controller defined above in order to call its methods

        # File I/O properties interface
        self.file = Widgets.FileGroupBox('File', self.controller)
        self.mainGrid.addWidget(self.file,0,2,1,3)

        # Main OCT device settings
        self.params = Widgets.ParamsGroupBox('OCT Imaging Parameters', self.controller)
        self.mainGrid.addWidget(self.params,1,2,1,1)

        # Fig 8 scan pattern parameters
        self.scanParameters = Widgets.Fig8GroupBox('Scan Pattern', self.controller)
        self.mainGrid.addWidget(self.scanParameters,1,3,1,1)

        # Master scan/acquire/stop buttons
        self.controlButtons = Widgets.ControlGroupBox('Control', self.controller)
        self.mainGrid.addWidget(self.controlButtons,2,1)

#Qt main loop
if __name__ == '__main__':
    appctxt = ApplicationContext()
    window = Main()
    window.show()
    exit_code = appctxt.app.exec_()
    sys.exit(exit_code)
