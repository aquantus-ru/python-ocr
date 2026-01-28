import os
import sys
import uuid
import subprocess
import json
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
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
        extension = filename.rsplit('.', 1)[1].lower()
        save_filename = f"{job_id}.{extension}"
        filepath = os.path.join(UPLOAD_FOLDER, save_filename)
        progress_filepath = os.path.join(RESULTS_FOLDER, f"{job_id}.progress")

        file.save(filepath)

        try:
            # Construct command args
            lang = request.form.get('lang', 'eng')

            cmd = [
                sys.executable, 'ocr_scanner.py',
                '-i', filepath,
                '-o', RESULTS_FOLDER,
                '-l', lang,
                '--overwrite',
                '--progress-file', progress_filepath
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
    # Check if client wants JSON
    wants_json = request.args.get('format') == 'json' or request.accept_mimetypes.best == 'application/json'

    if job_id not in JOBS:
        # Check if result file exists (finished job that was cleared from memory or server restarted)
        result_filename = f"{job_id}.txt"
        result_path = os.path.join(RESULTS_FOLDER, result_filename)

        if os.path.exists(result_path):
            if wants_json:
                 return jsonify({'status': 'finished', 'progress': 100})

            with open(result_path, 'r') as f:
                text = f.read()

            # Cleanup
            os.remove(result_path)
            upload_path = os.path.join(UPLOAD_FOLDER, f"{job_id}.pdf")
            if os.path.exists(upload_path):
                os.remove(upload_path)
            progress_path = os.path.join(RESULTS_FOLDER, f"{job_id}.progress")
            if os.path.exists(progress_path):
                os.remove(progress_path)

            return render_template('result.html', text=text)

        if wants_json:
             return jsonify({'status': 'not_found'}), 404
        return "Job not found or expired", 404

    proc = JOBS[job_id]
    ret_code = proc.poll()

    # Read progress file
    progress_data = {"current": 0, "total": 100} # Default
    progress_path = os.path.join(RESULTS_FOLDER, f"{job_id}.progress")
    if os.path.exists(progress_path):
        try:
            with open(progress_path, 'r') as f:
                progress_data = json.load(f)
        except:
            pass # Ignore read errors (e.g. file lock or partial write)

    if ret_code is None:
        # Still running
        if wants_json:
            return jsonify({
                'status': 'processing',
                'current': progress_data.get('current', 0),
                'total': progress_data.get('total', 100) # Default to 100 if unknown, or handle UI logic
            })
        return render_template('processing.html', job_id=job_id)

    elif ret_code == 0:
        # Finished successfully
        if wants_json:
             return jsonify({'status': 'finished', 'current': progress_data.get('total', 100), 'total': progress_data.get('total', 100)})

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
        if os.path.exists(progress_path):
            os.remove(progress_path)

        del JOBS[job_id]

        return render_template('result.html', text=text)

    else:
        # Failed
        del JOBS[job_id]
        if wants_json:
             return jsonify({'status': 'failed'})

        flash("Processing failed.")
        return redirect(url_for('index'))

if __name__ == '__main__':
    # Ensure directories exist
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    if not os.path.exists(RESULTS_FOLDER):
        os.makedirs(RESULTS_FOLDER)

    app.run(debug=True, host='0.0.0.0', port=5000)
