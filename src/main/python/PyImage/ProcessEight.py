import numba
from threading import Thread, Event
from multiprocessing import Queue, Pool, Process, Value, Array
from queue import Full, Empty

class ProcessEight:

    def __init__(self,controller):

        self.controller = controller
        self._threads = []

        self.dropped_frames = 0

    def initialize(self):

        self._raw_frames = Queue(maxsize=self._maxframes)
        self._proc_frames = Queue()
        self._displacements = Queue(maxsize=self._maxdisplacements)

    def put_frame(self,frame):

        try:

            self._raw_frames.put(frame)

        except Full:

            self.dropped_frames += 1

    def get_proccessed_frame(self):

        try:

            self._proc_frames.get()


class PreprocessingWorker(Thread):

    def __init__(self, controller, raw_queue, proc_queue):

        super(PreprocessingWorker, self).__init__()

        self.controller = controller
        self._raw_queue = raw_queue
        self._proc_queue = proc_queue

        self.stop = Event()

    def run(self):

        x = len(self.controller.scanpattern_b1)
        n = len(self.controller.scanpattern_x)
        b1 = self.controller.scanpattern_b1
        b2 = self.controller.scanpattern_b2
        window = self.controller.get_apodwindow()

        while not self.stop.is_set():

            try:

                raw = self._raw_queue.get()

                proc = self.preprocess_jitted(raw, x, n, b1, b2, window)

                self._proc_queue.put(proc)

            except Empty:

                continue

    def join(self, timeout=None):
        self.stoprequest.set()
        super(WorkerThread, self).join(timeout)

    @numba.jit(forceobj=True, fastmath=True, cache=True)  # Array creation cannot be compiled
    def preprocess_jitted(raw, x, n, b1, b2, window):
        """
        :argument raw: raw uint16 data from Telesto from single frame grab of one B-Scan
        :argument x: total number of A-scans in the B-scan
        :argument n: total number of A-scans in the figure 8 (Not to be confused with controller's N!)
        :argument b1: matrix of indices which make up first B-scan
        :argument b2: matrix of indices which make up second B-scan
        :argument window: apodization window (usually a 2048 Hanning window)
        :return im Spatial domain OCT data
        """

        reshaped = np.empty([2048, x, 2])
        mean = np.zeros(2048)
        apod = np.empty(2048)
        im = np.empty([1024, x, 2], dtype=np.complex64)

        reshape_jitted(raw, n, b1, b2, reshaped, mean)

        np.divide(mean, n, out=mean)
        np.divide(window, mean, out=apod)

        apodize_fft_jitted(reshaped, x, apod, im)  # TODO implement lambda->k interp

        return im

    @numba.njit(fastmath=True, cache=True)
    """
    Subfunction of preprocess that can be compiled in nopython mode
    """
    def reshape_jitted(raw, N, b1, b2, reshaped, mean):
        flat = raw.flatten()
        ib1 = 0
        ib2 = 0
        for i, n in enumerate(np.arange(0, N * 2048, 2048)):
            if b1[i]:
                this = flat[n:n + 2048]
                reshaped[:, ib1, 0] = this
                np.add(this, mean, mean)
                ib1 += 1

            elif b2[i]:
                this = flat[n:n + 2048]
                reshaped[:, ib2, 1] = this
                np.add(this, mean, mean)
                ib2 += 1
            else:
                this = flat[n:n + 2048]
                np.add(this, mean, mean)
        np.divide(mean, N, mean)







