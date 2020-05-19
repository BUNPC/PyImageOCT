from PyQt5.QtWidgets import QWidget, QGridLayout

from src.main.python.widgets.panels import FilePanel, RepeatsPanel, ConfigPanel, ScanPanelOCTA, ControlPanel
from src.main.python.widgets.plot import BScanView, SpectrumView


class TabOCTA(QWidget):

    def __init__(self, parent=None):
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

        self.bscanView = BScanView()
        self.layout.addWidget(self.bscanView, 0, 1, 2, 1)

        self.spectrumView = SpectrumView()
        self.layout.addWidget(self.spectrumView, 2, 1, 4, 1)

        self.setLayout(self.layout)
