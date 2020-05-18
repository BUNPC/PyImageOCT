from fbs_runtime.application_context.PyQt5 import ApplicationContext
from PyQt5.QtWidgets import QMainWindow, QWidget
from PyQt5 import uic
from src.main.python.widgets.panels import FilePanel, RepeatsPanel, ConfigPanel, ScanPanelOCTA, ControlPanel

import sys
import os

class MainWindow(QMainWindow):

    def __init__(self):

        super(MainWindow, self).__init__()
        ui = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))+"\\ui\\MainWindow.ui"
        uic.loadUi(ui, self)

        tabOCTA = self.findChild(QWidget, "tabOCTA")
        tabFig8A = self.findChild(QWidget, "tabFig8A")
        tabOCTA = self.findChild(QWidget, "tabCircleA")

        self.octa_controller = OCTAController(self)  # Pass MainWindow to controllers

        self.show()


if __name__ == '__main__':
    appctxt = ApplicationContext()       # 1. Instantiate ApplicationContext
    window = ControlPanel()
    # window.resize(860, 920)
    # window.setMinimumSize(860,920)
    # # window.setMaximumSize(860,920)
    window.show()
    exit_code = appctxt.app.exec_()      # 2. Invoke appctxt.app.exec_()
    sys.exit(exit_code)