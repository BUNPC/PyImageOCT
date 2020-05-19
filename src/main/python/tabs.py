from PyQt5.QtWidgets import QWidget, QGridLayout

from src.main.python.widgets.panels import FilePanel, RepeatsPanel, ConfigPanel, ScanPanelOCTA, ControlPanel
from src.main.python.widgets.plot import BScanView, SpectrumView
from src.main.python.controllers import SpectralRadarController

from PyQt5.QtCore import QThread, QObject, pyqtSignal, pyqtSlot

import numpy as np
from queue import Queue


class ScanWorker(QObject):

    started = pyqtSignal()
    finished = pyqtSignal()
    frame_completed = pyqtSignal()

    def __init__(self, controller, acquired_queue, frames_to_acquire=2147483647):

        super(QObject, self).__init__()

        self.controller = controller
        self.queue = acquired_queue
        self.frames_to_acquire = frames_to_acquire
        self.frames_acquired = 0

        self.abort_flag = False

    def acquistion(self):

        self.started.emit()
        print("Started")

        while self.frames_acquired < self.frames_to_acquire and self.abort_flag is not True:

            # Acquisition code here
            frame = np.empty([2048, 10, 10], dtype=np.uint16)
            for i in range(10):
                for j in range(10):
                    frame[:, i, j] = (np.sinc(2048)*np.random.random(2048)).astype(np.uint16)

            self.queue.put(frame)

            self.frame_completed.emit()

            print(self.queue.qsize())

            self.frames_acquired += 1

        self.finished.emit()


class TabOCTA(QWidget):

    def __init__(self, parent=None):
        super(QWidget, self).__init__()

        self.parent = parent

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
        self.layout.addWidget(self.bscanView, 0, 1, 3, 1)

        self.spectrumView = SpectrumView()
        self.layout.addWidget(self.spectrumView, 3, 1, 2, 1)

        self.setLayout(self.layout)

        self.controller = SpectralRadarController()
        self.raw_queue = Queue()

        self.scanWorker = None
        self.scanThread = None

        self.controlPanel.connect_to_scan(self._start_scan)
        self.controlPanel.connect_to_stop(self._stop_scan)

    def _start_scan(self):

        # Have to connect all this and instantiate new workers and threads each time
        # TODO figure out if that's not necessary

        self.scanWorker = ScanWorker(self.controller, self.raw_queue)
        self.scanThread = QThread()
        self.scanWorker.moveToThread(self.scanThread)

        self.scanThread.started.connect(self.scanWorker.acquistion)
        self.scanWorker.started.connect(self.controlPanel.set_scanning)

        self.scanWorker.finished.connect(self.controlPanel.set_idle)
        self.scanWorker.finished.connect(self.scanThread.quit)

        self.scanWorker.frame_completed.connect(self.spectrumView.update)
        self.scanWorker.frame_completed.connect(self.bscanView.update)

        # Actually start the thread:
        self.parent.status_log("Scanning...")
        self.scanThread.start()

    def _stop_scan(self):
        self.scanWorker.abort_flag = True
        self.parent.status_log("Aborting...")


