from tkinter import *
from tkinter import filedialog, messagebox, ttk
import os
import threading
from datetime import datetime, timezone

from annotation.cli import (
    annotate_genes,
    export_results,
    launch_viewer,
    setup_logging,
    parse_gene_file,
)
from annotation.summary import compute_summary, format_summary_text
from annotation.config import DEFAULT_OUTPUT_DIR, VERSION, SAMPLE_GENES_FILE, APP_NAME
from annotation.paths import resolve_output_stem


def interface():
    setup_logging()
    window = Tk()
    window.title(f"{APP_NAME} — Gene Annotation")
    window.geometry("580x420")

    mode = StringVar(value="file")
    use_cache = BooleanVar(value=True)
    export_html = BooleanVar(value=True)
    export_csv = BooleanVar(value=True)
    export_excel = BooleanVar(value=False)
    export_json = BooleanVar(value=False)
    open_viewer_after = BooleanVar(value=False)
    workers = IntVar(value=1)
    output_dir = StringVar(value=str(DEFAULT_OUTPUT_DIR))

    Label(window, text="Mode").pack(anchor="w", padx=10, pady=(10, 0))
    Radiobutton(window, text="Text file (.txt)", variable=mode, value="file").pack(anchor="w", padx=20)
    Radiobutton(window, text="Single gene", variable=mode, value="single").pack(anchor="w", padx=20)

    file_path = StringVar(value=str(SAMPLE_GENES_FILE))
    gene_value = StringVar(value="RAD51,homo_sapiens")

    file_entry = Entry(window, textvariable=file_path, width=60)
    gene_entry = Entry(window, textvariable=gene_value, width=60)

    def toggle_fields():
        if mode.get() == "file":
            gene_entry.pack_forget()
            file_entry.pack(padx=10, pady=5)
        else:
            file_entry.pack_forget()
            gene_entry.pack(padx=10, pady=5)

    def browse_file():
        selected = filedialog.askopenfilename(
            title="Select a gene file",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if selected:
            file_path.set(selected)

    Button(window, text="Browse...", command=browse_file).pack(pady=2)
    toggle_fields()
    mode.trace_add("write", lambda *_: toggle_fields())

    dir_frame = Frame(window)
    dir_frame.pack(fill="x", padx=10, pady=4)
    Label(dir_frame, text="Output folder:").pack(side=LEFT)
    Entry(dir_frame, textvariable=output_dir, width=45).pack(side=LEFT, padx=6)

    options = Frame(window)
    options.pack(pady=8)
    Checkbutton(options, text="Cache", variable=use_cache).pack(side=LEFT, padx=6)
    Checkbutton(options, text="HTML", variable=export_html).pack(side=LEFT, padx=6)
    Checkbutton(options, text="CSV", variable=export_csv).pack(side=LEFT, padx=6)
    Checkbutton(options, text="Excel", variable=export_excel).pack(side=LEFT, padx=6)
    Checkbutton(options, text="JSON", variable=export_json).pack(side=LEFT, padx=6)

    worker_frame = Frame(window)
    worker_frame.pack(pady=4)
    Label(worker_frame, text="Parallel workers:").pack(side=LEFT, padx=6)
    ttk.Spinbox(worker_frame, from_=1, to=4, textvariable=workers, width=5).pack(side=LEFT)
    Checkbutton(worker_frame, text="Open viewer after run", variable=open_viewer_after).pack(side=LEFT, padx=12)

    status = Label(window, text="Ready.", fg="gray")
    status.pack(pady=4)

    progress = ttk.Progressbar(window, mode="indeterminate", length=400)
    progress.pack(pady=4)
    progress.pack_forget()

    run_button = Button(window, text="Run annotation", width=25)

    def run_annotation():
        try:
            out_dir = output_dir.get().strip() or str(DEFAULT_OUTPUT_DIR)

            if mode.get() == "file":
                input_file = file_path.get().strip()
                if not os.path.exists(input_file):
                    messagebox.showerror("Error", "File not found.")
                    return
                genes = parse_gene_file(input_file)
                if not genes:
                    messagebox.showerror("Error", "No valid genes in file.")
                    return
                input_for_export = input_file
                output_stem = None
            else:
                value = gene_value.get().strip()
                if "," not in value:
                    messagebox.showerror("Error", "Expected format: GENE,organism")
                    return
                gene, organism = value.split(",", 1)
                genes = [(gene.strip(), organism.strip())]
                input_for_export = None
                output_stem = resolve_output_stem(
                    f"{gene.strip()}_{organism.strip()}.txt",
                    out_dir,
                )

            status.config(text="Annotating...", fg="blue")
            progress.pack(pady=4)
            progress.start(12)
            run_button.config(state=DISABLED)
            window.update()

            infos, stats = annotate_genes(
                genes,
                use_cache=use_cache.get(),
                workers=max(1, min(4, workers.get())),
            )
            summary = compute_summary(infos, meta=stats)
            metadata = {
                "version": VERSION,
                "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "gene_count": len(genes),
            }

            export_results(
                infos,
                summary,
                input_file=input_for_export,
                output_stem=output_stem,
                output_dir=out_dir,
                export_html=export_html.get(),
                export_csv=export_csv.get(),
                export_excel=export_excel.get(),
                export_json=export_json.get(),
                metadata=metadata,
            )

            if open_viewer_after.get():
                launch_viewer(out_dir)

            progress.stop()
            progress.pack_forget()
            run_button.config(state=NORMAL)
            status.config(text=f"Done. Results in {out_dir}", fg="green")
            messagebox.showinfo("Done", format_summary_text(summary))
        except Exception as error:
            progress.stop()
            progress.pack_forget()
            run_button.config(state=NORMAL)
            status.config(text="Error.", fg="red")
            messagebox.showerror("Error", str(error))

    def start():
        threading.Thread(target=run_annotation, daemon=True).start()

    run_button.config(command=start)
    run_button.pack(pady=6)

    def open_viewer():
        launch_viewer(output_dir.get().strip() or str(DEFAULT_OUTPUT_DIR))

    Button(window, text="Open web viewer", command=open_viewer, width=25).pack(pady=4)
    window.mainloop()


if __name__ == "__main__":
    interface()
