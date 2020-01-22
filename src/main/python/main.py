from fbs_runtime.application_context.PyQt5 import ApplicationContext
from PyQt5.QtWidgets import QMainWindow
from PyQt5 import uic, QtWidgets
import pyqtgraph as pyqtg
from src.main.python.controllers import OCTAController, Fig8AController, CircleAController, SpectralRadarController


import sys
import os

class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        uifile = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))+"\\ui\\MainWindow.ui"
        uic.loadUi(uifile,self)
        """
        Entire GUI is marked up in one .ui file. Models of each tab/major function will be passed the MainWindow and 
        will ask for the markup identifiers they expect directly.
        """

        self.octa_controller = OCTAController(self)  # Pass MainWindow to controllers

        self.show()



if __name__ == '__main__':
    appctxt = ApplicationContext()       # 1. Instantiate ApplicationContext
    window = MainWindow()
    window.resize(860, 920)
    window.setMinimumSize(860,920)
    window.setMaximumSize(860,920)
    window.show()
    exit_code = appctxt.app.exec_()      # 2. Invoke appctxt.app.exec_()
    sys.exit(exit_code)