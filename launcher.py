"""Launcher entry point for PyInstaller builds.

Uses dynamic import to prevent PyInstaller's bytecode scanner from
choking on fitz's .pyc files on Python 3.10.0.
"""
import importlib
import sys


def main():
    # Ensure pdf2png and fitz are importable at runtime
    importlib.import_module('fitz')
    importlib.import_module('pdf2png')
    gui = importlib.import_module('pdf2png_gui')
    gui.main()


if __name__ == '__main__':
    main()
