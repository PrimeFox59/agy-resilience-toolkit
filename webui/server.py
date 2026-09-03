#!/usr/bin/env python3
"""
Antigravity Web UI Server
Antarmuka Web Modern untuk Google Antigravity CLI (AGY) dengan dukungan:
- Lampiran Gambar / Foto (Drag-and-Drop & Clipboard Paste Ctrl+V)
- Multi-Account Google Switching & Auto-Fallback Kuota
- Real-time Streaming Output (Server-Sent Events)
- Markdown & Code Highlighting
"""

import sys
import os
import time
import json
import uuid
import base64
import subprocess
import threading
from flask import Flask, request, jsonify, Response, send_from_directory, render_template

# Tambahkan path agy_account ke system path
AGY_BIN_DIR = r"C:\Users\PRIMA\AppData\Local\agy\bin"
if AGY_BIN_DIR not in sys.path:
    sys.path.append(AGY_BIN_DIR)

import agy_account

APP_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOADS_DIR = os.path.join(APP_DIR, "uploads")
STATIC_DIR = os.path.join(APP_DIR, "static")
TEMPLATES_DIR = os.path.join(APP_DIR, "templates")

os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)

app = Flask(__name__, template_folder=TEMPLATES_DIR, static_folder=STATIC_DIR)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max upload

# Global state untuk mengontrol proses yang sedang berjalan
current_process = None
process_lock = threading.Lock()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/uploads/<path:filename>')
def serve_upload(filename):
    return send_from_directory(UPLOADS_DIR, filename)

@app.route('/api/accounts', methods=['GET'])
def get_accounts():
    """Mengambil daftar akun Google dan akun yang sedang aktif."""
    try:
        meta = agy_account.load_metadata()
        current_blob = agy_account.get_current_credential_blob()
        
        accs = []
        for a in meta.get('accounts', []):
            path = os.path.join(agy_account.PROFILES_DIR, f"{a}.dat")
            exists = os.path.exists(path)
            is_active = (a == meta.get('active', ''))
            accs.append({
                'name': a,
                'active': is_active,
                'ready': exists
            })
            
        return jsonify({
            'success': True,
            'active': meta.get('active', ''),
            'accounts': accs
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/accounts/switch', methods=['POST'])
def switch_account():
    """Berpindah ke akun Google tertentu."""
    data = request.get_json() or {}
    name = data.get('name')
    if not name:
        return jsonify({'success': False, 'error': 'Nama akun diperlukan'}), 400
    
    success = agy_account.switch_profile(name, silent=True)
    if success:
        return jsonify({'success': True, 'active': name})
    return jsonify({'success': False, 'error': f'Gagal beralih ke {name}'}), 500

@app.route('/api/accounts/add', methods=['POST'])
def add_account():
    """Memicu proses penambahan akun baru (membuka browser)."""
    data = request.get_json() or {}
    name = data.get('name', f"akun_{int(time.time())}")
    
    def run_add():
        agy_account.add_new_account(name)
        
    threading.Thread(target=run_add, daemon=True).start()
    return jsonify({'success': True, 'message': f'Proses login akun {name} telah dimulai di browser.'})

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Menangani upload gambar via file picker, drag-and-drop, atau Ctrl+V (base64/binary)."""
    try:
        uploaded_files = []
        
        # 1. Dari Multipart Form-Data
        if 'files' in request.files:
            files = request.files.getlist('files')
            for f in files:
                if f.filename:
                    ext = os.path.splitext(f.filename)[1].lower() or '.png'
                    safe_name = f"img_{int(time.time())}_{uuid.uuid4().hex[:6]}{ext}"
                    dest_path = os.path.join(UPLOADS_DIR, safe_name)
                    f.save(dest_path)
                    uploaded_files.append({
                        'fileName': f.filename,
                        'savedName': safe_name,
                        'absolutePath': dest_path,
                        'url': f"/uploads/{safe_name}"
                    })
                    
        # 2. Dari Base64 Data URL (Clipboard Paste)
        json_data = request.get_json(silent=True)
        if json_data and 'base64Data' in json_data:
            b64_str = json_data['base64Data']
            if ',' in b64_str:
                header, b64_str = b64_str.split(',', 1)
                
            img_bytes = base64.b64decode(b64_str)
            safe_name = f"clipboard_{int(time.time())}_{uuid.uuid4().hex[:6]}.png"
            dest_path = os.path.join(UPLOADS_DIR, safe_name)
            with open(dest_path, 'wb') as f:
                f.write(img_bytes)
                
            uploaded_files.append({
                'fileName': 'Clipboard_Screenshot.png',
                'savedName': safe_name,
                'absolutePath': dest_path,
                'url': f"/uploads/{safe_name}"
            })
            
        return jsonify({'success': True, 'files': uploaded_files})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/chat', methods=['POST'])
def chat_stream():
    """Streaming interaksi AGY CLI dengan auto-fallback Google account dan multimodal attachment."""
    global current_process
    
    data = request.get_json() or {}
    prompt = data.get('prompt', '').strip()
    model = data.get('model', 'gemini-3.8-flash-high')
    cwd = data.get('cwd', r"C:\Users\PRIMA")
    images = data.get('images', [])  # list of absolute paths
    continue_session = data.get('continueSession', False)
    
    if not prompt and not images:
        return jsonify({'error': 'Prompt atau gambar diperlukan'}), 400
        
    # Format instruksi multimodal untuk agent jika ada gambar terlampir
    if images:
        image_instructions = "\n\n[LAMPIRAN GAMBAR/FOTO DARI USER]:\n"
        for idx, img_path in enumerate(images, 1):
            image_instructions += f"{idx}. File Path: {img_path}\n"
        image_instructions += "Instruksi: Gunakan kemampuan inspeksi file / vision untuk menganalisis dan memahami konten gambar di atas dalam menyelesaikan permintaan user."
        full_prompt = prompt + image_instructions
    else:
        full_prompt = prompt

    def generate():
        global current_process
        
        target_prompt = full_prompt
        use_continue = continue_session
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            retry_count += 1
            meta = agy_account.load_metadata()
            active_acc = meta.get('active', 'default')
            
            yield f"data: {json.dumps({'type': 'status', 'account': active_acc, 'model': model})}\n\n"
            
            cmd = [agy_account.AGY_EXE]
            if use_continue:
                cmd.append("-c")
            cmd.extend(["-p", target_prompt, "--model", model])
            
            with process_lock:
                current_process = subprocess.Popen(
                    cmd,
                    cwd=cwd if os.path.isdir(cwd) else r"C:\Users\PRIMA",
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding='utf-8',
                    errors='replace'
                )
            
            is_quota_exhausted = False
            
            for line in iter(current_process.stdout.readline, ''):
                if not line:
                    break
                    
                # Cek jika terjadi error kuota
                lower_line = line.lower()
                for pattern in agy_account.QUOTA_ERROR_PATTERNS:
                    if pattern in lower_line:
                        is_quota_exhausted = True
                        break
                
                yield f"data: {json.dumps({'type': 'chunk', 'text': line})}\n\n"
            
            current_process.stdout.close()
            return_code = current_process.wait()
            
            with process_lock:
                current_process = None
                
            if is_quota_exhausted:
                next_acc = agy_account.get_next_profile()
                if next_acc and next_acc != active_acc:
                    yield f"data: {json.dumps({'type': 'fallback', 'message': f'Kuota Akun [{active_acc}] habis! Otomatis beralih ke Akun [{next_acc}]...'})}\n\n"
                    agy_account.switch_profile(next_acc, silent=True)
                    use_continue = True # Lanjutkan sesi
                    time.sleep(1)
                    continue
                else:
                    yield f"data: {json.dumps({'type': 'error', 'message': 'Semua akun Google yang terdaftar telah mencapai batas kuota.'})}\n\n"
                    break
            else:
                break
                
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return Response(generate(), mimetype='text/event-stream')

@app.route('/api/stop', methods=['POST'])
def stop_process():
    """Menghentikan proses AGY yang sedang berjalan."""
    global current_process
    with process_lock:
        if current_process and current_process.poll() is None:
            current_process.terminate()
            time.sleep(0.5)
            if current_process.poll() is None:
                current_process.kill()
            current_process = None
            return jsonify({'success': True, 'message': 'Proses berhasil dihentikan'})
    return jsonify({'success': True, 'message': 'Tidak ada proses aktif'})

def run_server(port=4567):
    print(f"\n=======================================================")
    print(f"      GOOGLE ANTIGRAVITY WEB UI (AGY VISION HUB)       ")
    print(f"=======================================================")
    print(f" [*] Web UI URL     : http://127.0.0.1:{port}")
    print(f" [*] Upload Folder  : {UPLOADS_DIR}")
    print(f" [*] Multi-Account  : Aktif (Auto-Fallback Ready)")
    print(f" [*] Image Vision   : Aktif (Paste Ctrl+V & Drag-Drop)")
    print(f"-------------------------------------------------------\n")
    app.run(host='127.0.0.1', port=port, debug=False, threaded=True)

if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 4567
    run_server(port)
