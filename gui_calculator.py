"""
3D Slicer Screenshot Calculator GUI

Tkinter desktop app that can:
- load multiple slicer screenshots
- OCR each screenshot through SlicerDataExtractor
- sum print time across jobs
- sum filament usage across jobs
- export a JSON payload for another node/code stage

The GUI uses lazy imports for OCR dependencies so it can still launch and
show dependency guidance if pytesseract/Pillow are missing.
"""

from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

from PIL import Image, ImageGrab

from slicer_data_extractor import ExtractionDebugInfo


@dataclass
class JobRecord:
    file_path: str
    print_time_hours: int
    print_time_minutes: int
    print_time_seconds: int
    total_seconds: int
    filament_grams: float
    filament_kilograms: float
    filament_unit: str
    confidence: float
    time_ambiguous: bool = False
    raw_text: str = ""
    source_image: Optional[Image.Image] = field(default=None, repr=False, compare=False)
    debug_info: Optional[ExtractionDebugInfo] = field(default=None, repr=False, compare=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "print_time_hours": self.print_time_hours,
            "print_time_minutes": self.print_time_minutes,
            "print_time_seconds": self.print_time_seconds,
            "total_seconds": self.total_seconds,
            "filament_grams": self.filament_grams,
            "filament_kilograms": self.filament_kilograms,
            "filament_unit": self.filament_unit,
            "confidence": self.confidence,
            "time_ambiguous": self.time_ambiguous,
            "raw_text": self.raw_text,
        }


class PrintJobCalculator:
    def __init__(self) -> None:
        self.records: List[JobRecord] = []

    @staticmethod
    def format_time(total_seconds: int) -> str:
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        return f"{hours}h {minutes}m {seconds}s"

    @staticmethod
    def format_filament(grams: float) -> str:
        kilograms = grams / 1000.0
        if kilograms >= 1:
            return f"{kilograms:.3f} kg"
        return f"{grams:.2f} g"

    def add_record(self, record: JobRecord) -> None:
        self.records.append(record)

    def add_manual_record(
        self,
        *,
        hours: int,
        minutes: int,
        seconds: int,
        filament_value: float,
        filament_unit: str,
        confidence: float = 1.0,
        file_path: str = "Manual Entry",
        raw_text: str = "",
    ) -> JobRecord:
        total_seconds = int(hours) * 3600 + int(minutes) * 60 + int(seconds)
        filament_unit = filament_unit.lower().strip()
        if filament_unit == "kg":
            filament_grams = float(filament_value) * 1000.0
            filament_kilograms = float(filament_value)
        else:
            filament_grams = float(filament_value)
            filament_kilograms = filament_grams / 1000.0

        record = JobRecord(
            file_path=file_path,
            print_time_hours=int(hours),
            print_time_minutes=int(minutes),
            print_time_seconds=int(seconds),
            total_seconds=total_seconds,
            filament_grams=filament_grams,
            filament_kilograms=filament_kilograms,
            filament_unit=filament_unit,
            confidence=float(confidence),
            raw_text=raw_text,
        )
        self.add_record(record)
        return record

    def totals(self) -> Dict[str, Any]:
        total_seconds = sum(record.total_seconds for record in self.records)
        total_grams = sum(record.filament_grams for record in self.records)
        return {
            "job_count": len(self.records),
            "total_seconds": total_seconds,
            "total_time": self.format_time(total_seconds),
            "total_filament_grams": total_grams,
            "total_filament_kilograms": total_grams / 1000.0,
            "total_filament_formatted": self.format_filament(total_grams),
        }

    def to_export_payload(self) -> Dict[str, Any]:
        return {
            "jobs": [record.to_dict() for record in self.records],
            "totals": self.totals(),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_export_payload(), indent=2)

    def clear(self) -> None:
        self.records.clear()


class SlicerCalculatorApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("3D Slicer Calculator")
        self.geometry("1150x760")
        self.minsize(1000, 700)

        self.calculator = PrintJobCalculator()
        self.extractor = None
        self.tesseract_path_var = tk.StringVar(value=r"C:\Program Files\Tesseract-OCR\tesseract.exe")
        self.naming_mode_var = tk.StringVar(value="manual")
        self.status_var = tk.StringVar(value="Ready")
        self.progress_var = tk.StringVar(value="")
        self.total_time_var = tk.StringVar(value="0h 0m 0s")
        self.total_filament_var = tk.StringVar(value="0.00 g")
        self.job_count_var = tk.StringVar(value="0")
        self.confidence_var = tk.StringVar(value="-")
        self.output_json: Optional[str] = None
        self._row_counter = 0
        self._next_manual_name_index = 1
        self.naming_mode_button: Optional[ttk.Button] = None
        self.debug_enabled = os.environ.get("SLICER_DEBUG", "0") == "1"
        self.debug_window = None

        self._build_ui()
        self._refresh_after_change()
        self._bind_shortcuts()

    def _build_ui(self) -> None:
        self.configure(bg="#131720")
        self._configure_styles()

        container = ttk.Frame(self, style="Root.TFrame", padding=14)
        container.pack(fill="both", expand=True)

        header = ttk.Frame(container, style="Panel.TFrame", padding=16)
        header.pack(fill="x")

        title = ttk.Label(header, text="3D Slicer Screenshot Calculator", style="Title.TLabel")
        title.pack(anchor="w")
        subtitle = ttk.Label(
            header,
            text="Load screenshots from IdeaMaker or BambuStudio, extract time and filament, and sum the total.",
            style="Subtitle.TLabel",
        )
        subtitle.pack(anchor="w", pady=(4, 0))

        main = ttk.Frame(container, style="Root.TFrame")
        main.pack(fill="both", expand=True, pady=(14, 0))
        main.columnconfigure(0, weight=1)
        main.columnconfigure(1, weight=2)
        main.rowconfigure(0, weight=1)

        left = ttk.Frame(main, style="Panel.TFrame", padding=14)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        right = ttk.Frame(main, style="Panel.TFrame", padding=14)
        right.grid(row=0, column=1, sticky="nsew")

        self._build_input_panel(left)
        self._build_results_panel(right)

        footer = ttk.Frame(container, style="Panel.TFrame", padding=12)
        footer.pack(fill="x", pady=(14, 0))
        ttk.Label(footer, textvariable=self.status_var, style="Status.TLabel").pack(anchor="w")

        self.progress_container = ttk.Frame(container, style="Panel.TFrame", padding=(12, 8))
        self.progress_container.pack(fill="x", pady=(10, 0))
        self.progress_container.pack_forget()
        ttk.Label(self.progress_container, textvariable=self.progress_var, style="Field.TLabel").pack(anchor="w")
        self.progress_bar = ttk.Progressbar(self.progress_container, mode="indeterminate")
        self.progress_bar.pack(fill="x", pady=(6, 0))

    def _configure_styles(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("Root.TFrame", background="#131720")
        style.configure("Panel.TFrame", background="#1b2130", relief="flat")
        style.configure("Title.TLabel", background="#1b2130", foreground="#f4f7fb", font=("Segoe UI", 20, "bold"))
        style.configure("Subtitle.TLabel", background="#1b2130", foreground="#9fb0c8", font=("Segoe UI", 10))
        style.configure("Section.TLabel", background="#1b2130", foreground="#e5ebf3", font=("Segoe UI", 11, "bold"))
        style.configure("Field.TLabel", background="#1b2130", foreground="#cdd8e6", font=("Segoe UI", 10))
        style.configure("Value.TLabel", background="#1b2130", foreground="#ffffff", font=("Segoe UI", 12, "bold"))
        style.configure("Status.TLabel", background="#1b2130", foreground="#9fb0c8", font=("Segoe UI", 10))
        style.configure("Action.TButton", font=("Segoe UI", 10, "bold"), padding=(12, 7))
        style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"), padding=(12, 7), background="#3875ff")
        style.map("Accent.TButton", background=[("active", "#5b8cff")])
        style.configure("Treeview", rowheight=28, font=("Segoe UI", 9), fieldbackground="#121722", background="#121722", foreground="#e7edf5")
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))

    def _build_input_panel(self, parent: ttk.Frame) -> None:
        ttk.Label(parent, text="Input", style="Section.TLabel").pack(anchor="w")

        tesseract_frame = ttk.Frame(parent, style="Panel.TFrame")
        tesseract_frame.pack(fill="x", pady=(10, 0))
        ttk.Label(tesseract_frame, text="Tesseract path", style="Field.TLabel").grid(row=0, column=0, sticky="w")
        tesseract_entry = ttk.Entry(tesseract_frame, textvariable=self.tesseract_path_var)
        tesseract_entry.grid(row=1, column=0, sticky="ew", pady=(4, 0))
        ttk.Button(tesseract_frame, text="Browse", style="Action.TButton", command=self._browse_tesseract).grid(row=1, column=1, padx=(8, 0), pady=(4, 0))
        tesseract_frame.columnconfigure(0, weight=1)

        button_row = ttk.Frame(parent, style="Panel.TFrame")
        button_row.pack(fill="x", pady=(12, 0))
        ttk.Button(button_row, text="Paste Screenshot (Ctrl+V)", style="Accent.TButton", command=self._paste_from_clipboard).pack(fill="x")
        self.naming_mode_button = ttk.Button(button_row, text=self._naming_mode_label(), style="Action.TButton", command=self._toggle_naming_mode)
        self.naming_mode_button.pack(fill="x", pady=(8, 0))
        ttk.Button(button_row, text="Delete Selected", style="Action.TButton", command=self._delete_selected_job).pack(fill="x", pady=(8, 0))
        ttk.Button(button_row, text="Delete All", style="Action.TButton", command=self._clear_jobs).pack(fill="x", pady=(8, 0))
        ttk.Button(button_row, text="Export JSON", style="Action.TButton", command=self._copy_json).pack(fill="x", pady=(8, 0))

    def _build_results_panel(self, parent: ttk.Frame) -> None:
        ttk.Label(parent, text="Jobs", style="Section.TLabel").pack(anchor="w")

        tree_frame = ttk.Frame(parent, style="Panel.TFrame")
        tree_frame.pack(fill="both", expand=True, pady=(10, 0))

        columns = ("file", "time", "filament", "confidence")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="browse")
        self.tree.heading("file", text="File")
        self.tree.heading("time", text="Time")
        self.tree.heading("filament", text="Filament")
        self.tree.heading("confidence", text="Confidence")

        self.tree.column("file", width=360, anchor="w")
        self.tree.column("time", width=120, anchor="center")
        self.tree.column("filament", width=120, anchor="center")
        self.tree.column("confidence", width=90, anchor="center")

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.tree.bind("<<TreeviewSelect>>", self._on_selection_changed)

        totals = ttk.Frame(parent, style="Panel.TFrame")
        totals.pack(fill="x", pady=(14, 0))

        self._metric(totals, 0, "Jobs", self.job_count_var)
        self._metric(totals, 1, "Total time", self.total_time_var)
        self._metric(totals, 2, "Total filament", self.total_filament_var)
        self._metric(totals, 3, "Average confidence", self.confidence_var)

        self.preview_var = tk.StringVar(value="No screenshot selected")
        preview_frame = ttk.Frame(parent, style="Panel.TFrame")
        preview_frame.pack(fill="x", pady=(14, 0))
        ttk.Label(preview_frame, text="Current selection", style="Field.TLabel").pack(anchor="w")
        ttk.Label(preview_frame, textvariable=self.preview_var, style="Value.TLabel", wraplength=520, justify="left").pack(anchor="w", pady=(2, 0))

    def _bind_shortcuts(self) -> None:
        self.bind_all("<Control-v>", self._handle_paste_shortcut, add="+")
        self.bind_all("<Control-V>", self._handle_paste_shortcut, add="+")

    def _naming_mode_label(self) -> str:
        if self.naming_mode_var.get() == "sequential":
            return "Naming mode: Sequential"
        return "Naming mode: Manual"

    def _toggle_naming_mode(self) -> None:
        if self.naming_mode_var.get() == "sequential":
            self.naming_mode_var.set("manual")
            self.status_var.set("Naming mode set to manual.")
        else:
            self.naming_mode_var.set("sequential")
            self.status_var.set("Naming mode set to sequential.")

        if self.naming_mode_button is not None:
            self.naming_mode_button.configure(text=self._naming_mode_label())

    def _metric(self, parent: ttk.Frame, column: int, label: str, variable: tk.StringVar) -> None:
        frame = ttk.Frame(parent, style="Panel.TFrame")
        frame.grid(row=0, column=column, sticky="ew", padx=(0, 12))
        ttk.Label(frame, text=label, style="Field.TLabel").pack(anchor="w")
        ttk.Label(frame, textvariable=variable, style="Value.TLabel").pack(anchor="w", pady=(2, 0))
        parent.columnconfigure(column, weight=1)

    def _browse_tesseract(self) -> None:
        path = filedialog.askopenfilename(
            title="Select tesseract.exe",
            filetypes=[("Executable", "tesseract.exe"), ("All files", "*.*")],
        )
        if path:
            self.tesseract_path_var.set(path)

    def _ensure_extractor(self):
        if self.extractor is not None:
            return self.extractor

        try:
            from slicer_data_extractor import SlicerDataExtractor
        except Exception as exc:
            messagebox.showerror(
                "Dependency missing",
                "Could not import slicer_data_extractor.py.\n\n"
                f"Details: {exc}",
            )
            return None

        self.extractor = SlicerDataExtractor(tesseract_path=self.tesseract_path_var.get().strip() or None)
        return self.extractor

    def _ensure_debug_window(self):
        if not self.debug_enabled:
            return None
        if self.debug_window is not None:
            try:
                if self.debug_window.winfo_exists():
                    return self.debug_window
            except tk.TclError:
                pass
            self.debug_window = None

        if self.debug_window is not None:
            return self.debug_window

        try:
            from ocr_debug_viewer import OCRDebugViewer
        except Exception as exc:
            self.status_var.set(f"Debug viewer unavailable: {exc}")
            return None

        self.debug_window = OCRDebugViewer(self)
        return self.debug_window

    def _set_busy(self, busy: bool, message: str = "") -> None:
        if busy:
            self.progress_var.set(message or "Working...")
            self.progress_container.pack(fill="x", pady=(10, 0))
            self.progress_bar.start(12)
        else:
            self.progress_bar.stop()
            self.progress_container.pack_forget()
            self.progress_var.set("")

    def _run_in_worker(self, target, *args) -> None:
        thread = threading.Thread(target=target, args=args, daemon=True)
        thread.start()

    def _get_display_name_for_clipboard_item(self) -> Optional[str]:
        if self.naming_mode_var.get() == "sequential":
            name = f"Screenshot {self._next_manual_name_index}"
            self._next_manual_name_index += 1
            return name

        name = simpledialog.askstring(
            "Name screenshot",
            "Enter a name for this screenshot:",
            parent=self,
        )
        if name is None:
            return None

        clean_name = name.strip()
        if not clean_name:
            clean_name = f"Screenshot {self._next_manual_name_index}"
            self._next_manual_name_index += 1
        return clean_name

    def _handle_paste_shortcut(self, event: tk.Event) -> str:
        self._paste_from_clipboard()
        return "break"

    def _prepare_clipboard_items(self) -> List[Dict[str, Any]]:
        extractor = self._ensure_extractor()
        if extractor is None:
            return []

        clipboard = ImageGrab.grabclipboard()
        if clipboard is None:
            messagebox.showinfo("Clipboard empty", "No image was found on the clipboard. Copy a screenshot first, then press Ctrl+V.")
            return []

        items: List[Any] = []
        if isinstance(clipboard, list):
            items.extend(str(item) for item in clipboard if str(item).lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".webp")))
        else:
            items.append(clipboard)

        if not items:
            messagebox.showinfo("Clipboard content unsupported", "The clipboard does not contain a screenshot image file.")
            return []

        prepared: List[Dict[str, Any]] = []
        for item in items:
            display_name = self._get_display_name_for_clipboard_item()
            if display_name is None:
                continue
            prepared.append({"item": item, "display_name": display_name})

        return prepared

    def _paste_from_clipboard(self) -> None:
        prepared_items = self._prepare_clipboard_items()
        if not prepared_items:
            return

        self._set_busy(True, f"Processing {len(prepared_items)} screenshot(s)...")
        self.status_var.set(f"Processing {len(prepared_items)} screenshot(s)...")
        self._run_in_worker(self._process_clipboard_items_worker, prepared_items)

    def _process_clipboard_items_worker(self, prepared_items: List[Dict[str, Any]]) -> None:
        extractor = self._ensure_extractor()
        if extractor is None:
            self.after(0, lambda: self._set_busy(False))
            return

        added_records: List[JobRecord] = []
        failures: List[str] = []

        for index, entry in enumerate(prepared_items, 1):
            item = entry["item"]
            display_name = entry["display_name"]
            try:
                if isinstance(item, str):
                    result = extractor.extract_from_file(item, return_debug=True)
                    source_image = Image.open(item).copy()
                else:
                    result = extractor.extract_from_image(item, return_debug=True)
                    source_image = item.copy()
                record = self._extract_record_from_result(display_name, result)
                record.source_image = source_image
                record.debug_info = getattr(result, "debug_info", None)
                added_records.append(record)
                self.after(0, lambda n=index, t=len(prepared_items): self.status_var.set(f"Processing OCR {n}/{t}..."))
            except Exception as exc:
                failures.append(f"{display_name}: {exc}")

        def finalize() -> None:
            for record in added_records:
                self.calculator.add_record(record)
                self._insert_row(record)
            if self.debug_enabled and added_records:
                debug_window = self._ensure_debug_window()
                if debug_window is not None:
                    try:
                        debug_window.show_record(added_records[-1])
                    except tk.TclError:
                        self.debug_window = None
            # If extraction looks ambiguous, prompt the user to recapture.
            for record in added_records:
                try:
                    ambiguous = getattr(record, "time_ambiguous", False)
                    low_conf = float(getattr(record, "confidence", 0.0)) < 0.6
                except Exception:
                    ambiguous = False
                    low_conf = False
                if ambiguous or low_conf:
                    name = record.file_path
                    msg = (
                        f"Extraction for '{name}' looks ambiguous (confidence {record.confidence:.2f}).\n"
                        "It may have chosen 'Model printing time' instead of 'Total time', or units may be misread.\n\n"
                        "Would you like to re-capture the screenshot and try again?"
                    )
                    retry = messagebox.askyesno("Ambiguous extraction", msg)
                    if retry:
                        messagebox.showinfo("Re-capture", "Please re-capture the slicer screenshot and press Ctrl+V to paste it into the app.")
                        self.status_var.set("Awaiting recapture and paste (Ctrl+V)...")
            self._refresh_after_change()
            self._set_busy(False)
            if failures:
                messagebox.showwarning("Some clipboard items failed", "\n".join(failures))
            self.status_var.set(f"Pasted {len(added_records)} screenshot(s) from clipboard.")

        self.after(0, finalize)

    def _extract_record_from_result(self, file_path: str, result: Any) -> JobRecord:
        data = result.to_dict()
        return JobRecord(
            file_path=file_path,
            print_time_hours=int(data["print_time"]["hours"]),
            print_time_minutes=int(data["print_time"]["minutes"]),
            print_time_seconds=int(data["print_time"]["seconds"]),
            total_seconds=int(data["print_time"]["total_seconds"]),
            filament_grams=float(data["filament"]["amount_grams"]),
            filament_kilograms=float(data["filament"]["amount_kilograms"]),
            filament_unit=str(data["filament"]["unit"]),
            confidence=float(data.get("confidence", 0.0)),
            time_ambiguous=bool(getattr(result, "time_ambiguous", False)),
            raw_text=str(data.get("raw_text", "")),
        )

    def _insert_row(self, record: JobRecord) -> None:
        filename = record.file_path
        self._row_counter += 1
        self.tree.insert(
            "",
            "end",
            iid=str(self._row_counter),
            values=(
                filename,
                self.calculator.format_time(record.total_seconds),
                self.calculator.format_filament(record.filament_grams),
                f"{record.confidence:.2f}",
            ),
        )

    def _delete_selected_job(self) -> None:
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Nothing selected", "Select a screenshot in the history list first.")
            return

        index = self.tree.index(selected[0])
        self.tree.delete(selected[0])
        if 0 <= index < len(self.calculator.records):
            del self.calculator.records[index]
        self._refresh_after_change()
        self.status_var.set("Selected screenshot deleted.")

    def _clear_jobs(self) -> None:
        self.calculator.clear()
        for item in self.tree.get_children():
            self.tree.delete(item)
        self._refresh_after_change()
        self.status_var.set("Job list cleared.")

    def _on_selection_changed(self, event: tk.Event) -> None:
        selected = self.tree.selection()
        if not selected:
            self.preview_var.set("No screenshot selected")
            return

        index = self.tree.index(selected[0])
        if 0 <= index < len(self.calculator.records):
            record = self.calculator.records[index]
            self.preview_var.set(f"{record.file_path} | {self.calculator.format_time(record.total_seconds)} | {self.calculator.format_filament(record.filament_grams)}")
        else:
            self.preview_var.set("Selected item is unavailable")

    def _copy_json(self) -> None:
        payload = self.calculator.to_json()
        self.output_json = payload
        self.clipboard_clear()
        self.clipboard_append(payload)
        self.status_var.set("JSON copied to clipboard.")

    def _refresh_after_change(self) -> None:
        totals = self.calculator.totals()
        self.job_count_var.set(str(totals["job_count"]))
        self.total_time_var.set(totals["total_time"])
        self.total_filament_var.set(totals["total_filament_formatted"])

        if self.calculator.records:
            # Use average confidence across all records instead of best.
            confidences = [float(record.confidence) for record in self.calculator.records if hasattr(record, 'confidence')]
            if confidences:
                avg_conf = sum(confidences) / len(confidences)
                self.confidence_var.set(f"{avg_conf:.2f}")
            else:
                self.confidence_var.set("-")
        else:
            self.confidence_var.set("-")
        self.output_json = self.calculator.to_json()


def main() -> None:
    app = SlicerCalculatorApp()
    app.mainloop()


if __name__ == "__main__":
    main()