FROM python:3.12-slim

# PyMuPDF ships manylinux wheels for cp312; no system libs needed.
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple \
        pymupdf==2.1 pillow==12.3.0 numpy==2.5.1

WORKDIR /app
COPY . /app

# smoke test: the CLI must answer --help inside the image
RUN python outputs/scripts/parse_pdf.py --help >/dev/null

ENTRYPOINT ["python", "src/reproduce.py"]
