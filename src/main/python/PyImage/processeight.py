import numba
import numpy as np
from PyImage.OCT import Worker
from multiprocessing import Queue, Pool, Process, Value, Array
from queue import Full, Empty

from concurrent.futures import ThreadPoolExecutor

class ProcessEight:

    def __init__(self, controller):

        self.controller = controller
        self._threads = []

        self.dropped_frames = 0

        # TODO un-hardcode
        self._window_size = 4
        self._maxframes = 4
        self._maxdisplacements = 2
        self._display_interval = 6
        self._counter = 0

        self._raw_frames = Queue()
        self._proc_frames = Queue()
        self._displacements = Queue(maxsize=self._maxdisplacements)

        self._display_frames = Queue()

        self._preprocessing_executor = None

    def clear(self):

        for q in [self._raw_frames, self._proc_frames, self._displacements, self._display_frames]:

            while not q.empty():

                q.get()

    def put_frame(self, frame):

        try:

            self._raw_frames.put(frame)

        except Full:

            pass

    def get_frame(self):

        try:

            f = self._raw_frames.get()

        except Empty:

            f = []

        return f

    def put_processed_frame(self, frame):

        try:

            self._proc_frames.put(frame)

        except Full:

            pass

    def get_proccessed_frame(self):

        try:

            f = self._proc_frames.get()

        except Empty:

            f = []

        return f

    def put_display_frame(self, b, s):

        try:

            self._display_frames.put([b, s])

        except Full:

            pass

    def get_display_frame(self):

        try:

            bs = self._display_frames.get()

        except Empty:

            bs = []

        return bs

    def start_preprocessing(self):

        # Calculate or obtain processing parameters from controller
        x = self.controller._scanpattern_aperb
        n = len(self.controller.scanpattern_x)
        b1 = self.controller.scanpattern_b1
        b2 = self.controller.scanpattern_b2
        window = self.controller.get_apodwindow()

        # Compile jit functions
        self._prejit(x,n,b1,b2,window)

        # Define helper class which manages pool of processor threads
        self._preprocessing_executor = PreprocessorPoolExecutor(x,n,b1,b2,window)

        self._preprocessing_thread = Worker(func=self._raw_window_consumer)
        self._preprocessing_thread.start()

    def _prejit(self,x,n,b1,b2,window):
        """
        Makes a few mock calls to the jitted functions so they are compiled in time for actual processing
        """
        for i in range(10):
            mockframe = np.ones(2048*n)
            preprocess_jitted(mockframe,x,n,b1,b2,window)

    def _raw_window_consumer(self):
        """
        Preprocesses batch of frames in window concurrently and waits for ordered result before returning
        Puts processed frames into display and processed queues
        """

        futures = [ [] for k in range(self._window_size) ]

        for i in range(self._window_size):

            grabbed = False

            while not grabbed:

                f = self.get_frame()

                if f is not []:
                    grabbed = True

            futures[i] = self._preprocessing_executor(f)

        for i in range(self._window_size):

            result = futures[i].result()

            self.put_processed_frame(result)

            self._counter += 1

            if self._counter % self._display_interval == 0:

                self.put_display_frame(result,f[0:2048])


class PreprocessorPoolExecutor:
    """
    Helper class which wraps pool of preprocessor threads. Call to submit a new job
    """

    def __init__(self, x, n, b1, b2, window, pool_size=4):

        self._pool = ThreadPoolExecutor(pool_size)
        self._static_args = [x, n, b1, b2, window]

    def __call__(self, frame):
        args = (frame, *self._static_args)
        return self._pool.submit(preprocess_jitted,*args)


# @numba.jit(forceobj=True, fastmath=True, cache=True)  # Array creation cannot be compiled
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

    flat = np.squeeze(raw.flatten())
    reshape_jitted(flat, n, b1, b2, reshaped, mean)

    np.divide(mean, n, out=mean)
    np.divide(window, mean, out=apod)

    apodize_fft_jitted(reshaped, x, apod, im)  # TODO implement lambda->k interp

    return im

"""
Subfunction of preprocess that can be compiled in nopython mode
"""
# @numba.njit(fastmath=True)
def reshape_jitted(flat, N, b1, b2, reshaped, mean):
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

@numba.jit(forceobj=True, parallel=True,fastmath=True)  # np.fft cannot be compiled
def apodize_fft_jitted(reshaped,X,apod,im):
    """
    reshaped: reshaped uint16 data
    X: total number of A-scans in the B-scan equal to 2nd dimension of reshaped
    apod: apodization window (usually a 2048 hanning window)
    im: empty array into which the fourier transformed complex data is placed
    """
    for i in numba.prange(X):
        for j in numba.prange(2):
            np.multiply(reshaped[:,i,j],apod,reshaped[:,i,j])
            im[:,i,j] = np.fft.ifft(reshaped[:,i,j])[0:1024]






