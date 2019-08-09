import numba
from multiprocessing import Queue, Pool, Process, Value, Array
from queue import Full, Empty

class ProcessEight:

    def __init__(self,controller):

        pass

    def initialize(self):

        self._raw_frames = Queue(maxsize=self._maxframes)
        self._proc_frames = Queue(maxsize=self._maxframes)
        self._displacements = Queue(maxsize=self._maxdisplacements)

    def put_frame(self,frame):
        self._raw_frames.put(frame)

    def __preprocess_frames(self):

        try:

            f = self._raw_frames.get()

        except Empty:

            pass

