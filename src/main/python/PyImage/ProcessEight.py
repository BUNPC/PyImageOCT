from multiprocessing import Queue

class ProcessEight:

    def __init__(self,controller):

        pass

    def initialize(self):

        self._raw_frames = Queue(maxsize=self._maxframes)
        self._proc_frames = Queue(maxsize=self._maxframes)
        self._displacements = Queue(maxsize=self._maxdisplacements)

    @numba.njit()  # Fastmath here creates issues w/ DivideByZero
    def weighted_peak_jitted(A, dim):
        """
        Returns weighted mean from array of values, weights passed with the dim
        """
        num = 0
        denom = 0
        for i in range(dim[0]):
            num += A[i, 0] * A[i, 1]
            denom += A[i, 1]
        if denom == 0:
            return 0
        else:
            return num / denom

    @numba.njit(fastmath=True)
    def complexcorr_jitted(A, B, L):
        """
        Complex correlation coefficient of 1D vectors A and B of length L
        """
        num = 0
        d1 = 0
        d2 = 0
        for x in range(L):
            num += A[x] * np.conj(B[x])
            d1 += np.abs(A[x]) ** 2
            d2 += np.abs(B[x]) ** 2

        return num / (np.sqrt(d1) * np.sqrt(d2))

    # @numba.njit(fastmath=True,parallel=True)
    def getdisplacement_jitted(t0, t1, dim, shifts, nshifts, corr, peak, peak_dim, thresh=0.4, peakwidth=2):

        displacement = 0

        for i in numba.prange(nshifts):
            corr[i] = shiftcorr_jitted(t0, t1, dim, shifts[i])

        maxi = np.argmax(corr)
        maxima.append(maxi)
        corrplots.append(corr)

        if maxi >= peakwidth and maxi < nshifts - peakwidth and corr[
            maxi] > thresh:  # Excludes first two and last two time points from maxima, only peaks > 0.4 are considered

            for i, offset in enumerate(
                    np.arange(-peakwidth, peakwidth + 1)):  # Interpolate peak from surrounding values, +- peakWidth

                peak[i, 0] = shifts[maxi + offset]
                peak[i, 1] = corr[maxi + offset]  # Weight mean by correlation

                displacement = weighted_peak_jitted(peak, peak_dim)

        return displacement

    @numba.njit(fastmath=True)
    def shiftcorr_jitted(A, B, dim, shift):
        """
        Returns average abs real  block-matching correlation along 2nd axis of A
        and B at given lateral pixel shift. Returns result.
        A, B: 2D complex arrays
        dim: lateral dimension of A, B
        shifts: shift to compute
        """

        out = 0

        # TODO figure out if you can do this without creating new vectors
        if shift < 0:  # Determine indexes of neighbors for a given lateral pixel shift

            index = np.arange(np.abs(shift), dim)

        else:

            index = np.arange(0, dim - shift)

        norm = 0
        for x in index:
            out += np.abs(np.real(complexcorr_jitted(A[:, x], B[:, x + shift], len(ROI))))
            norm += 1

        return out / norm