from fbs_runtime.application_context import ApplicationContext
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

if QtInstance is None:
    QtInstance = QApplication(sys.argv)

class Main(QTabWidget):
    
    def __init__(self,parent=None):

        super().__init__(parent)

        self.tab0 = QWidget()
        self.tabFigEight = TabFigEight(parent=self)

        self.addTab(self.tab0,'Tab 0')
        self.addTab(self.tabFigEight,'Figure-8 Motion Quantification')
        
        self.windowTitle = 'MinaWare V.0.0.1'
        self.setWindowTitle(self.windowTitle)
    
        
class TabFigEight(QWidget):
    
    def __init__(self,parent=None):
        
        super().__init__(parent)
        
        self.mainGrid = QGridLayout()
        self.setLayout(self.mainGrid)
        
        self.file = FileGroupbox('File')
        self.mainGrid.addWidget(self.file,1,1,1,3)
        
        #PLOTS
        self.plotSpectrum = PyQtG.PlotWidget(name="Spectral Scan")
        self.mainGrid.addWidget(self.plotSpectrum,1,0,1,1)
        self.plotSpectrum.setFixedWidth(500)
                
        self.plotIFFT = PyQtG.PlotWidget(name="IFFT")
        self.mainGrid.addWidget(self.plotIFFT,2,0,1,1)
        self.plotIFFT.setFixedWidth(500)

        
class FileGroupbox(QGroupBox):
    
    def __init__(self,name,parent=None):
        
        super().__init__(name)
            
        self.layout = QFormLayout()
        
        self.formFile = QGroupBox("File")
        self.fileLayout = QFormLayout()
    
        self.entryExpName = QLineEdit()
        self.entryExpDir = QLineEdit()
        self.entryFileSize = QComboBox()
        self.entryFileSize.addItems(["250 MB","500 MB","1 GB"])
        self.entryFileType = QComboBox()
        self.entryFileType.addItems([".npy",".csv"])
        self.layout.addRow(QLabel("Experiment name"),self.entryExpName)
        now = time.strftime("%Y%m%d-%H%M%S")
        self.entryExpName.setText(now+'-PyOCT-experiment')
        self.layout.addRow(QLabel("Experiment directory"),self.entryExpDir)
        self.entryExpDir.setText(str(Path.home()))
        self.layout.addRow(QLabel("Maximum file size"),self.entryFileSize)
        self.layout.addRow(QLabel("File type"),self.entryFileType)
        
        self.setLayout(self.layout)

if __name__ == '__main__':
    appctxt = ApplicationContext()       # 1. Instantiate ApplicationContext
    window = Main()
    window.resize(1000, 600)
    window.show()
    exit_code = appctxt.app.exec_()      # 2. Invoke appctxt.app.exec_()
    sys.exit(exit_code)