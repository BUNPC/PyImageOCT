# PyImageOCT V 0.1.5
Control applications for Thorlabs Telesto SD-OCT system

Currently, only Figure-8 scanning application which acquires two perpendicular B-scans is working.

The project is built around fbs but might run without it

## Dependencies:
- Python > 3.5 (fbs build is finnicky for > 3.6)
- NumPy
- Numba
- scipy.interpolate
- [fbs & PyInstaller](https://build-system.fman.io/manual/)
- PyQt5
- PyQtGraph 
- Qt 5.13.0
- [PySpectralRadar](https://github.com/sstucker/PySpectralRadar)
- h5py
