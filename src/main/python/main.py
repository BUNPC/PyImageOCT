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

import sys

from PyQt5 import QtCore

from PyImage import SpectralRadarControl
from PyImage import Widgets

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
    
        
class TabFigEight(QWidget):
    '''
    Experimental scanning mode which uses figure-8 pattern to quickly measure 3D motion
    along two orthogonal B-scans.
    '''
    
    def __init__(self,parent=None):
        
        super().__init__(parent)

        self.mainGrid = QGridLayout()
        self.setLayout(self.mainGrid)

        #Real-time plot widget for display of raw spectral data
        self.plotSpectrum = Widgets.plotWidget2D(name="Raw Spectrum",type='curve')
        self.mainGrid.addWidget(self.plotSpectrum,1,1,2,1)

        #Real-time scatter plot widget for display of scan pattern
        self.plotPattern = Widgets.plotWidget2D(name="Scan Pattern Parameters",type='scatter')
        self.mainGrid.addWidget(self.plotPattern,2,3,1,1)

        #Thorlabs SpectralRadar SDK is wrapped with PySpectralRadar module.
        #Interfaces corresponding to scanning modes are defined PyImage.SpectralRadarControl
        #All display widgets must be passed to the controller!
        self.controller = SpectralRadarControl.FigureEight(plotWidget=self.plotSpectrum,scatterWidget=self.plotPattern)

        # Control GUI must be passed the controller defined above in order to call its methods

        #File I/O properties interface
        self.file = Widgets.FileGroupbox('File',self.controller)
        self.mainGrid.addWidget(self.file,1,2,1,2)

        #Master scan/acquire/stop buttons
        self.controlButtons = Widgets.ControlGroupbox('Control',self.controller)
        self.mainGrid.addWidget(self.controlButtons,4,1)

        #Fig 8 scan pattern parameters
        self.scanParameters = Widgets.Fig8Groupbox('Scan Pattern',self.controller)
        self.mainGrid.addWidget(self.scanParameters,2,2,1,1)

#Qt main loop
if __name__ == '__main__':
    appctxt = ApplicationContext()
    window = Main()
    window.show()
    exit_code = appctxt.app.exec_()
    sys.exit(exit_code)