FROM python:3.12-slim

# pdflatex plus the packages used by curriculum_template.tex and generate_syllabus_pdf.py
RUN apt-get update && apt-get install -y --no-install-recommends \
        texlive-latex-base texlive-latex-recommended texlive-latex-extra \
        texlive-fonts-recommended texlive-plain-generic \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# app.py runs the syllabus generators with ./venv/bin/python3 when it exists
COPY requirements.txt .
RUN python -m venv /app/venv && /app/venv/bin/pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p output && chown -R 1000:1000 /app/output
USER 1000:1000
ENV HOME=/tmp

EXPOSE 8080
# One worker: compile status is kept in memory and form_data.json is a single file.
CMD ["/app/venv/bin/gunicorn", "-w", "1", "--threads", "4", "--timeout", "180", "-b", "0.0.0.0:8080", "app:app"]
