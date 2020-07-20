import os
from collections import deque

import numpy as np
import pyqtgraph
from PyQt5 import uic
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QWidget, QRadioButton, QCheckBox, QSlider, QLabel


class SpectrumPlotWidget(pyqtgraph.PlotWidget):

    def __init__(self):
        super(pyqtgraph.PlotWidget, self).__init__()


class OCTViewer(pyqtgraph.GraphicsLayoutWidget):

    def __init__(self):
        super().__init__()

        self._viewbox = self.addViewBox(row=1, col=1)
        self._viewbox.setAspectLocked()
        self.image = pyqtgraph.ImageItem()
        self._viewbox.addItem(self.image)

    def setImage(self, img):
        self.image.setImage(np.rot90(img))

    def setLevels(self, levels):
        self.image.setLevels(levels)


class SpectrumView(QWidget):

    def __init__(self):
        super(QWidget, self).__init__()
        ui = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) + "\\ui\\spectrumplotter.ui"
        uic.loadUi(ui, self)

        plotwidget_placeholder = self.findChild(QWidget, "widgetSpec")
        plotwidget_placeholder_layout = plotwidget_placeholder.parent().layout()
        self.plotWidget = SpectrumPlotWidget()
        plotwidget_placeholder_layout.replaceWidget(plotwidget_placeholder, self.plotWidget)

    def update(self):
        print("SpectrumView update")


class BScanView(QWidget):

    def __init__(self):

        super(QWidget, self).__init__()
        ui = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) + "\\ui\\bscanplotter.ui"  # Double escape dir
        uic.loadUi(ui, self)

        # Add pyqtgraph subwidget
        viewer_placeholder = self.findChild(QWidget, "widget3D")
        viewer_placeholder_layout = viewer_placeholder.parent().layout()
        self.viewer = OCTViewer()
        viewer_placeholder_layout.replaceWidget(viewer_placeholder, self.viewer)

        self._slice_timer = QTimer()
        self._display_update_timer = QTimer()
        self._slice_slider = self.findChild(QSlider, "sliderSlice")
        self._enface_radio = self.findChild(QRadioButton, "radioEnface")
        self._scan_check = self.findChild(QCheckBox, "checkScanThrough")
        self._db_check = self.findChild(QCheckBox, "checkDb")
        self._mip_check = self.findChild(QCheckBox, "checkMIP")
        self.slice_label = self.findChild(QLabel, "sliceLabel")

        # Initial conditions
        self._frame_shape = []
        self._current_frame = []
        self._current_slice = -1
        self._slice_max = 0
        self.enface_enabled = None  # Intentionally public

        self._buffer = deque(maxlen=16)  # TODO implement parameter for maxlen

        self._slice_slider.valueChanged.connect(self._slider_change)
        self._enface_radio.toggled.connect(self._set_orientation)
        self._scan_check.toggled.connect(self._set_scan_toggle)
        self._mip_check.toggled.connect(self._mip_changed)
        self._db_check.toggled.connect(self._db_changed)
        self._slice_timer.timeout.connect(self._slice_thru_advance)
        self._display_update_timer.timeout.connect(self._update_display)

        for i in range(32):
            self.enque_frame(500 * np.random.random([40, 20, 20]))  # For testing only!

    def enque_frame(self, frame):
        """
        Enques a 3D OCT frame for display. Will overwrite previously queued undisplayed frames if the circular queue
        is full. The rate at which the display updates and displays a new frame from the buffer can be set with
        set_update_rate(rate_in_hz). Default is 60.
        :param frame: 3D OCT data frame
            First dimension: A-line, z
            Second dimension: B-line, fast axis
            Third dimension (optional): Slow axis
        :return: 0 on success
        """
        self._buffer.append(np.array(frame).astype(np.complex64))
        self._frame_shape = np.shape(frame)
        if not self._display_update_timer.isActive():  # If buffer emptied out or this is startup
            if self._current_slice is -1:  # On initial startup only
                self._set_slice(1)  # Slice 1 is index 0!
            self._set_orientation()
            self._display_update_timer.start(16)  # > 60 FPS. TODO implement parameter
        print('Frame appended. Frames in buffer:', len(self._buffer))

    def get_frame_shape(self):
        """
        Gets shape of currently displayed 3D data
        :return: 3D shape array
        """
        return self._frame_shape

    def _slice_thru_advance(self):
        if self._current_slice is self._slice_max:
            self._set_slice(1)
        else:
            self._set_slice(self._current_slice + 1)

    def _update_display(self):

        try:
            f = self._buffer.pop()
            print('Frame popped. Frames in buffer:', len(self._buffer))
        except IndexError:  # If deque is empty
            f = self._current_frame
            print('Buffer empty. Stopping refresh timer until a new frame is added')
            self._display_update_timer.stop()

        self._current_frame = f

        self._draw_frame()  # Draws the frame. This is called from GUI callbacks as well

    def _draw_frame(self):
        frame = self._current_frame
        frame = np.abs(frame)  # TODO make abs vs real vs imag etc parameters
        try:
            if self._db_check.isChecked():
                frame = 20 * np.log10(frame)
            if self.enface_enabled:  # Enface mode
                if self._mip_check.isChecked():  # MIP
                    self.viewer.setImage(np.max(frame, axis=0))  # Axial MIP
                else:
                    self.viewer.setImage(frame[self._current_slice - 1, :, :])  # Slice is indexed from 1
            else:  # B-scan mode
                if self._mip_check.isChecked():  # MIP
                    self.viewer.setImage(np.max(frame, axis=2))  # MIP across slow axis
                else:
                    self.viewer.setImage(frame[:, :, self._current_slice - 1])
            return 0
        except IndexError:  # Occurs when a new frame has been added with different dimensions
            return -1

    def _set_scan_toggle(self):
        if self._scan_check.isChecked():
            self._slice_slider.setEnabled(False)
            self._slice_timer.start(64)  # TODO implement parameter
            print("Automatic scan")
            self._slice_slider.blockSignals(True)
        else:
            self._slice_slider.setEnabled(True)
            self._slice_timer.stop()
            print("Manual control")
            self._slice_slider.blockSignals(False)

    def _mip_changed(self):
        if self._mip_check.isChecked():
            self._slice_slider.setEnabled(0)
            self._scan_check.setEnabled(0)
            self.slice_label.setEnabled(0)
            self._slice_timer.stop()
            print('MIP mode entered')
        else:
            self._slice_slider.setEnabled(1)
            self._scan_check.setEnabled(1)
            self.slice_label.setEnabled(1)
            self._set_scan_toggle()  # Resume normal scan control
            print('MIP mode exit')
        self._draw_frame()

    def _db_changed(self):
        self._draw_frame()

    def _set_orientation(self):
        if self._enface_radio.isChecked():
            self.enface_enabled = True
            self._slice_max = self._frame_shape[0]  # Slice through z
        else:
            self.enface_enabled = False
            self._slice_max = self._frame_shape[2]  # Slice through slow axis
        if self._current_slice > self._slice_max:  # If current slice too big for new orientation
            self._set_slice(self._frame_shape[2])
        else:
            self._set_slice(self._current_slice)  # Update slice label
        self._slice_slider.setMaximum(self._slice_max)

    def _set_slice(self, index):
        print('Current slice', index)
        self._current_slice = index  # Only place where this assignment is allowed!
        self.slice_label.setText(str(self._current_slice) + "/" + str(self._slice_max))
        self._slice_slider.setValue(self._current_slice)  # Slider not connected to this method on auto slice
        self._draw_frame()

    def _slider_change(self):
        self._set_slice(self._slice_slider.value())
