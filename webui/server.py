#!/usr/bin/env python3
"""
Antigravity Web UI Server
Modern Executive Web UI for Google Antigravity CLI (AGY):
- Sidebar with full conversation history imported directly from AGY CLI sessions
- Multimodal Image & Screenshot Attachment (Paste Ctrl+V & Drag-Drop)
- Multi-Account Google Credential Swapping & Auto-Fallback Quota
- Real-time Server-Sent Events (SSE) Streaming
- Markdown & Code Syntax Highlighting with 1-Click Copy
"""

import sys
import os
import time
import json
import uuid
import re
import base64
import sqlite3
import subprocess
import threading
from datetime import datetime, timezone, timedelta
from flask import Flask, request, jsonify, Response, send_from_directory, send_file, render_template

# Tambahkan path agy_account ke sys.path
AGY_BIN_DIR = r"C:\Users\PRIMA\AppData\Local\agy\bin"
if AGY_BIN_DIR not in sys.path:
    sys.path.append(AGY_BIN_DIR)

import agy_account

APP_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOADS_DIR = os.path.join(APP_DIR, "uploads")
STATIC_DIR = os.path.join(APP_DIR, "static")
TEMPLATES_DIR = os.path.join(APP_DIR, "templates")
SUMMARIES_DB = r"C:\Users\PRIMA\.gemini\antigravity-cli\conversation_summaries.db"
BRAIN_DIR = r"C:\Users\PRIMA\.gemini\antigravity-cli\brain"

os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)

app = Flask(__name__, template_folder=TEMPLATES_DIR, static_folder=STATIC_DIR)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

current_process = None
process_lock = threading.Lock()

def get_db_connection():
    if os.path.exists(SUMMARIES_DB):
        conn = sqlite3.connect(SUMMARIES_DB, timeout=5.0)
        conn.row_factory = sqlite3.Row
        return conn
    return None

def format_relative_time(iso_str):
    """Mengubah timestamp ISO ke label waktu ramah pengguna (Hari ini, Kemarin, dll)."""
    if not iso_str:
        return "", "Lainnya"
    try:
        # Bersihkan format timezone jika ada
        clean_str = iso_str.split('+')[0].split('.')[0].strip()
        dt = datetime.strptime(clean_str, "%Y-%m-%d %H:%M:%S")
        
        # Asumsikan UTC jika tidak ada timezone, konversi ke lokal WIB (+7)
        dt_local = dt + timedelta(hours=7)
        now_local = datetime.now()
        
        time_display = dt_local.strftime("%H:%M")
        date_diff = (now_local.date() - dt_local.date()).days
        
        if date_diff == 0:
            return time_display, "Hari Ini"
        elif date_diff == 1:
            return time_display, "Kemarin"
        elif date_diff < 7:
            return dt_local.strftime("%a %H:%M"), "7 Hari Terakhir"
        elif date_diff < 30:
            return dt_local.strftime("%d %b"), "Bulan Ini"
        else:
            return dt_local.strftime("%d/%m/%y"), "Lebih Lama"
    except Exception:
        return iso_str[:10], "Lainnya"

@app.route('/')
def index():
    resp = Flask.make_response(app, render_template('index.html'))
    resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    resp.headers['Pragma'] = 'no-cache'
    resp.headers['Expires'] = '0'
    return resp

@app.route('/uploads/<path:filename>')
def serve_upload(filename):
    return send_from_directory(UPLOADS_DIR, filename)

@app.route('/api/image-preview')
def serve_image_preview():
    """Melayani gambar lokal dengan aman untuk ditampilkan di chat preview."""
    file_path = request.args.get('path', '')
    if file_path and os.path.exists(file_path):
        ext = os.path.splitext(file_path)[1].lower()
        if ext in ('.png', '.jpg', '.jpeg', '.webp', '.gif', '.svg'):
            return send_file(file_path)
    return jsonify({'error': 'Image not found'}), 404

def get_latest_conversation_id():
    """Mengembalikan conversation_id terbaru dari direktori brain."""
    if not os.path.exists(BRAIN_DIR):
        return None
    try:
        dirs = [os.path.join(BRAIN_DIR, d) for d in os.listdir(BRAIN_DIR) if os.path.isdir(os.path.join(BRAIN_DIR, d))]
        if not dirs:
            return None
        dirs.sort(key=os.path.getmtime, reverse=True)
        return os.path.basename(dirs[0])
    except Exception:
        return None

def sync_brain_conversations(conn):
    """Memindai folder brain dan menyelaraskan percakapan yang belum tercatat di conversation_summaries.db."""
    if not os.path.exists(BRAIN_DIR):
        return
    try:
        cur = conn.cursor()
        known = set(r[0] for r in cur.execute("SELECT conversation_id FROM conversation_summaries").fetchall())
        brains = [d for d in os.listdir(BRAIN_DIR) if os.path.isdir(os.path.join(BRAIN_DIR, d))]
        
        for cid in brains:
            tpath = os.path.join(BRAIN_DIR, cid, ".system_generated", "logs", "transcript.jsonl")
            if os.path.exists(tpath):
                mtime = os.path.getmtime(tpath)
                dt_iso = datetime.fromtimestamp(mtime, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S.000000+00:00")
                
                title = ""
                preview = ""
                steps = 0
                with open(tpath, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        if not line.strip(): continue
                        steps += 1
                        try:
                            d = json.loads(line)
                            if d.get("type") == "USER_INPUT" and not preview:
                                raw = d.get("content", "")
                                m = re.search(r"<USER_REQUEST>(.*?)</USER_REQUEST>", raw, re.DOTALL)
                                preview = (m.group(1).strip() if m else raw.strip())[:100]
                                title = preview[:40]
                        except Exception:
                            pass
                if preview:
                    cur.execute("""
                        INSERT OR REPLACE INTO conversation_summaries
                        (conversation_id, title, preview, step_count, last_modified_time, workspace_uris, project_id, last_user_input_time, last_user_input_step_index, app_data_dir)
                        VALUES (?, ?, ?, ?, ?, ?, 'default-cli-project', ?, 0, 'antigravity-cli')
                    """, (cid, title, preview, steps, dt_iso, '["file:///C:/Users/PRIMA"]', dt_iso))
        conn.commit()
    except Exception as e:
        print(f"Sync brain error: {e}")

@app.route('/api/conversations', methods=['GET'])
def get_conversations():
    """Mengambil daftar riwayat percakapan dari AGY CLI SQLite database."""
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': True, 'conversations': []})
    
    try:
        sync_brain_conversations(conn)
        cur = conn.cursor()
        query = """
            SELECT conversation_id, title, preview, step_count, last_modified_time, workspace_uris, project_id 
            FROM conversation_summaries 
            ORDER BY last_modified_time DESC 
            LIMIT 150
        """
        rows = cur.execute(query).fetchall()
        
        conversations = []
        for r in rows:
            cid = r['conversation_id']
            title = r['title'] or r['preview'] or "Percakapan Tanpa Judul"
            time_label, group_label = format_relative_time(r['last_modified_time'])
            
            conversations.append({
                'id': cid,
                'title': title,
                'preview': r['preview'] or '',
                'stepCount': r['step_count'] or 0,
                'lastModified': r['last_modified_time'],
                'timeLabel': time_label,
                'groupLabel': group_label,
                'workspace': r['workspace_uris'] or ''
            })
            
        conn.close()
        return jsonify({'success': True, 'conversations': conversations})
    except Exception as e:
        if conn: conn.close()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/conversations/<cid>/messages', methods=['GET'])
def get_conversation_messages(cid):
    """Mengekstrak seluruh pesan percakapan dari transcript.jsonl AGY."""
    tpath = os.path.join(BRAIN_DIR, cid, ".system_generated", "logs", "transcript.jsonl")
    if not os.path.exists(tpath):
        return jsonify({'success': True, 'messages': []})
    
    messages = []
    try:
        with open(tpath, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if not line.strip(): continue
                d = json.loads(line)
                stype = d.get("type")
                
                if stype == "USER_INPUT":
                    raw = d.get("content", "")
                    m = re.search(r"<USER_REQUEST>(.*?)</USER_REQUEST>", raw, re.DOTALL)
                    text = m.group(1).strip() if m else raw.strip()
                    
                    # Deteksi lampiran gambar
                    img_matches = re.findall(r"-\s*([A-Za-z]:/[^ \r\n]+\.(?:png|jpg|jpeg|webp))", raw, re.IGNORECASE)
                    
                    messages.append({
                        'role': 'user',
                        'text': text,
                        'images': img_matches,
                        'timestamp': d.get("created_at")
                    })
                    
                elif stype == "PLANNER_RESPONSE":
                    content = d.get("content", "")
                    thinking = d.get("thinking", "")
                    tools = []
                    for tc in d.get("tool_calls", []):
                        if isinstance(tc, dict):
                            func = tc.get("function", {})
                            name = func.get("name") or tc.get("name", "tool")
                            tools.append({
                                'name': name,
                                'summary': tc.get("toolSummary") or func.get("name") or name
                            })
                            
                    if content or thinking or tools:
                        messages.append({
                            'role': 'assistant',
                            'text': content,
                            'thinking': thinking,
                            'tools': tools,
                            'timestamp': d.get("created_at")
                        })
                        
        return jsonify({'success': True, 'messages': messages, 'conversationId': cid})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/accounts', methods=['GET'])
def get_accounts():
    """Mengambil daftar akun Google dan status aktif."""
    try:
        meta = agy_account.load_metadata()
        accs = []
        for a in meta.get('accounts', []):
            path = os.path.join(agy_account.PROFILES_DIR, f"{a}.dat")
            accs.append({
                'name': a,
                'active': (a == meta.get('active', '')),
                'ready': os.path.exists(path)
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
    """Berpindah ke profil akun Google tertentu."""
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
    """Menambah akun Google baru via browser auth."""
    data = request.get_json() or {}
    name = data.get('name', f"akun_{int(time.time())}")
    
    def run_add():
        agy_account.add_new_account(name)
        
    threading.Thread(target=run_add, daemon=True).start()
    return jsonify({'success': True, 'message': f'Login browser akun {name} telah dipicu.'})

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Menangani upload gambar dari file picker, drag-and-drop, atau Ctrl+V paste."""
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
                        'absolutePath': dest_path.replace('\\', '/'),
                        'url': f"/uploads/{safe_name}"
                    })
                    
        # 2. Dari Base64 Data URL (Clipboard Paste)
        json_data = request.get_json(silent=True)
        if json_data and 'base64Data' in json_data:
            b64_str = json_data['base64Data']
            if ',' in b64_str:
                _, b64_str = b64_str.split(',', 1)
                
            img_bytes = base64.b64decode(b64_str)
            safe_name = f"clipboard_{int(time.time())}_{uuid.uuid4().hex[:6]}.png"
            dest_path = os.path.join(UPLOADS_DIR, safe_name)
            with open(dest_path, 'wb') as f:
                f.write(img_bytes)
                
            uploaded_files.append({
                'fileName': 'Screenshot.png',
                'savedName': safe_name,
                'absolutePath': dest_path.replace('\\', '/'),
                'url': f"/uploads/{safe_name}"
            })
            
        return jsonify({'success': True, 'files': uploaded_files})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/chat', methods=['POST'])
def chat_stream():
    """Streaming interaksi AGY dengan auto-fallback Google account dan multimodal attachment."""
    global current_process
    
    data = request.get_json() or {}
    prompt = data.get('prompt', '').strip()
    model = data.get('model', 'gemini-3.8-flash-high')
    cwd = data.get('cwd', r"C:\Users\PRIMA")
    conversation_id = data.get('conversationId')
    images = data.get('images', [])
    
    if not prompt and not images:
        return jsonify({'error': 'Prompt atau gambar diperlukan'}), 400
        
    # Susun instruksi multimodal
    if images:
        image_instructions = "\n\n[LAMPIRAN GAMBAR/FOTO DARI USER]:\n"
        for idx, img_path in enumerate(images, 1):
            image_instructions += f"{idx}. File Path: {img_path}\n"
        image_instructions += "Instruksi: Analisis dan periksa gambar di atas untuk merespons permintaan user."
        full_prompt = prompt + image_instructions
    else:
        full_prompt = prompt

    def generate():
        global current_process
        
        target_prompt = full_prompt
        active_cid = conversation_id
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            retry_count += 1
            meta = agy_account.load_metadata()
            active_acc = meta.get('active', 'default')
            
            yield f"data: {json.dumps({'type': 'status', 'account': active_acc, 'model': model, 'conversationId': active_cid})}\n\n"
            
            cmd = [agy_account.AGY_EXE]
            if active_cid:
                cmd.extend(["--conversation", active_cid])
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
                    yield f"data: {json.dumps({'type': 'fallback', 'message': f'Kuota Akun [{active_acc}] habis. Otomatis beralih ke Akun [{next_acc}]...'})}\n\n"
                    agy_account.switch_profile(next_acc, silent=True)
                    time.sleep(1)
                    continue
                else:
                    yield f"data: {json.dumps({'type': 'error', 'message': 'Semua akun Google terdaftar telah mencapai batas kuota.'})}\n\n"
                    break
        # Deteksi conversation_id terbaru jika tadi None
        final_cid = active_cid
        if not final_cid:
            final_cid = get_latest_conversation_id()
            
        if final_cid:
            try:
                conn = get_db_connection()
                if conn:
                    sync_brain_conversations(conn)
                    conn.close()
            except Exception:
                pass

        yield f"data: {json.dumps({'type': 'done', 'conversationId': final_cid})}\n\n"

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
    print(f" [*] Summaries DB   : {SUMMARIES_DB}")
    print(f" [*] Multi-Account  : Aktif (Auto-Fallback Ready)")
    print(f" [*] Image Vision   : Aktif (Paste Ctrl+V & Drag-Drop)")
    print(f"-------------------------------------------------------\n")
    app.run(host='127.0.0.1', port=port, debug=False, threaded=True)

if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 4567
    run_server(port)
