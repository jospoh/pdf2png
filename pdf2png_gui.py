"""PDF to PNG Converter - Desktop GUI Application."""

import os
import sys
from pathlib import Path

from PySide6.QtCore import (
    QThread,
    QUrl,
    Signal,
    Qt,
)
from PySide6.QtGui import QDesktopServices, QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

import pdf2png


# ---------------------------------------------------------------------------
# Worker Thread
# ---------------------------------------------------------------------------

class ConversionWorker(QThread):
    """Background thread that converts PDFs one by one."""

    progress_updated = Signal(int, int, str)   # (index, total, filename)
    file_completed = Signal(str, list)          # (pdf_path, output_files)
    file_failed = Signal(str, str)              # (pdf_path, error_msg)
    conversion_finished = Signal(int, int)      # (success, fail)

    def __init__(
        self,
        pdf_paths: list[str],
        output_dir: str,
        dpi: int,
        pages: list[int] | None,
    ):
        super().__init__()
        self._pdf_paths = pdf_paths
        self._output_dir = output_dir
        self._dpi = dpi
        self._pages = pages
        self._abort = False

    def abort(self):
        self._abort = True

    def run(self):
        total = len(self._pdf_paths)
        ok = 0
        fail = 0
        for i, pdf_path in enumerate(self._pdf_paths):
            if self._abort:
                break
            name = Path(pdf_path).name
            self.progress_updated.emit(i, total, name)

            # Use per-PDF subdirectory to avoid filename collisions
            stem = Path(pdf_path).stem
            out_dir = os.path.join(self._output_dir, stem) if total > 1 else self._output_dir
            try:
                files = pdf2png.convert_pdf(pdf_path, out_dir, self._dpi, self._pages)
                self.file_completed.emit(pdf_path, files)
                ok += 1
            except Exception as e:
                self.file_failed.emit(pdf_path, str(e))
                fail += 1

        self.conversion_finished.emit(ok, fail)


# ---------------------------------------------------------------------------
# Drop Zone Widget
# ---------------------------------------------------------------------------

class DropZone(QWidget):
    """Area that accepts drag-and-dropped PDF files."""

    files_dropped = Signal(list)

    _STYLE_NORMAL = """
        DropZone {
            border: 2px dashed #aaaaaa;
            border-radius: 8px;
            background-color: #f9f9f9;
        }
    """
    _STYLE_HOVER = """
        DropZone {
            border: 2px dashed #3385ff;
            border-radius: 8px;
            background-color: #e6f0ff;
        }
    """

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setMinimumHeight(110)
        self.setStyleSheet(self._STYLE_NORMAL)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._label = QLabel("Drag PDF files or folders here")
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setStyleSheet("font-size: 14px; color: #666; border: none; background: transparent;")
        layout.addWidget(self._label)

        btn_row = QHBoxLayout()
        btn_row.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._btn_files = QPushButton("Select Files...")
        self._btn_folder = QPushButton("Select Folder...")
        self._btn_files.setStyleSheet("border: 1px solid #ccc; padding: 4px 12px; background: white;")
        self._btn_folder.setStyleSheet("border: 1px solid #ccc; padding: 4px 12px; background: white;")
        btn_row.addWidget(self._btn_files)
        btn_row.addWidget(self._btn_folder)
        layout.addLayout(btn_row)

        self._btn_files.clicked.connect(self._select_files)
        self._btn_folder.clicked.connect(self._select_folder)

    # -- Drag & Drop events --------------------------------------------------

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet(self._STYLE_HOVER)
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self.setStyleSheet(self._STYLE_NORMAL)
        event.accept()

    def dropEvent(self, event: QDropEvent):
        self.setStyleSheet(self._STYLE_NORMAL)
        paths = []
        for url in event.mimeData().urls():
            local = url.toLocalFile()
            if local:
                paths.append(local)
        if paths:
            pdf_files = pdf2png.collect_pdf_files(paths)
            if pdf_files:
                self.files_dropped.emit(pdf_files)
        event.acceptProposedAction()

    # -- File dialog helpers --------------------------------------------------

    def _select_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select PDF Files", "", "PDF Files (*.pdf)"
        )
        if files:
            self.files_dropped.emit(files)

    def _select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            pdf_files = pdf2png.collect_pdf_files([folder])
            if pdf_files:
                self.files_dropped.emit(pdf_files)


# ---------------------------------------------------------------------------
# Main Window
# ---------------------------------------------------------------------------

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PDF to PNG Converter")
        self.setMinimumSize(650, 560)
        self.resize(780, 680)

        self._worker: ConversionWorker | None = None

        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(8)

        # -- Drop zone -------------------------------------------------------
        self._drop_zone = DropZone()
        self._drop_zone.files_dropped.connect(self._add_files)
        root_layout.addWidget(self._drop_zone)

        # -- Splitter: queue + results ----------------------------------------
        splitter = QSplitter(Qt.Orientation.Vertical)

        # File queue panel
        queue_widget = QWidget()
        queue_layout = QVBoxLayout(queue_widget)
        queue_layout.setContentsMargins(0, 0, 0, 0)

        queue_header = QHBoxLayout()
        self._queue_label = QLabel("Files to convert (0)")
        self._queue_label.setStyleSheet("font-weight: bold;")
        queue_header.addWidget(self._queue_label)
        queue_header.addStretch()
        self._btn_clear_queue = QPushButton("Clear")
        self._btn_clear_queue.clicked.connect(self._clear_queue)
        queue_header.addWidget(self._btn_clear_queue)
        queue_layout.addLayout(queue_header)

        self._file_list = QListWidget()
        queue_layout.addWidget(self._file_list)
        splitter.addWidget(queue_widget)

        # Result panel
        result_widget = QWidget()
        result_layout = QVBoxLayout(result_widget)
        result_layout.setContentsMargins(0, 0, 0, 0)

        result_header = QHBoxLayout()
        self._result_label = QLabel("Results")
        self._result_label.setStyleSheet("font-weight: bold;")
        result_header.addWidget(self._result_label)
        result_header.addStretch()
        self._btn_clear_results = QPushButton("Clear")
        self._btn_clear_results.clicked.connect(self._clear_results)
        result_header.addWidget(self._btn_clear_results)
        result_layout.addLayout(result_header)

        self._result_tree = QTreeWidget()
        self._result_tree.setHeaderLabels(["Status", "File", "Directory", ""])
        self._result_tree.setColumnWidth(0, 50)
        self._result_tree.setColumnWidth(1, 250)
        self._result_tree.setColumnWidth(2, 280)
        self._result_tree.setRootIsDecorated(False)
        result_layout.addWidget(self._result_tree)
        splitter.addWidget(result_widget)

        splitter.setSizes([200, 200])
        root_layout.addWidget(splitter, 1)

        # -- Settings bar -----------------------------------------------------
        settings_layout = QHBoxLayout()

        settings_layout.addWidget(QLabel("DPI:"))
        self._dpi_spin = QSpinBox()
        self._dpi_spin.setRange(72, 1200)
        self._dpi_spin.setSingleStep(50)
        self._dpi_spin.setValue(300)
        settings_layout.addWidget(self._dpi_spin)

        settings_layout.addWidget(QLabel("Pages:"))
        self._pages_edit = QLineEdit()
        self._pages_edit.setPlaceholderText("All (e.g. 1,3,5-8)")
        self._pages_edit.setMaximumWidth(150)
        settings_layout.addWidget(self._pages_edit)

        settings_layout.addWidget(QLabel("Output:"))
        self._output_edit = QLineEdit()
        self._output_edit.setText(os.path.abspath("./output"))
        self._output_edit.setReadOnly(True)
        settings_layout.addWidget(self._output_edit, 1)

        self._btn_browse = QPushButton("Browse...")
        self._btn_browse.clicked.connect(self._browse_output)
        settings_layout.addWidget(self._btn_browse)

        root_layout.addLayout(settings_layout)

        # -- Action bar -------------------------------------------------------
        action_layout = QHBoxLayout()

        self._btn_start = QPushButton("Start Conversion")
        self._btn_start.setMinimumHeight(32)
        self._btn_start.setStyleSheet("font-weight: bold; padding: 4px 20px;")
        self._btn_start.clicked.connect(self._start_conversion)
        action_layout.addWidget(self._btn_start)

        self._btn_cancel = QPushButton("Cancel")
        self._btn_cancel.setMinimumHeight(32)
        self._btn_cancel.setEnabled(False)
        self._btn_cancel.clicked.connect(self._cancel_conversion)
        action_layout.addWidget(self._btn_cancel)

        self._progress_bar = QProgressBar()
        self._progress_bar.setVisible(False)
        action_layout.addWidget(self._progress_bar, 1)

        self._status_label = QLabel("Ready")
        action_layout.addWidget(self._status_label)

        root_layout.addLayout(action_layout)

    # -- File queue management ------------------------------------------------

    def _add_files(self, paths: list[str]):
        existing = set()
        for i in range(self._file_list.count()):
            existing.add(self._file_list.item(i).data(Qt.ItemDataRole.UserRole))

        added = 0
        for p in paths:
            if p not in existing:
                item = QListWidgetItem(f"{Path(p).name}    {Path(p).parent}")
                item.setData(Qt.ItemDataRole.UserRole, p)
                item.setToolTip(p)
                self._file_list.addItem(item)
                added += 1

        self._update_queue_label()
        if added == 0 and paths:
            self._status_label.setText("Files already in queue")

    def _clear_queue(self):
        self._file_list.clear()
        self._update_queue_label()

    def _update_queue_label(self):
        count = self._file_list.count()
        self._queue_label.setText(f"Files to convert ({count})")

    def _clear_results(self):
        self._result_tree.clear()
        self._result_label.setText("Results")

    # -- Settings helpers -----------------------------------------------------

    def _browse_output(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if folder:
            self._output_edit.setText(folder)

    def _get_pages(self) -> list[int] | None:
        text = self._pages_edit.text().strip()
        if not text:
            return None
        try:
            return pdf2png.parse_pages(text)
        except (ValueError, TypeError):
            return None

    # -- Conversion control ---------------------------------------------------

    def _start_conversion(self):
        if self._file_list.count() == 0:
            QMessageBox.warning(self, "No Files", "Please add PDF files first.")
            return

        pages_text = self._pages_edit.text().strip()
        if pages_text:
            try:
                pdf2png.parse_pages(pages_text)
            except (ValueError, TypeError):
                QMessageBox.warning(
                    self, "Invalid Pages",
                    f"Cannot parse page specification: '{pages_text}'\n"
                    "Use format like: 1,3,5-8"
                )
                return

        pdf_paths = []
        for i in range(self._file_list.count()):
            pdf_paths.append(self._file_list.item(i).data(Qt.ItemDataRole.UserRole))

        output_dir = self._output_edit.text()
        dpi = self._dpi_spin.value()
        pages = self._get_pages()

        # Lock UI
        self._btn_start.setEnabled(False)
        self._btn_cancel.setEnabled(True)
        self._btn_clear_queue.setEnabled(False)
        self._progress_bar.setVisible(True)
        self._progress_bar.setRange(0, len(pdf_paths))
        self._progress_bar.setValue(0)

        self._worker = ConversionWorker(pdf_paths, output_dir, dpi, pages)
        self._worker.progress_updated.connect(self._on_progress)
        self._worker.file_completed.connect(self._on_file_completed)
        self._worker.file_failed.connect(self._on_file_failed)
        self._worker.conversion_finished.connect(self._on_finished)
        self._worker.finished.connect(self._worker.deleteLater)
        self._worker.start()

    def _cancel_conversion(self):
        if self._worker:
            self._worker.abort()
            self._status_label.setText("Cancelling...")
            self._btn_cancel.setEnabled(False)

    # -- Worker signal handlers -----------------------------------------------

    def _on_progress(self, index: int, total: int, name: str):
        self._progress_bar.setValue(index)
        self._status_label.setText(f"{index + 1}/{total}  {name}")

    def _on_file_completed(self, pdf_path: str, output_files: list[str]):
        for f in output_files:
            fp = Path(f)
            item = QTreeWidgetItem(["OK", fp.name, str(fp.parent)])
            item.setData(2, Qt.ItemDataRole.UserRole, str(fp.parent))
            self._result_tree.addTopLevelItem(item)

            btn = QPushButton("Open")
            btn.setMaximumWidth(60)
            directory = str(fp.parent)
            btn.clicked.connect(lambda checked=False, d=directory: self._open_directory(d))
            self._result_tree.setItemWidget(item, 3, btn)

    def _on_file_failed(self, pdf_path: str, error: str):
        name = Path(pdf_path).name
        item = QTreeWidgetItem(["ERR", name, error])
        item.setForeground(0, Qt.GlobalColor.red)
        item.setForeground(2, Qt.GlobalColor.red)
        self._result_tree.addTopLevelItem(item)

    def _on_finished(self, success: int, fail: int):
        self._btn_start.setEnabled(True)
        self._btn_cancel.setEnabled(False)
        self._btn_clear_queue.setEnabled(True)
        self._progress_bar.setValue(self._progress_bar.maximum())

        total = success + fail
        if fail == 0:
            self._status_label.setText(f"Done - {success} file(s) converted")
        else:
            self._status_label.setText(f"Done - {success} OK, {fail} failed")

        self._result_label.setText(f"Results ({self._result_tree.topLevelItemCount()})")

    # -- Utilities ------------------------------------------------------------

    @staticmethod
    def _open_directory(directory: str):
        QDesktopServices.openUrl(QUrl.fromLocalFile(directory))


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
