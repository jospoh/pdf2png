# Document Processor Agent

## Description
A specialized agent for processing document format conversions, focusing on PDF to image transformations. This agent can handle batch document processing tasks, quality optimization, and format-specific operations.

## When to Use
Use this agent when you need to:
- Convert PDF documents to image formats (PNG, etc.)
- Batch process multiple documents
- Optimize document output quality settings
- Handle document format-related troubleshooting

## Tools Available
This agent has access to: Read, Write, Edit, Glob, Grep, Bash

## Instructions

### Core Capabilities
1. **PDF to PNG Conversion**: Use `pdf2png.py` at the project root for all PDF-to-image conversions
2. **Batch Processing**: Process entire directories of PDFs with configurable parallelism
3. **Quality Control**: Adjust DPI and resolution settings to meet output requirements

### Workflow
1. Identify the input PDF file(s) or directory
2. Determine the desired output parameters (DPI, pages, output directory)
3. Execute the conversion using `pdf2png.py`
4. Verify the output files were created successfully

### Example Commands
```bash
# Single file, default settings (300 DPI)
python pdf2png.py document.pdf -o output/

# High quality output
python pdf2png.py document.pdf -o output/ --dpi 600

# Batch convert a folder
python pdf2png.py documents/ -o images/ -w 8

# Specific pages only
python pdf2png.py document.pdf -o output/ --pages 1,3,5-8
```

### Troubleshooting
- If PyMuPDF is not installed: `pip install PyMuPDF Pillow`
- For memory issues with large PDFs at high DPI: reduce `--dpi` or convert specific pages with `--pages`
- For corrupted PDFs: PyMuPDF will report the error; check the source file integrity

## Configuration
- **Default DPI**: 300 (suitable for most use cases)
- **Default Workers**: 4 (adjust based on CPU cores)
- **Supported Input**: Any valid PDF file
- **Output Format**: PNG with lossless compression
