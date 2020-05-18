from fbs_runtime.application_context.PyQt5 import ApplicationContext
from PyQt5.QtWidgets import QMainWindow, QWidget, QStatusBar, QGridLayout
from PyQt5 import uic
from src.main.python.widgets.panels import FilePanel, RepeatsPanel, ConfigPanel, ScanPanelOCTA, ControlPanel

import sys
import os


class TabOCTA(QWidget):

    def __init__(self):

        super(QWidget, self).__init__()

        self.layout = QGridLayout()

        self.filePanel = FilePanel()
        self.layout.addWidget(self.filePanel)

        self.configPanel = ConfigPanel()
        self.layout.addWidget(self.configPanel)

        self.scanPanel = ScanPanelOCTA()
        self.layout.addWidget(self.scanPanel)

        self.repeatsPanel = RepeatsPanel()
        self.layout.addWidget(self.repeatsPanel)

        self.controlPanel = ControlPanel()
        self.layout.addWidget(self.controlPanel)

        self.setLayout(self.layout)


class MainWindow(QMainWindow):

    def __init__(self):

        super(MainWindow, self).__init__()
        ui = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))+"\\ui\\MainWindow.ui"
        uic.loadUi(ui, self)

        tab_octa_placeholder = self.findChild(QWidget, "tabOCTA")
        tab_octa_placeholder_layout = tab_octa_placeholder.parent().layout()
        self.tabOCTA = TabOCTA()
        tab_octa_placeholder_layout.replaceWidget(tab_octa_placeholder, self.tabOCTA)

        self.statusBar = self.findChild(QStatusBar, "MainStatusBar")

        self.status_log("Ready")

        self.show()

    def status_log(self, msg):
        self.statusBar.showMessage(msg)


if __name__ == '__main__':
    appctxt = ApplicationContext()       # 1. Instantiate ApplicationContext
    window = MainWindow()
    # window.resize(860, 920)
    # window.setMinimumSize(860,920)
    # # window.setMaximumSize(860,920)
    window.show()
    exit_code = appctxt.app.exec_()      # 2. Invoke appctxt.app.exec_()
    sys.exit(exit_code)