"""PDF to PNG converter - High quality batch conversion tool."""

import argparse
import os
import sys
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import fitz  # PyMuPDF


DEFAULT_DPI = 300
DEFAULT_QUALITY = 95
DEFAULT_WORKERS = 4


def convert_page(page: fitz.Page, dpi: int) -> bytes:
    """Convert a single PDF page to PNG bytes."""
    zoom = dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)
    pixmap = page.get_pixmap(matrix=matrix, alpha=False)
    return pixmap.tobytes(output="png")


def convert_pdf(
    pdf_path: str,
    output_dir: str,
    dpi: int = DEFAULT_DPI,
    pages: list[int] | None = None,
) -> list[str]:
    """Convert a PDF file to PNG images.

    Args:
        pdf_path: Path to the PDF file.
        output_dir: Directory to save PNG files.
        dpi: Resolution in dots per inch.
        pages: List of page numbers (0-indexed) to convert. None means all pages.

    Returns:
        List of output file paths.
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(str(pdf_path))
    total_pages = doc.page_count

    if pages is None:
        page_indices = list(range(total_pages))
    else:
        page_indices = [p for p in pages if 0 <= p < total_pages]
        if not page_indices:
            doc.close()
            raise ValueError(
                f"No valid pages specified. PDF has {total_pages} pages (0-{total_pages - 1})."
            )

    stem = pdf_path.stem
    output_files = []

    for idx in page_indices:
        page = doc.load_page(idx)
        png_data = convert_page(page, dpi)

        if total_pages == 1 and pages is None:
            out_name = f"{stem}.png"
        else:
            out_name = f"{stem}_page{idx + 1:04d}.png"

        out_path = output_dir / out_name
        out_path.write_bytes(png_data)
        output_files.append(str(out_path))

    doc.close()
    return output_files


def batch_convert(
    pdf_paths: list[str],
    output_dir: str,
    dpi: int = DEFAULT_DPI,
    pages: list[int] | None = None,
    workers: int = DEFAULT_WORKERS,
) -> dict[str, list[str] | str]:
    """Batch convert multiple PDF files to PNG.

    Args:
        pdf_paths: List of PDF file paths.
        output_dir: Directory to save PNG files.
        dpi: Resolution in dots per inch.
        pages: List of page numbers to convert per PDF.
        workers: Number of concurrent workers.

    Returns:
        Dict mapping PDF path to list of output files or error message.
    """
    results: dict[str, list[str] | str] = {}

    def _convert(path: str) -> tuple[str, list[str] | str]:
        try:
            files = convert_pdf(path, output_dir, dpi, pages)
            return path, files
        except Exception as e:
            return path, f"Error: {e}"

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(_convert, p): p for p in pdf_paths}
        for future in as_completed(futures):
            path, result = future.result()
            results[path] = result

    return results


def collect_pdf_files(inputs: list[str]) -> list[str]:
    """Collect PDF file paths from a mix of files and directories."""
    pdf_files = []
    for item in inputs:
        p = Path(item)
        if p.is_file() and p.suffix.lower() == ".pdf":
            pdf_files.append(str(p.resolve()))
        elif p.is_dir():
            for f in sorted(p.rglob("*.pdf")):
                pdf_files.append(str(f.resolve()))
        else:
            print(f"Warning: skipping '{item}' (not a PDF file or directory)")
    return pdf_files


def parse_pages(pages_str: str | None) -> list[int] | None:
    """Parse page specification string like '1,3,5-8' into 0-indexed list."""
    if not pages_str:
        return None

    pages = set()
    for part in pages_str.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-", 1)
            start, end = int(start.strip()), int(end.strip())
            pages.update(range(start - 1, end))  # Convert to 0-indexed
        else:
            pages.add(int(part) - 1)  # Convert to 0-indexed

    return sorted(pages)


def main():
    parser = argparse.ArgumentParser(
        description="PDF to PNG Converter - High quality batch conversion tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  %(prog)s input.pdf
  %(prog)s input.pdf -o output_dir --dpi 600
  %(prog)s *.pdf -o images --dpi 300 --pages 1,3,5-8
  %(prog)s pdf_folder/ -o images -w 8
  %(prog)s a.pdf b.pdf c.pdf -o result
""",
    )

    parser.add_argument(
        "input",
        nargs="+",
        help="PDF files or directories containing PDF files",
    )
    parser.add_argument(
        "-o", "--output",
        default="./output",
        help="Output directory for PNG files (default: ./output)",
    )
    parser.add_argument(
        "-d", "--dpi",
        type=int,
        default=DEFAULT_DPI,
        help=f"Output resolution in DPI (default: {DEFAULT_DPI})",
    )
    parser.add_argument(
        "-p", "--pages",
        type=str,
        default=None,
        help="Pages to convert, e.g. '1,3,5-8' (default: all pages)",
    )
    parser.add_argument(
        "-w", "--workers",
        type=int,
        default=DEFAULT_WORKERS,
        help=f"Number of concurrent workers for batch processing (default: {DEFAULT_WORKERS})",
    )

    args = parser.parse_args()

    # Collect PDF files
    pdf_files = collect_pdf_files(args.input)
    if not pdf_files:
        print("Error: No PDF files found in the specified inputs.")
        sys.exit(1)

    # Parse pages
    page_list = parse_pages(args.pages)

    print(f"Found {len(pdf_files)} PDF file(s)")
    print(f"Output directory: {os.path.abspath(args.output)}")
    print(f"DPI: {args.dpi}")
    if page_list is not None:
        print(f"Pages: {[p + 1 for p in page_list]}")
    print(f"Workers: {args.workers}")
    print("-" * 50)

    start_time = time.time()

    if len(pdf_files) == 1:
        # Single file mode
        pdf = pdf_files[0]
        print(f"Converting: {pdf}")
        try:
            outputs = convert_pdf(pdf, args.output, args.dpi, page_list)
            for f in outputs:
                print(f"  -> {f}")
            print(f"Done. {len(outputs)} image(s) generated.")
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)
    else:
        # Batch mode
        results = batch_convert(
            pdf_files, args.output, args.dpi, page_list, args.workers
        )
        total_images = 0
        errors = 0
        for pdf, result in results.items():
            if isinstance(result, str):
                print(f"FAILED: {pdf}")
                print(f"  {result}")
                errors += 1
            else:
                print(f"OK: {pdf} -> {len(result)} image(s)")
                total_images += len(result)

        print("-" * 50)
        print(f"Total: {total_images} image(s) from {len(pdf_files) - errors} file(s)")
        if errors:
            print(f"Errors: {errors} file(s) failed")

    elapsed = time.time() - start_time
    print(f"Time: {elapsed:.2f}s")


if __name__ == "__main__":
    main()
