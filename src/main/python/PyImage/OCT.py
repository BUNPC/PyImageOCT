import numpy as np


def generateIdealFigureEightPositions(xsize, alinesPerX, rpt=1, alinesPerFlyback=20):
    '''
    Generates figure-8 scan pattern positions with orthogonal cross.
    :param xdistance: Distance between adjacent scans in perpendicular B-scans
    :param alinesPerX: Number of A-lines in each orthogonal B-scan
    :param rpt: Number of times to repeat the pattern in the 1D positions array
    :return: posRpt: 1D positions array for use with FreeformScanPattern; [x1,y1,x2,y2...]
             X: X coordinates of a single figure-8
             Y: Y coordinates of a single figure-8
             B1: Indices of first B-scan
             B2: Indices of second B-scan
             N: Total number of A-scans in the pattern
    '''
    if rpt > 0:
        t = np.linspace(0, 2 * np.pi, alinesPerFlyback, dtype=np.float32)

        cross = np.linspace(-xsize, xsize, alinesPerX)

        fb1 = np.linspace(-np.pi / 3.2, np.pi / 3.2, alinesPerFlyback, dtype=np.float32)
        fb2 = np.linspace(-np.pi / 3.2 + np.pi, np.pi / 3.2 + np.pi, alinesPerFlyback, dtype=np.float32)

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
            [np.zeros(alinesPerFlyback), np.ones(alinesPerX), np.zeros(alinesPerFlyback), np.zeros(alinesPerX)]).astype(
            np.bool)
        b2 = np.concatenate(
            [np.zeros(alinesPerFlyback), np.zeros(alinesPerX), np.zeros(alinesPerFlyback), np.ones(alinesPerX)]).astype(
            np.bool)

        pos = np.empty(int(2 * len(X)), dtype=np.float32)

        pos[0::2] = X
        pos[1::2] = Y

        posRpt = np.tile(pos, rpt)

        N = len(X)

        return [posRpt, X, Y, b1, b2, N, D]
