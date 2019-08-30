import numpy as np
from threading import Thread, Event
import numba

"""
Misc toolbox for OCT imaging
author: sstucker
"""

class Worker(Thread):
    """
    General use thread which targets a function passed as func and calls repeatedly until joined
    """

    def __init__(self, func, args=[]):
        super(Worker, self).__init__()
        self._stop_event = Event()
        self.func = func
        self.args = args

    def run(self):

        if self.args is not []:

            while not self._stop_event.is_set():

                self.func(*self.args)  # Calls function repeatedly until thread is joined and killed

        else:

            while not self._stop_event.is_set():

                self.func()

    def join(self, timeout=None):
        self._stop_event.set()
        super(Worker, self).join(timeout)

def generate_figure8(xdistance, alinesPerX, rpt=1, padB=0, angle=np.pi / 4, flyback=20, flybackangle=np.pi / 2.58):
    """
    Generates figure-8 scan pattern positions with orthogonal cross.
    :param xdistance: Distance between adjacent scans in perpendicular B-scans
    :param alinesPerX: Number of A-lines in each orthogonal B-scan
    :param rpt: Number of times to repeat the pattern in the 1D positions array. Default is 1
    :param angle: Angle by which to rotate the figure-8 in radians. Default is pi/4
    :param flyback: Number of A-lines in each flyback loop
    :param flybackangle: Range over which to sweep flyback loops in radians
    :return: posRpt: 1D positions array for use with FreeformScanPattern; [x1,y1,x2,y2...] format
             X: X coordinates of a single figure-8
             Y: Y coordinates of a single figure-8
             B1: Indices of first B-scan
             B2: Indices of second B-scan
             N: Total number of A-scans in the pattern
             D: Distance between adjacent A-scans in the B-scans
    """
    fbscale = 2
    xsize = np.sqrt(2) / 4 * xdistance * (alinesPerX - 1)
    rotmat = np.array([[np.cos(angle), np.sin(angle)], [-np.sin(angle), np.cos(angle)]])

    if rpt > 0:
        cross = np.linspace(-xsize, xsize, alinesPerX)

        fb1 = np.linspace(-flybackangle, flybackangle, flyback, dtype=np.float32)
        fb2 = np.linspace(-flybackangle + np.pi, flybackangle + np.pi, flyback, dtype=np.float32)

        B1 = np.array([cross[::-1], cross[::-1]])
        B2 = np.array([cross, -cross])

        D = np.sqrt((B1[0][0] - B1[0][1]) ** 2 + (B1[1][0] - B1[1][1]) ** 2)

        x1 = 1.93 * fbscale * xsize * np.cos(fb1)
        y1 = fbscale * xsize * np.sin(2 * fb1)
        x2 = 1.93 * fbscale * xsize * np.cos(fb2)
        y2 = fbscale * xsize * np.sin(2 * fb2)

        X = np.concatenate([x1, B1[0], x2, B2[0]])
        Y = np.concatenate([y1, B1[1], y2, B2[1]])

        [X, Y] = np.matmul(rotmat, [X, Y])

        b1 = np.concatenate(
            [np.zeros(flyback+padB), np.ones(alinesPerX-padB), np.zeros(flyback), np.zeros(alinesPerX)]).astype(
            np.bool)
        b2 = np.concatenate(
            [np.zeros(flyback), np.zeros(alinesPerX), np.zeros(flyback+padB), np.ones(alinesPerX-padB)]).astype(
            np.bool)

        pos = np.empty(int(2 * len(X)), dtype=np.float32)

        pos[0::2] = X
        pos[1::2] = Y

        posRpt = np.tile(pos, rpt)

        N = len(X)

        return [posRpt, X, Y, b1, b2, N, D]


@numba.jit(forceobj=True)
def preprocess8(A,N,B,AlinesPerX,apod):
    """
    Compiled w numba. Reshapes raw figure-8 OCT data into a B scan
    :param A: Raw uint16 OCT spectral data
    :param N: The total number of A-scans in each figure-8
    :param B: Boolean array of indices size N indicating B-scan
    :param AlinesPerX: Number of A-scans in the B-scan
    :param apod: Apodization window
    :return: 2D Preprocessed data, [z,n] where z is axial dimension, n is lateral A-scans
    """
    flattened = A.flatten()
    pp = np.empty([2048,AlinesPerX],dtype=np.double)
    i = 0
    for n in np.arange(N):
        if B[n]:
            pp[:, i] = flattened[2048 * n:2048 * n + 2048]
            i += 1
    dc = np.mean(pp, axis=1)
    window = apod / dc
    for n in np.arange(AlinesPerX):
        pp[:,n] = pp[:, n] * window
    return pp

