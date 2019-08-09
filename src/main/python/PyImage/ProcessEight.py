import numba
from multiprocessing import Queue, Pool, Process, Value, Array
from queue import Full, Empty

class ProcessEight:

    def __init__(self,controller):

        self.controller = controller
        self._threads = []

    def initialize(self):

        self._raw_frames = Queue(maxsize=self._maxframes)
        self._proc_frames = Queue(maxsize=self._maxframes)
        self._displacements = Queue(maxsize=self._maxdisplacements)

    def put_frame(self,frame):

        try:

            self._raw_frames.put(frame)

        except Full:

            pass

    def get_raw_frame(self):

        try:

            return self._raw_frames.get()

        except Empty:

            return 0

    def __preprocess_frames(self):





