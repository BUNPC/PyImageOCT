from PyQt5.QtGui import QCloseEvent
from PyQt5.QtWidgets import QWidget, QGridLayout

from src.main.python.PyScanPattern.ScanPattern import RasterScanPattern
from src.main.python.widgets.panels import FilePanel, RepeatsPanel, ConfigPanel, ScanPanelOCTA, ControlPanel
from src.main.python.widgets.plot import BScanView, SpectrumView
from src.main.python.controllers import SpectralRadarController, NIController

from PyQt5.QtCore import QThread, QObject, pyqtSignal, pyqtSlot

import matplotlib.pyplot as plt

import numpy as np
from collections import deque
from queue import Queue

import numba
import time


@numba.jit(forceobj=True)
def process_oct(raw, alines, blines, window, n=2048):

    spatial = np.empty([int(n/2), alines, blines], dtype=np.complex64)
    window = np.hanning(n)

    k = 0
    for j in numba.prange(blines):

        for i in numba.prange(alines):

            spatial[:, i, j] = np.fft.ifft(raw[n*k:n*k + n] * window)[0:int(n/2)]
            k += 1

    return spatial


class PyImageOCTWorker(QObject):

    def __init__(self, parent):
        """
        Managing worker that gets directs processed frames to the save or display buffers
        :param parent: The parent PyImageOCT tab GUI. Will pass handles to the relevant buffers with get_buffers()
        """
        super(QObject, self).__init__()

        self._msg_queue = Queue()  # Queue for messages from other threads or the parent GUI tab TODO implement
        self._parent = parent
        [self._raw_buffer, self._proc_buffer, self._export_buffer] = parent.get_buffers()
        [self._3D_display, self._spectrum_display] = parent.get_displays()

        self.started = pyqtSignal()
        self.paused = pyqtSignal()
        self.error = pyqtSignal()

        self.abort_flag = False

    def start(self):

        i = 0
        interval = 30
        window = np.hanning(2048)

        while not self.abort_flag:

            try:

                f = self._raw_buffer.pop()

                if i % interval == 0:
                    self._spectrum_display.enqueue_frame(f[0:2048])

                    # TODO pass to a processing object
                    p = process_oct(f, self._parent.scan_dim[0], self._parent.scan_dim[1], window)

                    self._3D_display.enqueue_frame(p[0:500, :, :])

                i += 1

            except IndexError:
                continue




class GrabWorker(QObject):
    started = pyqtSignal()
    finished = pyqtSignal()
    frame_grabbed = pyqtSignal()

    def __init__(self, grab_fn, put_fn, grab_fn_args=[], put_fn_args=[], frames_to_grab=np.inf):
        """
        Worker that calls grab_fn and appends result to a buffer using put_fn
        :param grab_fn: Method of an API controller that returns handle to frame from camera. Takes
        list of arguments grab_fn_args.
        :param put_fn: Method of a buffer object that takes the result of grab_fn + frab_fn_args
        :param grab_fn_args: List of arguments passed to grab_fn
        :param put_fn_args: List of arguments paasseed to put_fn in addition to return value of grab_fn
        :param frames_to_grab: The thread will execute until this number has been reached. Defaults to np.inf
        """

        super(QObject, self).__init__()
        # Public
        self.frames_grabbed = 0
        self.frames_to_grab = frames_to_grab

        # Protected
        self._grab_fn = grab_fn
        self._grab_fn_args = grab_fn_args
        self._put_fn = put_fn
        self._put_fn_args = put_fn_args

        self.abort_flag = False

    @pyqtSlot()
    def start(self):
        self.started.emit()
        print("GrabWorker: started!")

        while self.abort_flag is not True:
            # print('GrabWorker: grabbing frame', self.frames_grabbed)
            try:
                self._put_fn(self._grab_fn(*self._grab_fn_args), *self._put_fn_args)
            except OSError:
                print('GrabWorker: exiting due to illegal grab attempt...')
                self.finished.emit()
                self.thread().quit()
                return
            self.frames_grabbed += 1  # TODO implement in a way that won't overflow
            self.frame_grabbed.emit()

        self.finished.emit()
        self.thread().quit()


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

        # self.controller = SpectralRadarController()
        self.controller = NIController('img0',  # Camera name
                                       'Dev1',  # Scan DAQ name
                                       'ao0',  # Camera trigger ch name
                                       'ao1',  # X galvo ch name
                                       'ao2')  # Y galvo ch name

        self._raw_queue = deque(maxlen=32)  # Queue for unprocessed frames TODO add max size
        self._proc_queue = deque(maxlen=32)  # Queue for processed frames
        self._export_queue = deque(maxlen=32)  # Queue for acquired frames

        self._grab_worker = None
        self._grab_thread = None

        self._pyimageoct_worker = None
        self._pyimageoct_thread = None

        self.scanning = False  # One bool state machine

        # TODO implement proper scan pattern stuff
        self.alines = 600
        self.blines = 1
        self._scan_pattern = RasterScanPattern()
        self._scan_pattern._generate_raster_scan(self.alines, self.blines)
        self.scan_dim = [self.alines, self.blines]

        self.controlPanel.connect_to_scan(self._start_scan)
        self.controlPanel.connect_to_stop(self._stop_scan)
        self.controlPanel.connect_to_acq(self._start_acq)

        err = self.controller.initialize()

        self._launch_manager_thread()

    def get_buffers(self):
        """
        Get the buffers associated with this imaging mode
        :return: [raw_buffer, processed_buffer, export_buffer]
        """
        return [self._raw_queue, self._proc_queue, self._export_queue]

    def get_displays(self):
        """
        Get display objects associated with this imaging mode
        :return: [bscan_display, spectrum_display]
        """
        return [self.bscanView, self.spectrumView]

    def close(self):
        print('Closing!')
        if self.controller.mode is 1:
            self.controller.stop_scan()
        self.controller.close()

    def _start_acq(self):
        self.controller.start_scan()
        print("Acquisiton started")

    def _start_scan(self):
        self.scanning = True
        self.controller.set_scanpattern(self._scan_pattern)
        self.controller.start_scan()
        self._launch_grab_thread()

    def _start_display(self):
        self.spectrumView.start_refresh()
        self.bscanView.start_refresh()

    def _stop_scan(self):
        self._grab_worker.abort_flag = True
        self._grab_thread.wait(500)  # Abort the thread and wait for frame grabbing to stop
        self._end_scan()

    def _end_scan(self):
        self.controller.stop_scan()
        self.controlPanel.set_idle()
        self.spectrumView.stop_refresh()
        self.bscanView.stop_refresh()
        self.scanning = False

    def _launch_grab_thread(self):
        self._grab_thread = QThread()
        self._grab_worker = GrabWorker(self.controller.grab,
                                       self._raw_queue.append)
        self._grab_worker.moveToThread(self._grab_thread)
        self._grab_thread.started.connect(self._grab_worker.start)
        self._grab_worker.frame_grabbed.connect(self._start_display)
        self._grab_worker.finished.connect(self._end_scan)
        self._grab_thread.start()

    def _launch_manager_thread(self):
        self._pyimageoct_thread = QThread()
        self._pyimageoct_worker = PyImageOCTWorker(self)
        self._pyimageoct_worker.moveToThread(self._pyimageoct_thread)
        self._pyimageoct_thread.started.connect(self._pyimageoct_worker.start)
        self._pyimageoct_thread.start()
