from fbs_runtime.application_context.PyQt5 import ApplicationContext
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

import time

import sys
from pathlib import Path

from PyQt5 import QtCore

from PyImage import SpectralRadarControl
from PyImage import Widgets

QtInstance = QtCore.QCoreApplication.instance()

#Something wrong with these-- intended to fix DPI scaling issues but they make it worse
'''
if hasattr(QtCore.Qt, 'AA_EnableHighDpiScaling'):
    PyQt5.QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)

if hasattr(QtCore.Qt, 'AA_UseHighDpiPixmaps'):
    PyQt5.QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)
'''

#Allows IPython kernal to recover from closing of app
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
    
        
class TabFigEight(QWidget):
    '''
    Experimental scanning mode which uses figure-8 pattern to quickly measure 3D motion
    along two orthogonal B-scans.
    '''
    
    def __init__(self,parent=None):
        
        super().__init__(parent)

        self.mainGrid = QGridLayout()
        self.setLayout(self.mainGrid)

        #File I/O properties interface
        self.file = Widgets.FileGroupbox('File')
        self.mainGrid.addWidget(self.file,1,2)

        #Real-time plot widget for display of data
        self.plotSpectrum = Widgets.RealTimePlot(name="Raw Spectrum")
        self.mainGrid.addWidget(self.plotSpectrum,1,1)

        #Thorlabs SpectralRadar SDK is wrapped with PySpectralRadar module.
        #Interfaces corresponding to scanning modes are defined PyImage.SpectralRadarControl
        #All display widgets must be passed to the controller!
        self.controller = SpectralRadarControl.FigureEight(self.plotSpectrum)

        #Control GUI must be passed the controller define above
        self.controlButtons = Widgets.ControlGroupbox('Control',self.controller)
        self.mainGrid.addWidget(self.controlButtons,2,2)

#Qt main loop
if __name__ == '__main__':
    appctxt = ApplicationContext()
    window = Main()
    window.resize(1200, 600)
    window.show()
    exit_code = appctxt.app.exec_()
    sys.exit(exit_code)