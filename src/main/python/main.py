import os
import sys

from PyQt5 import uic
from PyQt5.QtWidgets import QMainWindow, QWidget, QStatusBar
from fbs_runtime.application_context.PyQt5 import ApplicationContext

from src.main.python.tabs import TabOCTA


class MainWindow(QMainWindow):

    def __init__(self):

        super(MainWindow, self).__init__()
        ui = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))+"\\ui\\MainWindow.ui"
        uic.loadUi(ui, self)

        self.statusBar = self.findChild(QStatusBar, "MainStatusBar")
        self.status_log("Getting set up...")

        self._tabs = []

        tab_octa_placeholder = self.findChild(QWidget, "tabOCTA")
        tab_octa_placeholder_layout = tab_octa_placeholder.parent().layout()
        self.tabOCTA = TabOCTA(parent=self)
        tab_octa_placeholder_layout.replaceWidget(tab_octa_placeholder, self.tabOCTA)

        self._tabs.append(self.tabOCTA)

        self.status_log("Ready")

        self.show()

    def status_log(self, msg):
        self.statusBar.showMessage(msg)

    def closeEvent(self, event):
        for tab in self._tabs:
            tab.close()
        event.accept()


if __name__ == '__main__':
    appctxt = ApplicationContext()       # 1. Instantiate ApplicationContext
    window = MainWindow()
    # window.resize(860, 920)
    # window.setMinimumSize(860,920)
    # # window.setMaximumSize(860,920)
    window.show()
    exit_code = appctxt.app.exec_()      # 2. Invoke appctxt.app.exec_()
    sys.exit(exit_code)