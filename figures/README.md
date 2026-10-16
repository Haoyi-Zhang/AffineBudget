# Symbolic FCFS diagrams

Install the optional dependency from figures/requirements.txt and run
python -B figures/build_figures.py --outdir /path/to/output.
The PDFs preserve six-job dependencies, the candidate bank-order edge and the
order-switch intervals. Bar widths are schematic, not measured durations.
Fonts are embedded; no TeX backend is used.
The scientific algorithms and retained-result checks do not need Matplotlib.
