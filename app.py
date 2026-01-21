import os
import sys
import uuid
import subprocess
from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'supersecretkey'
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'temp_uploads')
RESULTS_FOLDER = os.path.join(os.getcwd(), 'temp_results')
ALLOWED_EXTENSIONS = {'pdf'}

# In-memory dictionary to store process handles
# Key: job_id, Value: subprocess.Popen object
JOBS = {}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process():
    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)

    file = request.files['file']

    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)

    if file and allowed_file(file.filename):
        job_id = str(uuid.uuid4())
        filename = secure_filename(file.filename)
        # Use job_id in filename to avoid collisions and track easily
        # But we must keep extension for ocr_scanner to detect type
        extension = filename.rsplit('.', 1)[1].lower()
        save_filename = f"{job_id}.{extension}"
        filepath = os.path.join(UPLOAD_FOLDER, save_filename)

        file.save(filepath)

        try:
            # Construct command args
            lang = request.form.get('lang', 'eng')

            cmd = [
                sys.executable, 'ocr_scanner.py',
                '-i', filepath,
                '-o', RESULTS_FOLDER,
                '-l', lang,
                '--overwrite'
            ]

            if 'grayscale' in request.form:
                cmd.append('--grayscale')

            # Start subprocess
            proc = subprocess.Popen(cmd)
            JOBS[job_id] = proc

            return redirect(url_for('status', job_id=job_id))

        except Exception as e:
            flash(f'Error starting process: {str(e)}')
            if os.path.exists(filepath):
                os.remove(filepath)
            return redirect(url_for('index'))

    else:
        flash('Invalid file type. Only PDF is allowed.')
        return redirect(url_for('index'))

@app.route('/status/<job_id>')
def status(job_id):
    if job_id not in JOBS:
        # Fallback: check if result file exists (in case of server restart)
        # But we can't know if it failed or is still running without the process handle in this simple implementation.
        # We will check only for success.
        result_filename = f"{job_id}.txt"
        result_path = os.path.join(RESULTS_FOLDER, result_filename)
        if os.path.exists(result_path):
             with open(result_path, 'r') as f:
                text = f.read()
             # Cleanup result file (optional, maybe we want to keep it?)
             # Let's clean it up to save space
             os.remove(result_path)
             # Also try to clean upload if it lingers
             upload_path = os.path.join(UPLOAD_FOLDER, f"{job_id}.pdf")
             if os.path.exists(upload_path):
                 os.remove(upload_path)

             return render_template('result.html', text=text)

        return "Job not found or expired", 404

    proc = JOBS[job_id]
    ret_code = proc.poll()

    if ret_code is None:
        # Still running
        return render_template('processing.html', job_id=job_id)

    elif ret_code == 0:
        # Finished successfully
        result_filename = f"{job_id}.txt"
        result_path = os.path.join(RESULTS_FOLDER, result_filename)

        text = ""
        if os.path.exists(result_path):
            with open(result_path, 'r') as f:
                text = f.read()
            os.remove(result_path)
        else:
            text = "Error: Result file not found despite successful exit."

        # Cleanup
        upload_path = os.path.join(UPLOAD_FOLDER, f"{job_id}.pdf")
        if os.path.exists(upload_path):
            os.remove(upload_path)

        del JOBS[job_id]

        return render_template('result.html', text=text)

    else:
        # Failed
        del JOBS[job_id]
        flash("Processing failed.")
        return redirect(url_for('index'))

if __name__ == '__main__':
    # Ensure directories exist
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    if not os.path.exists(RESULTS_FOLDER):
        os.makedirs(RESULTS_FOLDER)

    app.run(debug=True, host='0.0.0.0', port=5000)
