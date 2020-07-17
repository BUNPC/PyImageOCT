from PyQt5.QtWidgets import QWidget, QGridLayout

from src.main.python.widgets.panels import FilePanel, RepeatsPanel, ConfigPanel, ScanPanelOCTA, ControlPanel
from src.main.python.widgets.plot import BScanView, SpectrumView
from src.main.python.controllers import SpectralRadarController

from PyQt5.QtCore import QThread, QObject, pyqtSignal, pyqtSlot

import numpy as np
from queue import Queue

class AcqWorker(QObject):

    started = pyqtSignal()
    finished = pyqtSignal()
    frame_completed = pyqtSignal()

    def __init__(self, proc_queue, max_size, file_type, save_path):

        super(QObject, self).__init__()

        self.proc_queue = proc_queue
        self.max_size = max_size
        self.file_type = file_type
        self.save_path = save_path

    def exporting(self):

        self.started.emit()
        print("Saving acquired data")

        while self.proc_queue.empty is not True:

            # Do processing here

            print("Processing!")

        self.finished.emit()


class ProcWorker(QObject):

    started = pyqtSignal()
    finished = pyqtSignal()
    frame_completed = pyqtSignal()

    def __init__(self, src_queue, dst_queue):
        """
        :param src_queue: Queue of raw frames
        :param dst_queue: Queue where processed frames will be put
        """

        super(QObject, self).__init__()

        self.raw_queue = src_queue
        self.proc_queue = dst_queue

    def processing(self):

        self.started.emit()
        print("Processing")

        while self.raw_queue.empty is not True:

            # Do processing here

            print("Processing!")

        self.finished.emit()


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

    def scanning(self):

        self.started.emit()
        print("Started")

        while self.frames_acquired < self.frames_to_acquire and self.abort_flag is not True:

            # Acquisition code here. Dummy example rn
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
        self.raw_queue = Queue()  # Queue for raw frames
        self.proc_queue = Queue()  # Queue for processed frames

        self.scanWorker = None
        self.scanThread = None

        self.procWorker = None
        self.procThread = None

        self.acqWorker = None
        self.acqThread = None

        self.controlPanel.connect_to_scan(self._start_scan)
        self.controlPanel.connect_to_stop(self._stop_scan)
        self.controlPanel.connect_to_acq(self._start_acq)

        self.scanning = False  # One bool state machine

    def _start_acq(self):
        print("Acquisiton started")

    def _stop_acq(self):
        print("Acquisition stopped")

    def _start_scan(self):

        self.scanning = True

        # Have to connect all this and instantiate new workers and threads each time
        # TODO figure out if that's not necessary

        self.scanWorker = ScanWorker(self.controller, self.raw_queue)
        self.scanThread = QThread()
        self.scanWorker.moveToThread(self.scanThread)

        self.scanThread.started.connect(self.scanWorker.scanning)
        self.scanWorker.started.connect(self.controlPanel.set_scanning)

        self.scanWorker.finished.connect(self.controlPanel.set_idle)
        self.scanWorker.finished.connect(self.scanThread.quit)

        self.scanWorker.frame_completed.connect(self.spectrumView.update)
        self.scanWorker.frame_completed.connect(self.bscanView.update)

        # Actually start the thread:
        self.parent.status_log("Scanning...")
        self.scanThread.start()

    def _stop_scan(self):

        self.scanning = False  # Flag that actually stops the thread

        self.scanWorker.abort_flag = True
        self.parent.status_log("Ready")


