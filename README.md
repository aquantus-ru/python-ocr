# OCR Scanner

This script uses Tesseract OCR to extract text from PDFs, images, and videos.

## Installation

1.  **Install Tesseract:**
    *   **macOS:** `brew install tesseract`
    *   **Ubuntu:** `sudo apt-get install tesseract-ocr`
    *   **Windows:** Download from the [official Tesseract repository](https://github.com/UB-Mannheim/tesseract/wiki).

2.  **Install Poppler:** (Required for PDF processing)
    *   **macOS:** `brew install poppler`
    *   **Ubuntu:** `sudo apt-get install poppler-utils`
    *   **Windows:** Download from the [Poppler for Windows](https://github.com/oschwartz10612/poppler-windows/releases/) page.

3.  **Install Python dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Usage

```bash
python ocr_scanner.py --input <file_or_directory> --output <output_directory>
```
