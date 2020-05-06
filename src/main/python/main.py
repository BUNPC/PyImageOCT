from fbs_runtime.application_context.PyQt5 import ApplicationContext
from PyQt5.QtWidgets import QMainWindow, QWidget
from PyQt5 import uic, QtWidgets
from octacontroller import OCTAController


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

from PyQt5.QtWidgets import QGroupBox, QLineEdit, QComboBox, QToolButton, QFileDialog

class FilePanel(QGroupBox):

    def __init__(self):

        super(QGroupBox, self).__init__()

        ui = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))+"\\ui\\filePanel.ui"
        uic.loadUi(ui, self)
        self.show()

        self.exp_dir_line = self.findChild(QLineEdit, "lineExp")
        self.trial_name_line = self.findChild(QLineEdit, "lineFileName")
        self.file_type_combo = self.findChild(QComboBox, "comboFileType")
        self.file_size_combo = self.findChild(QComboBox, "comboFileSize")

        self.file_browse_button = self.findChild(QToolButton, "buttonBrowse")
        self.file_browse_button.clicked.connect(self.browse_for_file)

        self.file_dialog = QFileDialog()

        # Defaults

        self.experiment_directory = None
        self.trial_name = None
        self.file_type = None
        self.file_size = None

    def browse_for_file(self):
        #  Uses QFileDialog to select a directory to save in
        self.experiment_directory = self.file_dialog.getExistingDirectory(self, "Select Directory")
        self.exp_dir_line.setText(self.experiment_directory)

if __name__ == '__main__':
    appctxt = ApplicationContext()       # 1. Instantiate ApplicationContext
    window = FilePanel()
    window.resize(860, 920)
    window.setMinimumSize(860,920)
    # window.setMaximumSize(860,920)
    window.show()
    exit_code = appctxt.app.exec_()      # 2. Invoke appctxt.app.exec_()
    sys.exit(exit_code)