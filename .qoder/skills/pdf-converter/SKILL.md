# PDF Converter Skill

## Description
Convert PDF files to high-quality PNG images with batch processing support.

## When to Use
Use this skill when the user wants to:
- Convert PDF files to PNG images
- Batch convert multiple PDFs to images
- Extract specific pages from PDFs as images
- Adjust image resolution/DPI for PDF conversions

## Instructions

### Prerequisites
Ensure dependencies are installed:
```bash
pip install PyMuPDF Pillow
```

### Usage

The main tool is `pdf2png.py` located at the project root.

#### Basic conversion
```bash
python pdf2png.py input.pdf
```

#### Specify output directory and DPI
```bash
python pdf2png.py input.pdf -o output_dir --dpi 600
```

#### Convert specific pages (1-indexed)
```bash
python pdf2png.py input.pdf --pages 1,3,5-8
```

#### Batch convert from directory
```bash
python pdf2png.py pdf_folder/ -o images -w 8
```

#### Batch convert multiple files
```bash
python pdf2png.py a.pdf b.pdf c.pdf -o result
```

### Parameters
| Parameter | Short | Default | Description |
|-----------|-------|---------|-------------|
| `--output` | `-o` | `./output` | Output directory for PNG files |
| `--dpi` | `-d` | `300` | Output resolution in DPI |
| `--pages` | `-p` | all | Pages to convert, e.g. `1,3,5-8` |
| `--workers` | `-w` | `4` | Concurrent workers for batch processing |

### Programmatic Usage
```python
from pdf2png import convert_pdf, batch_convert

# Single file
output_files = convert_pdf("input.pdf", "output_dir", dpi=300)

# Batch
results = batch_convert(["a.pdf", "b.pdf"], "output_dir", dpi=300, workers=4)
```

## Desktop GUI Application

A graphical interface is available via `pdf2png_gui.py` (PySide6).

### Launch GUI (development)
```bash
pip install PySide6
python pdf2png_gui.py
```

### Build standalone executable
```bash
pip install pyinstaller
python build.py
```
Output will be in `dist/PDF2PNG/` directory. The `PDF2PNG.exe` (Windows) or `PDF2PNG.app` (macOS) can run without Python installed.

### GUI Features
- Drag and drop PDF files or folders onto the window
- Configure DPI, page selection, and output directory
- Progress bar with per-file status updates
- Result list with "Open Directory" buttons
- Batch processing with automatic subdirectory creation

## Key Implementation Details
- Uses PyMuPDF (fitz) for high-quality PDF rendering
- Supports arbitrary DPI settings for resolution control
- Handles different page sizes automatically via PDF's internal coordinate system
- Thread-based parallelism for batch conversion
- Zero-dependency image output (PyMuPDF generates PNG directly)
- PySide6 GUI with QThread for non-blocking conversion
- PyInstaller onedir packaging for standalone distribution
