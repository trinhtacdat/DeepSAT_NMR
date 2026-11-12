"""Windows desktop interface for the local DeepSAT runner."""

import csv
import json
import os
from pathlib import Path
from queue import Empty, Queue
import subprocess
import sys
from threading import Thread
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from deepsat_local import EXAMPLES, ROOT


class DeepSATApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("DeepSAT Local")
        self.geometry("920x640")
        self.minsize(730, 560)
        self.configure(background="#f6f7fa")
        self.file_path = tk.StringVar()
        self.channel = tk.StringVar(value="Normal HSQC")
        self.mw = tk.StringVar()
        self.status = tk.StringVar(value="Choose a peak list or load an example.")
        self.summary = tk.StringVar()
        self.process = None
        self.messages = Queue()
        self.result_folder = None

        style = ttk.Style(self)
        style.configure("Title.TLabel", font=("Segoe UI", 22, "bold"), foreground="#16314f", background="#f6f7fa")
        style.configure("Treeview", rowheight=27)
        style.configure("Body.TFrame", background="#f6f7fa")
        body = ttk.Frame(self, padding=22, style="Body.TFrame")
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=1)
        body.rowconfigure(3, weight=1)
        ttk.Label(body, text="DeepSAT Local", style="Title.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 12))

        form = ttk.LabelFrame(body, text="HSQC peak list", padding=12)
        form.grid(row=1, column=0, sticky="ew")
        form.columnconfigure(0, weight=1)
        ttk.Entry(form, textvariable=self.file_path).grid(row=0, column=0, columnspan=4, sticky="ew", padx=(0, 8))
        ttk.Button(form, text="Browse…", command=self.browse).grid(row=0, column=4, sticky="ew")
        modes = ttk.Combobox(form, state="readonly", values=("Normal HSQC", "Edited HSQC"), textvariable=self.channel, width=17)
        modes.grid(row=1, column=0, sticky="w", pady=(10, 0))
        ttk.Label(form, text="MW (optional)").grid(row=1, column=1, padx=(10, 5), pady=(10, 0))
        ttk.Entry(form, textvariable=self.mw, width=10).grid(row=1, column=2, pady=(10, 0))
        ttk.Button(form, text="Load example", command=self.load_example).grid(row=1, column=3, padx=8, pady=(10, 0))
        self.run_button = ttk.Button(form, text="Run DeepSAT", command=self.run_analysis)
        self.run_button.grid(row=1, column=4, pady=(10, 0), sticky="ew")
        ttk.Label(body, textvariable=self.status, background="#f6f7fa").grid(row=2, column=0, sticky="w", pady=10)

        tabs = ttk.Notebook(body)
        tabs.grid(row=3, column=0, sticky="nsew")
        results = ttk.Frame(tabs, padding=10)
        log_tab = ttk.Frame(tabs, padding=10)
        tabs.add(results, text="Candidates")
        tabs.add(log_tab, text="Run log")
        ttk.Label(results, textvariable=self.summary, justify="left").pack(anchor="w", pady=(0, 8))
        table = ttk.Frame(results)
        table.pack(fill="both", expand=True)
        self.candidates = ttk.Treeview(table, columns=("name", "score", "mw"), show="headings", selectmode="browse")
        for key, label, width in (("name", "Compound", 510), ("score", "Cosine", 90), ("mw", "MW", 90)):
            self.candidates.heading(key, text=label)
            self.candidates.column(key, width=width, stretch=(key == "name"), anchor="w" if key == "name" else "e")
        scroll = ttk.Scrollbar(table, orient="vertical", command=self.candidates.yview)
        self.candidates.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.candidates.pack(side="left", fill="both", expand=True)

        self.log = tk.Text(log_tab, wrap="word", state="disabled", font=("Consolas", 10))
        self.log.pack(fill="both", expand=True)
        actions = ttk.Frame(results)
        actions.pack(fill="x", pady=(8, 0))
        self.result_buttons = {}
        for filename, label in (("hsqc.png", "Open HSQC plot"), ("structures.png", "Open structures"), ("", "Open result folder")):
            button = ttk.Button(actions, text=label, state="disabled", command=lambda name=filename: self.open_result(name))
            button.pack(side="left", padx=(0, 8))
            self.result_buttons[filename] = button

        self.protocol("WM_DELETE_WINDOW", self.close_app)
        self.after(100, self.poll_messages)

    def browse(self):
        path = filedialog.askopenfilename(filetypes=[("HSQC peak lists", "*.csv *.tsv *.txt"), ("All files", "*.*")])
        if path:
            self.file_path.set(path)

    def selected_channel(self):
        return 2 if self.channel.get() == "Edited HSQC" else 1

    def load_example(self):
        self.file_path.set(str(EXAMPLES[self.selected_channel()]))
        self.mw.set("")

    def run_analysis(self):
        path = Path(self.file_path.get().strip())
        if not path.is_file():
            messagebox.showerror("Peak list required", "Choose an existing CSV or TSV peak list.", parent=self)
            return
        python = Path(sys.executable)
        if python.name.lower() == "pythonw.exe":
            python = python.with_name("python.exe")
        command = [str(python), "-u", str(ROOT / "deepsat_local.py"), str(path.resolve()), "--channel", str(self.selected_channel())]
        if self.mw.get().strip():
            command.extend(["--mw", self.mw.get().strip()])
        try:
            self.process = subprocess.Popen(
                command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace", creationflags=subprocess.CREATE_NO_WINDOW,
            )
        except OSError as error:
            messagebox.showerror("DeepSAT could not start", str(error), parent=self)
            return
        self.run_button.state(["disabled"])
        self.status.set("Starting analysis…")
        self.summary.set("")
        self.candidates.delete(*self.candidates.get_children())
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")
        for button in self.result_buttons.values():
            button.state(["disabled"])
        Thread(target=self.read_output, args=(self.process,), daemon=True).start()

    def read_output(self, process):
        result = None
        with process.stdout as stream:
            for line in stream:
                line = line.strip()
                self.messages.put(("log", line))
                if line.startswith("Result folder: "):
                    result = Path(line.removeprefix("Result folder: "))
        exit_code = process.wait()
        self.messages.put(("finished", result if exit_code == 0 else None))

    def poll_messages(self):
        try:
            while True:
                kind, value = self.messages.get_nowait()
                if kind == "log":
                    self.log.configure(state="normal")
                    self.log.insert("end", value + "\n")
                    self.log.see("end")
                    self.log.configure(state="disabled")
                    if value.startswith(("Read ", "Predicting ", "Searching ", "Saving ", "DeepSAT:")):
                        self.status.set(value)
                else:
                    self.process = None
                    self.run_button.state(["!disabled"])
                    if value is None:
                        if not self.status.get().startswith("DeepSAT:"):
                            self.status.set("Analysis failed. See the Run log for details.")
                    else:
                        self.show_results(value)
        except Empty:
            pass
        self.after(100, self.poll_messages)

    def show_results(self, folder):
        self.result_folder = folder
        try:
            report = json.loads((folder / "prediction.json").read_text(encoding="utf-8"))
            with (folder / "candidates.csv").open(encoding="utf-8-sig", newline="") as source:
                for rank, hit in enumerate(csv.DictReader(source), 1):
                    name = f"{rank}. {hit['Name'].split(' | ', 1)[0]}"
                    self.candidates.insert("", "end", values=(name, f"{float(hit['Cosine score']):.3f}", hit["MW"]))
        except (OSError, ValueError, KeyError) as error:
            self.status.set(f"Could not display the saved results: {error}")
        else:
            top_class = report["predicted_classes"][0]
            self.summary.set(
                f"Predicted MW {report['predicted_mw']:.2f}   |   Search MW {report['search_mw']:.2f}   |   "
                f"Glycoside score {report['glycoside_score']:.1%}\n"
                f"Top predicted class   {top_class['name']} ({top_class['score']:.1%})"
            )
            self.status.set(f"{report['candidate_count']} candidates   |   {report['usable_peaks']} peaks used   |   {report['excluded_peaks']} excluded")
        for filename, button in self.result_buttons.items():
            if (folder / filename).exists():
                button.state(["!disabled"])

    def open_result(self, filename):
        try:
            os.startfile(self.result_folder / filename)
        except OSError as error:
            messagebox.showerror("Could not open result", str(error), parent=self)

    def close_app(self):
        if self.process and self.process.poll() is None:
            if not messagebox.askyesno("DeepSAT is running", "Stop the analysis and close DeepSAT?", parent=self):
                return
            self.process.terminate()
        self.destroy()


if __name__ == "__main__":
    DeepSATApp().mainloop()
