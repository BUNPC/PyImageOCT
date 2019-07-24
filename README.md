# PyImageOCT V 0.1.0
Control applications for Thorlabs Telesto SD-OCT system
Developed for BOAS Lab at Boston University

Currently, only Figure-8 scanning application which acquires two perpendicular B-scans is working.

The project is dependent on fbs but will run without it

Dependencies:
Python > 3.5 (fbs build is finnicky for > 3.6)
NumPy
Numba
scipy.interpolate
fbs/PyInstaller
PyQt5
PyQtGraph
Qt 5.13.0
PySpectralRadar
h5py
