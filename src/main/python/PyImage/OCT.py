import numpy as np
import numba

def generateIdealFigureEightPositions(xsize, alinesPerX, rpt=1):
    '''
    Generates figure-8 scan pattern positions with orthogonal cross.
    :param alinesPerX: Number of A-lines in each orthogonal B-scan
    :param rpt: Number of times to repeat the pattern in the 1D positions array
    :return: posRpt: 1D positions array for use with FreeformScanPattern; [x1,y1,x2,y2...]
             X: X coordinates of a single figure-8
             Y: Y coordinates of a single figure-8
             B1: Indices of first B-scan
             B2: Indices of second B-scan
             N: Total number of A-scans in the pattern
             D: Distance between adjacent A-scans in the pattern
    '''
    if rpt > 0:
        t = np.linspace(0, 2 * np.pi, 100, dtype=np.float32)
        cross = np.linspace(-xsize, xsize, alinesPerX)
        B1 = np.array([cross[::-1], cross[::-1]])
        B2 = np.array([cross, -cross])
        D = np.sqrt((B1[0][0] - B1[0][1]) ** 2 + (B1[1][0] - B1[1][1]) ** 2)
        x = 2 * xsize * np.cos(t)
        y = ((2 * xsize) / 1.7) * np.sin(2 * t)
        x1 = x[x > xsize + 0.001 * xsize]
        x2 = x[x < -xsize - 0.001 * xsize]
        y1 = y[x > xsize + 0.001 * xsize]
        y2 = y[x < -xsize - 0.001 * xsize]

        X = np.concatenate([x1[0:16], B1[0], x2, B2[0], x1[17::]])
        Y = np.concatenate([y1[0:16], B1[1], y2, B2[1], y1[17::]])
        b1 = np.concatenate([np.zeros(np.size(x1[0:16])), np.ones(alinesPerX), np.zeros(alinesPerX),np.zeros(np.size(x1[17::]))])
        b2 = np.concatenate([np.zeros(np.size(x1[0:16])), np.zeros(alinesPerX), np.ones(alinesPerX),np.zeros(np.size(x1[17::]))])

        pos = np.empty(int(2 * len(X)), dtype=np.float32)
        pos[0::2] = X
        pos[1::2] = Y
        posRpt = np.tile(pos, rpt)

        N = len(X)

        print('Figure-8 scan pattern generated...')
        print(str(len(B1[0])) + ' points in each orthogonal cross...')
        print(str(len(X)) + ' total points.')

        return [posRpt, X, Y, b1, b2, N, D]
