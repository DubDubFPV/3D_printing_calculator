"""OCR debug viewer for the 3D slicer calculator.

Displays the source screenshot and the OCR passes used during extraction,
including word boxes drawn on top of the image.
"""

from __future__ import annotations

from typing import Any, List, Optional

import tkinter as tk
from tkinter import ttk

from PIL import Image, ImageDraw, ImageTk

from slicer_data_extractor import ExtractionDebugInfo, OCRPassDebug, OCRWordBox


class OCRDebugViewer(tk.Toplevel):
    def __init__(self, master: tk.Misc):
        super().__init__(master)
        self.title("OCR Debug Viewer")
        self.geometry("1200x800")
        self.minsize(900, 650)
        self.configure(bg="#111722")

        self._photo_refs: List[ImageTk.PhotoImage] = []
        self._current_record = None

        self.summary_var = tk.StringVar(value="No screenshot loaded")
        self.details_var = tk.StringVar(value="")

        self.protocol("WM_DELETE_WINDOW", self._close)
        self._build_ui()

    def _close(self) -> None:
        self.destroy()

    def _build_ui(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("DebugRoot.TFrame", background="#111722")
        style.configure("DebugPanel.TFrame", background="#171d2b")
        style.configure("DebugTitle.TLabel", background="#171d2b", foreground="#f4f7fb", font=("Segoe UI", 15, "bold"))
        style.configure("DebugText.TLabel", background="#171d2b", foreground="#c8d2e0", font=("Segoe UI", 10))
        style.configure("DebugValue.TLabel", background="#171d2b", foreground="#ffffff", font=("Segoe UI", 10, "bold"))

        root = ttk.Frame(self, style="DebugRoot.TFrame", padding=12)
        root.pack(fill="both", expand=True)

        header = ttk.Frame(root, style="DebugPanel.TFrame", padding=12)
        header.pack(fill="x")
        ttk.Label(header, text="OCR Debug Viewer", style="DebugTitle.TLabel").pack(anchor="w")
        ttk.Label(header, textvariable=self.summary_var, style="DebugText.TLabel").pack(anchor="w", pady=(4, 0))
        ttk.Label(header, textvariable=self.details_var, style="DebugValue.TLabel").pack(anchor="w", pady=(2, 0))

        body = ttk.Frame(root, style="DebugRoot.TFrame")
        body.pack(fill="both", expand=True, pady=(12, 0))
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=2)
        body.rowconfigure(0, weight=1)

        self.notebook = ttk.Notebook(body)
        self.notebook.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        right = ttk.Frame(body, style="DebugPanel.TFrame", padding=12)
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure(1, weight=1)
        right.columnconfigure(0, weight=1)

        ttk.Label(right, text="OCR Text", style="DebugTitle.TLabel").grid(row=0, column=0, sticky="w")
        self.text_box = tk.Text(
            right,
            wrap="word",
            bg="#111722",
            fg="#e7edf5",
            insertbackground="#e7edf5",
            relief="flat",
            font=("Consolas", 9),
        )
        self.text_box.grid(row=1, column=0, sticky="nsew", pady=(8, 0))

        self.image_tabs: List[dict[str, Any]] = []

    def show_record(self, record: Any) -> None:
        try:
            if not self.winfo_exists():
                return
        except tk.TclError:
            return

        self._current_record = record
        debug_info: Optional[ExtractionDebugInfo] = getattr(record, "debug_info", None)
        source_image: Optional[Image.Image] = getattr(record, "source_image", None)

        self.summary_var.set(f"{getattr(record, 'file_path', 'Screenshot')} | Time: {getattr(record, 'print_time_hours', 0)}h {getattr(record, 'print_time_minutes', 0)}m {getattr(record, 'print_time_seconds', 0)}s | Filament: {getattr(record, 'filament_grams', 0.0):.2f} g")
        self.details_var.set(f"Confidence: {getattr(record, 'confidence', 0.0):.2f}")

        try:
            self.text_box.delete("1.0", tk.END)
        except tk.TclError:
            return
        for tab in self.notebook.tabs():
            self.notebook.forget(tab)
        self.image_tabs.clear()
        self._photo_refs.clear()

        if debug_info is None or source_image is None:
            self.text_box.insert(tk.END, "No debug data was attached to this record.")
            return

        passes = debug_info.passes
        selected_index = min(debug_info.selected_pass_index, max(len(passes) - 1, 0))

        for index, pass_debug in enumerate(passes):
            tab = ttk.Frame(self.notebook)
            tab.rowconfigure(0, weight=1)
            tab.columnconfigure(0, weight=1)
            self.notebook.add(tab, text=self._tab_label(pass_debug, index, selected_index))

            canvas = tk.Canvas(tab, bg="#0e1420", highlightthickness=0)
            canvas.grid(row=0, column=0, sticky="nsew")
            self._render_pass(canvas, pass_debug, source_image)
            self.image_tabs.append({"canvas": canvas, "pass": pass_debug})

        if passes:
            self._show_pass_text(passes[selected_index])

    def _tab_label(self, pass_debug: OCRPassDebug, index: int, selected_index: int) -> str:
        label = f"{index + 1}. {pass_debug.variant_label}"
        if index == selected_index:
            label += " *"
        return label

    def _show_pass_text(self, pass_debug: OCRPassDebug) -> None:
        try:
            self.text_box.delete("1.0", tk.END)
            self.text_box.insert(tk.END, f"Variant: {pass_debug.variant_label}\nConfig: {pass_debug.config}\n\n")
            self.text_box.insert(tk.END, pass_debug.text)
        except tk.TclError:
            return

    def _render_pass(self, canvas: tk.Canvas, pass_debug: OCRPassDebug, source_image: Image.Image) -> None:
        image = source_image.convert("RGB")
        max_width = 900
        max_height = 600
        scale = min(max_width / image.width, max_height / image.height, 1.0)
        display_size = (max(1, int(image.width * scale)), max(1, int(image.height * scale)))
        display_image = image.resize(display_size, Image.Resampling.LANCZOS if hasattr(Image, "Resampling") else Image.BICUBIC)

        draw = ImageDraw.Draw(display_image)
        for word in pass_debug.word_boxes:
            left = int(word.left * scale)
            top = int(word.top * scale)
            right = int((word.left + word.width) * scale)
            bottom = int((word.top + word.height) * scale)
            color = "#ffd166"
            if any(ch.isdigit() for ch in word.text) or word.text.lower() in {"total", "time", "model", "material", "filament", "g", "kg"}:
                color = "#ff5f5f"
            draw.rectangle((left, top, right, bottom), outline=color, width=2)

        photo = ImageTk.PhotoImage(display_image)
        self._photo_refs.append(photo)
        canvas.configure(width=display_image.width, height=display_image.height, scrollregion=(0, 0, display_image.width, display_image.height))
        canvas.create_image(0, 0, anchor="nw", image=photo)

        # Add a tiny footer with the pass metadata for quick inspection.
        footer = f"{pass_debug.variant_label} | OCR words: {len(pass_debug.word_boxes)}"
        canvas.create_rectangle(0, max(0, display_image.height - 22), display_image.width, display_image.height, fill="#111722", outline="")
        canvas.create_text(8, display_image.height - 11, anchor="w", fill="#d7e0ea", text=footer, font=("Segoe UI", 9, "bold"))


__all__ = ["OCRDebugViewer"]
