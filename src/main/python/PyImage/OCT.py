import numpy as np
import numba
from scipy.interpolate import interp1d


def generateIdealFigureEightPositions(xsize, alinesPerX, rpt=1, flyback=20):
    """
    Generates figure-8 scan pattern positions with orthogonal cross.
    :param xdistance: Distance between adjacent scans in perpendicular B-scans
    :param alinesPerX: Number of A-lines in each orthogonal B-scan
    :param rpt: Number of times to repeat the pattern in the 1D positions array
    :return: posRpt: 1D positions array for use with FreeformScanPattern; [x1,y1,x2,y2...] format
             X: X coordinates of a single figure-8
             Y: Y coordinates of a single figure-8
             B1: Indices of first B-scan
             B2: Indices of second B-scan
             N: Total number of A-scans in the pattern
             D: Distance between adjacent A-scans in the B-scans
    """
    if rpt > 0:
        cross = np.linspace(-xsize, xsize, alinesPerX)

        fb1 = np.linspace(-np.pi / 3.2, np.pi / 3.2, flyback, dtype=np.float32)
        fb2 = np.linspace(-np.pi / 3.2 + np.pi, np.pi / 3.2 + np.pi, flyback, dtype=np.float32)

        B1 = np.array([cross[::-1], cross[::-1]])
        B2 = np.array([cross, -cross])

        D = np.sqrt((B1[0][0] - B1[0][1]) ** 2 + (B1[1][0] - B1[1][1]) ** 2)

        x1 = 2 * xsize * np.cos(fb1)
        y1 = (1.18 * xsize) * np.sin(2 * fb1)
        x2 = 2 * xsize * np.cos(fb2)
        y2 = (1.18 * xsize) * np.sin(2 * fb2)

        X = np.concatenate([x1, B1[0], x2, B2[0]])
        Y = np.concatenate([y1, B1[1], y2, B2[1]])

        b1 = np.concatenate(
            [np.zeros(flyback), np.ones(alinesPerX), np.zeros(flyback), np.zeros(alinesPerX)]).astype(
            np.bool)
        b2 = np.concatenate(
            [np.zeros(flyback), np.zeros(alinesPerX), np.zeros(flyback), np.ones(alinesPerX)]).astype(
            np.bool)

        pos = np.empty(int(2 * len(X)), dtype=np.float32)

        pos[0::2] = X
        pos[1::2] = Y

        posRpt = np.tile(pos, rpt)

        N = len(X)

        return [posRpt, X, Y, b1, b2, N, D]


def fig8ToBScan(A, N, B, AlinesPerX, apod, ROI=200, lam=None, start=14):
    """
    Converts a raw array of unsigned 16 bit integer fig-8 data from Telesto to ROI of spatial domain pixels for
    live display
    :param A: Raw figure-8 data
    :param N: The total number of A-lines in the figure-8 pattern
    :param B: Boolean-type array representing indices in N-length A which make up a B-scan
    :param AlinesPerX: Number of A-lines in each B-scan
    :param apod: Apodization window. Must be 2048 in length
    :param ROI: number of pixels from the top of the B-scan to return
    :param lam: linear interpolation vector
    :param start: start of ROI, used to exclude ringing from edge of window
    :return: A 2D array of dB scale quasi-spatial data
    """
    flat = A.flatten()
    proc = np.empty([1024, AlinesPerX], dtype=np.complex64)
    interpolated = np.empty([2048,AlinesPerX])

    preprocessed = preprocess8(flat,N,B,AlinesPerX,apod)

    for n in np.arange(AlinesPerX):
        k = interp1d(lam,preprocessed[:,n])
        interpolated[:,n] = k(np.linspace(min(lam),max(lam),2048))
        proc[:, n] = np.fft.ifft(interpolated[:,n])[0:1024].astype(np.complex64)

    return 20 * np.log10(np.abs(proc[start:ROI]))

@numba.jit
def preprocess8(flattened,N,B,AlinesPerX,apod):
    pp = np.empty([2048,AlinesPerX])
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


def reshape8(A,N,AlinesPerX,B1,B2):

    reshaped = np.empty([2048,AlinesPerX,2])

    flattened = A.flatten()

    b1 = 0
    b2 = 0
    for n in np.arange(N):
        if B1[n]:
            reshaped[:,b1,0] = flattened[2048*n:2048*n+2048]
            b1 += 1
        elif B2[n]:
            reshaped[:,b2,1] = flattened[2048*n:2048*n+2048]
            b2 += 1

    return reshaped