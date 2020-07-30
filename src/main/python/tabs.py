from src.main.python.PyScanPattern.ScanPattern import RasterScanPattern
from src.main.python.widgets.panels import FilePanel, RepeatsPanel, ConfigPanel, ScanPanelOCTA, ControlPanel
from src.main.python.widgets.plot import BScanView, SpectrumView
from src.main.python.controllers import SpectralRadarController, NIController

from PyQt5.QtWidgets import QWidget, QGridLayout, QDialog
from PyQt5.QtCore import QThread, QObject, pyqtSignal, pyqtSlot, Qt

import numpy as np
from collections import deque

import matplotlib
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as Canvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as Toolbar
from matplotlib.figure import Figure

import numba
import pyfftw
import time

matplotlib.use('Qt5Agg')

def plan_1d_r2c_fftw(fft_input_len):
    start = time.time()

    in_arr = pyfftw.empty_aligned(fft_input_len, dtype='float32')
    out_arr = pyfftw.empty_aligned(int(fft_input_len / 2 + 1), dtype='complex64')

    fftw_obj = pyfftw.FFTW(in_arr,
                           out_arr,
                           # direction='FFT_FORWARD',
                           flags=['FFTW_PATIENT']
                           )

    print('Planned fftw', time.time() - start, 'elapsed')

    return in_arr, out_arr, fftw_obj


# @numba.jit(parallel=True, forceobj=True)
def process_oct_b(raw, n_alines, window, fft, n=2048):
    spatial = np.empty([int(n/2), n_alines], dtype=np.complex64)
    for i in numba.prange(n_alines):
        fft_in = pyfftw.byte_align(raw[n*i:n*i + n] * window, dtype='float32')
        fft_out = pyfftw.empty_aligned(int(n / 2) + 1, dtype='complex64')
        fft.update_arrays(fft_in, fft_out)
        fft()
        spatial[:, i] = fft_out[1::]

    return spatial


class ProcessWorker(QObject):

    started = pyqtSignal()
    finished = pyqtSignal()
    frame_processed = pyqtSignal()

    def __init__(self, parent, src_buffer, dst_buffer, spec_display_method=None, b_display_method=None, n=2048, window=np.hanning(2048)):
        super(QObject, self).__init__()

        self._src_buffer = src_buffer
        self._dst_buffer = dst_buffer
        self._spec_display_method = spec_display_method
        self._b_display_method = b_display_method
        self._window = window
        self._n = n
        fft_in, fft_out, self._fft = plan_1d_r2c_fftw(self._n)

        self.parent = parent
        self.abort_flag = False

    def start(self):

        self.started.emit()

        while self.abort_flag is not True:

            start = time.time()
            frame = np.empty([int(self._n/2), self.parent.alines, self.parent.blines], dtype=np.complex64)

            i = 0
            while i < self.parent.blines:
                if self._src_buffer:
                    b = self._src_buffer.pop()
                    if self._spec_display_method is not None:
                        self._spec_display_method(b[2048:4096])
                        if b is not []:
                            frame[:, :, i] = process_oct_b(b,
                                                           self.parent.alines,
                                                           self._window,
                                                           self._fft)
                            i = i + 1
                            # print('ProcessWorker: Processed B-line', i, 'of', self.parent.blines)


            self._dst_buffer.append(frame)
            if self._b_display_method is not None:
                self._b_display_method(frame)
            elapsed = time.time() - start
            print('ProcessWorker: Frame appended. A-line rate',
                  (self.parent.alines*self.parent.blines) / elapsed, 'Hz')
            self.frame_processed.emit()

        self.finished.emit()


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
                print('GrabWorker: illegal grab attempt... frame is unavailable or camera is improperly configured')
                # self.finished.emit()
                # self.thread().quit()
                return
            self.frames_grabbed += 1  # TODO implement in a way that won't overflow
            # self.frame_grabbed.emit()

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
        self.scanPanel.commit_button.released.connect(self._commit_scan_pattern)
        self.scanPanel.preview_button.released.connect(self._scan_pattern_plot)

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

        # TODO implement proper scan pattern init stuff
        # Don't change here on startup! Use GUI!
        self.alines = 100
        self.blines = 100
        self.scan_dim = [self.alines, self.blines]

        self._dac_fs = 400000
        self._imaq_buffers = self.blines

        # self.controller = SpectralRadarController()
        self.controller = NIController('img0',  # Camera name
                                       'Dev1',  # Scan DAQ name
                                       'ao0',  # Camera trigger ch name
                                       'ao1',  # X galvo ch name
                                       'ao2',  # Y galvo ch name
                                       dac_sample_rate=self._dac_fs,
                                       imaq_buffer_size=self._imaq_buffers)

        self._raw_buffer = deque(maxlen=100)  # Queue for unprocessed frames TODO add max size
        self._processed_buffer = deque(maxlen=100)  # Queue for unprocessed frames TODO add max size
        self._disp_bscan_buffer = self.bscanView.get_buffer()
        self._disp_spec_buffer = self.spectrumView.get_buffer()

        self._grab_worker = None
        self._grab_thread = None

        self._process_worker = None
        self._process_thread = None

        self.scanning = False  # One bool state machine

        self.controlPanel.connect_to_scan(self._start_scan)
        self.controlPanel.connect_to_stop(self._stop_scan)
        self.controlPanel.connect_to_acq(self._start_acq)

        err = self.controller.initialize(scanpattern=self.get_scanpattern())

    def setEnabled(self, val):
        self.controlPanel.setEnabled(val)
        self.scanPanel.setEnabled(val)
        self.spectrumView.setEnabled(val)
        self.bscanView.setEnabled(val)
        self.configPanel.setEnabled(val)
        self.repeatsPanel.setEnabled(val)
        self.filePanel.setEnabled(val)

    def get_buffers(self):
        """
        Get the buffers associated with this imaging mode
        :return: [raw_buffer, processed_buffer, export_buffer]
        """
        return self._raw_buffer

    def get_displays(self):
        """
        Get display objects associated with this imaging mode
        :return: [bscan_display, spectrum_display]
        """
        return [self.bscanView, self.spectrumView]

    def get_scanpattern(self):
        # TODO implement threaded/responsive
        self.alines = self.scanPanel.x_count_spin.value()
        self.blines = self.scanPanel.y_count_spin.value()
        pat = RasterScanPattern(dac_samples_per_second=self._dac_fs,
                                debug=True)
        fov2d = [self.scanPanel.x_roi_spin.value(), self.scanPanel.y_roi_spin.value()]
        # spacing2d = [self.scanPanel.x_spacing_spin.value(), self.scanPanel.y_spacing_spin.value()]
        pat.generate_raster_scan(
            self.scanPanel.x_count_spin.value(),  # A-lines
            self.scanPanel.y_count_spin.value(),  # B-lines
            # exposure_time_us=25,  # Width of trigger pulse in us
            fov=fov2d,  # FOV
            # spacing=spacing2d  # Spacing
        )
        return pat

    def close(self):
        print('Closing!')
        if self.controller.mode is 1:
            self.controller.stop_scan()
        self.controller.close()

    @pyqtSlot()
    def _scan_pattern_plot(self):
        # TODO implement in pyqtgraph, matplotlib is slow
        pat = self.get_scanpattern()
        x = pat.get_x()
        y = pat.get_y()
        exposures = pat.get_trigger()
        scan_exposure_starts = pat.get_exposure_starts()
        print('Scan pattern preview')

        dlg = QDialog(self)
        dlg.f = Figure()
        dlg.canvas = Canvas(dlg.f)
        dlg.toolbar = Toolbar(dlg.canvas, dlg)
        dlg.layout = QGridLayout()
        dlg.layout.addWidget(dlg.toolbar)
        dlg.layout.addWidget(dlg.canvas)
        dlg.setLayout(dlg.layout)

        ax_signal_x = dlg.f.add_subplot(4, 1, 1)
        ax_signal_y = dlg.f.add_subplot(4, 1, 2)
        ax_signal_cam = dlg.f.add_subplot(4, 1, 3)

        ax_signal_x.plot(x, label='x-galvo')
        ax_signal_y.plot(y, label='y-galvo')
        ax_signal_cam.plot(exposures*.5, label='cam trigger')

        ax_spatial = dlg.f.add_subplot(4, 1, 4)

        ax_spatial.plot(x, y)
        ax_spatial.scatter(x[0], y[0], label='initial position')
        ax_spatial.scatter(x[scan_exposure_starts], y[scan_exposure_starts], label='exposures')
        # ax_spatial.legend()

        dlg.setWindowModality(Qt.ApplicationModal)
        dlg.setWindowTitle('Scan pattern preview')
        dlg.exec_()
        dlg.canvas.draw()
        dlg.show()

    @pyqtSlot()
    def _commit_scan_pattern(self):
        """
        Updates controller with new scan pattern geometry. Launches a thread to do so because it takes
        awhile to allocate the buffers (?)
        """
        self.setEnabled(False)
        self.controller.close()
        pat = self.get_scanpattern()
        self.controller.initialize(scanpattern=pat)
        self.setEnabled(True)

    def _start_acq(self):
        self.controller.start_scan()
        print("Acquisiton started")

    def _start_scan(self):
        self.scanning = True
        self._launch_process_thread()
        self.scanPanel.setEnabled(False)  # TODO implement mid-scan pattern changes
        self.controller.start_scan()
        self._launch_grab_thread()

    def _start_display(self):
        self.spectrumView.start_refresh()
        self.bscanView.start_refresh()

    def _stop_scan(self):
        self._grab_worker.abort_flag = True
        self._grab_thread.wait(500)  # Abort the thread and wait for frame grabbing to stop
        print('TabOCTA: GrabThread exited')
        self.scanPanel.setEnabled(True)
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
                                       self._raw_buffer.append)
        self._grab_worker.moveToThread(self._grab_thread)
        self._grab_worker.started.connect(self._start_display)
        self._grab_thread.started.connect(self._grab_worker.start)
        self._grab_worker.finished.connect(self._end_scan)
        self._grab_thread.start()

    def _launch_process_thread(self):
        self._process_thread = QThread()
        self._process_worker = ProcessWorker(self, self._raw_buffer,
                                             self._processed_buffer,
                                             spec_display_method=self.spectrumView.enqueue_frame,
                                             b_display_method=self.bscanView.enqueue_frame)
        self._process_worker.moveToThread(self._process_thread)
        self._process_thread.started.connect(self._process_worker.start)
        self._process_thread.start()
