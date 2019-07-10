# -*- coding: utf-8 -*-

import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from queue import Queue
import threading

from src.main.python.PySpectralRadar import *

#-------------------------------------------------------------------------------

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

#-------------------------------------------------------------------------------

print('\n----------------------------------')
print('PySpectralRadar Figure-8 Scanner')
print('----------------------------------\n')

###input('\nPress ENTER to initiate device handle...')

dev = initDevice()

###input('\nPress ENTER to set device parameters...')

triggerType = Device_TriggerType
setTriggerMode(dev,triggerType.Trigger_FreeRunning)
setTriggerTimeoutSec(dev,5)

print('\n----------------------------------')
print('Set trigger mode to free running, timeout = 5 s')
print('----------------------------------\n')

###input('\nPress ENTER to initiate probe handle...')

probe = initProbe(dev,'ProbeLKM10-LV')

###input('\nPress ENTER to initiate processing handle...')

proc = createProcessingForDevice(dev)

setCameraPreset(dev,probe,proc,0)
print('\n----------------------------------')
print('Set camera preset = 0')
print('----------------------------------\n')

###input('\nPress ENTER to initiate acquisition...')

FALSE = BOOL(0)
TRUE = BOOL(1)



size = 0.003182
N = 10
fb=10
repeats = 1
intpDk = -0.19
apod = np.hanning(2048)
k = np.linspace(1-intpDk/2, 1+intpDk/2, 2048)
lam = 1/k[::-1]
interpIndices = np.linspace( min(lam), max(lam), 2048)

fig8pos, X, Y, b1, b2, Na, D = generateIdealFigureEightPositions(size,N,rpt=repeats,flyback=fb)

plt.plot(X,Y)
plt.show()

xsection1 = np.arange(Na)[b1]
xsection = np.arange(Na)[b2]

scanPattern = createFreeformScanPattern(probe,fig8pos,len(X)*repeats,1,FALSE)
angle = 45

rotateScanPattern(scanPattern,angle)

print('\n----------------------------------')
print('Created scan pattern: 10X figure-8.')
print(D)
print('----------------------------------\n')

acq = AcquisitionType

print('\n----------------------------------')
print('Tried to start measurement. Created data objects.')
print('----------------------------------\n')

rawDataHandle = createRawData()
complexDataHandle = createComplexData()

rpt = 10000

def AcqThread():

    i = rpt
    startMeasurement(dev,scanPattern,acq.Acquisition_AsyncContinuous)

    while i > 0:
        setComplexDataOutput(proc,complexDataHandle)
        getRawData(dev,rawDataHandle)
        # executeProcessing(proc,rawDataHandle)

        if i == rpt:
            prop = RawDataPropertyInt
            rawSize1 = getRawDataPropertyInt(rawDataHandle,prop.RawData_Size1)
            rawSize2 = getRawDataPropertyInt(rawDataHandle,prop.RawData_Size2)
            rawSize3 = getRawDataPropertyInt(rawDataHandle,prop.RawData_Size3)
            rawNumberOfElements = getRawDataPropertyInt(rawDataHandle,prop.RawData_NumberOfElements)

            rawDim = [rawSize1,rawSize2,rawSize3]

            prop2 = DataPropertyInt
            complexSize1 = getComplexDataPropertyInt(complexDataHandle,prop2.Data_Size1)
            complexSize2 = getComplexDataPropertyInt(complexDataHandle,prop2.Data_Size2)
            complexSize3 = getComplexDataPropertyInt(complexDataHandle,prop2.Data_Size3)
            complexNumberOfElements = getComplexDataPropertyInt(complexDataHandle,prop2.Data_NumberOfElements)
            complexBytes = getComplexDataPropertyInt(complexDataHandle,prop2.Data_BytesPerElement)

            complexDim = [complexSize1,complexSize2,complexSize3]

        holder = np.empty(rawDim,dtype=np.uint16)
        copyRawDataContent(rawDataHandle,holder)

        cholder = np.empty(complexDim,dtype=np.complex64)
        copyComplexDataContent(complexDataHandle,cholder)

        if (i % 9) == 0:
            PREVIEW.put(holder)

        i -= 1

    stopMeasurement(dev)


PREVIEW = Queue()

fig = plt.figure()

window = np.hanning(2048)

# @numba.jit
def process(raw):

    proc = np.empty([1024,N],dtype=np.complex64)
    fig8 = np.empty([2048,N],dtype=np.uint16)
    flat = raw.flatten()

    i = 0
    for n in xsection1:
        fig8[:,i] = flat[2048*n:2048*n+2048]
        i += 1

    dc = np.mean(fig8,axis=1)

    for n in range(N):
        corr = (fig8[:,n] - dc) * apod
        proc[:,n] = np.fft.ifft(corr)[1024:2048].astype(np.complex64)

    return proc[-400::]

def animate(i):

    disp = np.zeros([1024,N],dtype=np.float32)
    plt.cla()

    latest = PREVIEW.get()

    if latest.size > 0:

        bscan = process(latest)

        disp = 20*np.log10(abs(bscan))

    b = plt.imshow(disp,aspect=1,cmap='gray',origin='lower',vmin=-100,vmax=-2)

    return b

Acquisition = threading.Thread(target=AcqThread)
Acquisition.start()

ani = FuncAnimation(fig, animate, interval=1)
plt.show()

clearScanPattern(scanPattern)
clearRawData(rawDataHandle)
closeProcessing(proc)
closeProbe(probe)
closeDevice(dev)

print('\n----------------------------------')
print('Cleared objects from memory.')
print('----------------------------------')
