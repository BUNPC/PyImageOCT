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

import pyqtgraph as PyQtG

import time

import sys
from pathlib import Path

from PyQt5 import QtCore

from PyImage import SpectralRadarControl
from PyImage import Widgets

QtInstance = QtCore.QCoreApplication.instance()

# if hasattr(QtCore.Qt, 'AA_EnableHighDpiScaling'):
#     PyQt5.QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
#
# if hasattr(QtCore.Qt, 'AA_UseHighDpiPixmaps'):
#     PyQt5.QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)

if QtInstance is None:
    QtInstance = QApplication(sys.argv)

class Main(QTabWidget):
    
    def __init__(self,parent=None):

        super().__init__(parent)

        # self.tab0 = QWidget()
        self.tabFigEight = TabFigEight(parent=self)

        # self.addTab(self.tab0,'Tab 0')
        self.addTab(self.tabFigEight,'Figure-8 Motion Quantification')
        
        self.windowTitle = 'PyOCT V.0.0.1'
        self.setWindowTitle(self.windowTitle)
    
        
class TabFigEight(QWidget):
    
    def __init__(self,parent=None):
        
        super().__init__(parent)
        
        self.mainGrid = QGridLayout()
        self.setLayout(self.mainGrid)
        
        self.file = Widgets.FileGroupbox('File')
        self.mainGrid.addWidget(self.file,1,2)

        self.srcontrol = SpectralRadarControl.FigureEight()

        self.control = Widgets.ControlGroupbox('Control',spectralRadarController=self.srcontrol)
        self.mainGrid.addWidget(self.control,2,2)
        
        #PLOTS
        self.plotSpectrum = PyQtG.PlotWidget(name="Spectral Scan")
        self.mainGrid.addWidget(self.plotSpectrum,1,1)
                
        self.plotIFFT = PyQtG.PlotWidget(name="IFFT")
        self.mainGrid.addWidget(self.plotIFFT,2,1)

if __name__ == '__main__':
    appctxt = ApplicationContext()
    window = Main()
    window.resize(1200, 600)
    window.show()
    exit_code = appctxt.app.exec_()
    sys.exit(exit_code)