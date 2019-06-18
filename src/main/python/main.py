import PyQt5
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

import sys
import time
from pathlib import Path

from PyQt5 import QtCore

QtInstance = QtCore.QCoreApplication.instance()

if hasattr(QtCore.Qt, 'AA_EnableHighDpiScaling'):
    PyQt5.QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)

if hasattr(QtCore.Qt, 'AA_UseHighDpiPixmaps'):
    PyQt5.QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)

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
        
        self.file = FileGroupbox('File')
        self.mainGrid.addWidget(self.file,1,2)

        self.control = ControlGroupbox('Control')
        self.mainGrid.addWidget(self.control,2,2)
        
        #PLOTS
        self.plotSpectrum = PyQtG.PlotWidget(name="Spectral Scan")
        self.mainGrid.addWidget(self.plotSpectrum,1,1)
                
        self.plotIFFT = PyQtG.PlotWidget(name="IFFT")
        self.mainGrid.addWidget(self.plotIFFT,2,1)

        
class FileGroupbox(QGroupBox):
    
    def __init__(self,name,parent=None):
        
        super().__init__(name)
            
        self.layout = QFormLayout()

        self.setFixedWidth(700)
        
        self.formFile = QGroupBox("File")
        self.fileLayout = QFormLayout()
    
        self.entryExpName = QLineEdit()
        now = time.strftime("%y-%m-%d")
        default = now+'-PyImageOCT-exp'
        self.entryExpName.setText(default)

        self.entryExpDir = QLineEdit()
        here = str(Path.home())+'\\PyImageOCT\\Experiments\\'+default
        self.entryExpDir.setText(here)

        self.entryFileSize = QComboBox()
        self.entryFileSize.addItems(["250 MB","500 MB","1 GB"])

        self.entryFileType = QComboBox()
        self.entryFileType.addItems([".npy",".csv"])

        self.layout.addRow(QLabel("Experiment name"),self.entryExpName)
        self.layout.addRow(QLabel("Experiment directory"),self.entryExpDir)
        self.layout.addRow(QLabel("Maximum file size"),self.entryFileSize)
        self.layout.addRow(QLabel("File type"),self.entryFileType)
        
        self.setLayout(self.layout)

class ControlGroupbox(QGroupBox):

    def __init__(self, name, parent=None):

        super().__init__(name)

        self.layout = QGridLayout()

        self.scanButton = QPushButton('SCAN')
        self.acqButton = QPushButton('ACQUIRE')
        self.stopButton = QPushButton('STOP')

        self.layout.addWidget(self.scanButton,0,0)
        self.layout.addWidget(self.acqButton,0,1)
        self.layout.addWidget(self.stopButton,0,2)

        self.setLayout(self.layout)

if __name__ == '__main__':
    appctxt = ApplicationContext()
    window = Main()
    window.resize(1200, 600)
    window.show()
    exit_code = appctxt.app.exec_()
    sys.exit(exit_code)