import numpy as np


def generateIdealFigureEightPositions(xsize, alinesPerX, rpt=1, flyback=20):
    '''
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
    '''
    if rpt > 0:
        t = np.linspace(0, 2 * np.pi, flyback, dtype=np.float32)

        cross = np.linspace(-xsize, xsize, alinesPerX)

        fb1 = np.linspace(-np.pi / 3.4, np.pi / 3.4, flyback, dtype=np.float32)
        fb2 = np.linspace(-np.pi / 3.4 + np.pi, np.pi / 3.4 + np.pi, flyback, dtype=np.float32)

        B1 = np.array([cross[::-1], cross[::-1]])
        B2 = np.array([cross, -cross])

        D = np.sqrt((B1[0][0] - B1[0][1]) ** 2 + (B1[1][0] - B1[1][1]) ** 2)

        x1 = 2 * xsize * np.cos(fb1)
        y1 = ((2 * xsize) / 1.7) * np.sin(2 * fb1)
        x2 = 2 * xsize * np.cos(fb2)
        y2 = ((2 * xsize) / 1.7) * np.sin(2 * fb2)

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

def fig8ToBScan(A,N,B,AlinesPerX,apod,ROI=400):
    """
    Converts a raw array of unsigned 16 bit integer fig-8 data from Telesto to ROI of spatial domain pixels for
    live display ONLY (no lambda-k interpolation)
    :param A: Raw figure-8 data
    :param N: The total number of A-lines in the figure-8 pattern
    :param B: Boolean-type array representing indices in N-length A which make up a B-scan
    :param AlinesPerX: Number of A-lines in each B-scan
    :param apod: Apodization window. Must be 2048 in length
    :param ROI: number of pixels from the top of the B-scan to return
    :return: A 2D array of dB scale quasi-spatial data
    """
    flat = A.flatten()
    proc = np.empty([1024,AlinesPerX],dtype=np.complex64)
    fig8 = np.empty([2048,AlinesPerX],dtype=np.uint16)

    i = 0
    for n in np.arange(N):
        if B[n]:
            fig8[:,i] = flat[2048*n:2048*n+2048]
            i += 1

    dc = np.mean(fig8,axis=1)

    for n in np.arange(AlinesPerX):
        c = (fig8[:,n] - dc) * apod
        proc[:,n] = np.fft.ifft(c)[0:1024].astype(np.complex64)

    return 20*np.log10(np.abs(proc[0:ROI]))




