from fbs_runtime.application_context.PyQt5 import ApplicationContext
from PyQt5.QtWidgets import QApplication
from PyQt5.QtWidgets import QWidget
from PyQt5.QtWidgets import QTabWidget
from PyQt5.QtWidgets import QGridLayout

import sys

from PyQt5 import QtCore

from src.main.python.PyImage import SpectralRadarControl, Widgets

# Something wrong with these-- intended to fix DPI scaling issues but they make it worse
'''
if hasattr(QtCore.Qt, 'AA_EnableHighDpiScaling'):
    PyQt5.QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)

if hasattr(QtCore.Qt, 'AA_UseHighDpiPixmaps'):
    PyQt5.QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)
'''

QtInstance = QtCore.QCoreApplication.instance()

# Supposed to allow IPython kernal to recover from closing of app
if QtInstance is None:
    QtInstance = QApplication(sys.argv)

class Main(QTabWidget):
    '''
    At the highest level, the GUI consists of tabs which organize various scanning/acquisition modes, similar to the
    OCT Imaging Freeform SDK program developed in LabView
    '''

    def __init__(self, parent=None):
        super().__init__(parent)

        self.figEight = SpectralRadarControl.FigureEight(parent=self)

        self.addTab(self.figEight.tab, 'Figure-8 Motion Quantification')

        self.windowTitle = 'PyOCT V.0.1.5'
        self.setWindowTitle(self.windowTitle)

        # self.setMinimumHeight(550)
        # self.setMinimumWidth(800)
        #
        # self.setMaximumHeight(550)
        # self.setMaximumWidth(1200)

    def closeEvent(self, event):
        self.figEight.close()

# Qt main loop
if __name__ == '__main__':
    appctxt = ApplicationContext()
    window = Main()
    window.show()
    exit_code = appctxt.app.exec_()
    sys.exit(exit_code)
