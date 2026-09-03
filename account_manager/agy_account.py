#!/usr/bin/env python3
"""
Antigravity CLI (AGY) Google Account Auto-Fallback & Multi-Account Manager
Mengelola multi-akun Google untuk Antigravity CLI dengan automatic fallback saat kuota habis.
"""

import sys
import os
import ctypes
import json
import subprocess
import time
from ctypes import wintypes

USER_HOME = os.environ.get("USERPROFILE") or os.path.expanduser("~")
LOCAL_APP_DATA = os.environ.get("LOCALAPPDATA") or os.path.join(USER_HOME, "AppData", "Local")

PROFILES_DIR = os.path.join(USER_HOME, ".gemini", "account_profiles")
META_FILE = os.path.join(PROFILES_DIR, "metadata.json")
AGY_EXE = os.path.join(LOCAL_APP_DATA, "agy", "bin", "agy.exe")
if not os.path.exists(AGY_EXE):
    import shutil
    found_agy = shutil.which("agy.exe") or shutil.which("agy")
    if found_agy:
        AGY_EXE = found_agy

QUOTA_ERROR_PATTERNS = [
    "individual quota reached",
    "quota reached",
    "please upgrade your subscription",
    "rate limit exceeded",
    "resource has been exhausted",
    "429 too many requests",
]

# Windows Advapi32 Credential Structures
advapi32 = ctypes.windll.advapi32

class CREDENTIAL(ctypes.Structure):
    _fields_ = [
        ('Flags', wintypes.DWORD),
        ('Type', wintypes.DWORD),
        ('TargetName', wintypes.LPWSTR),
        ('Comment', wintypes.LPWSTR),
        ('LastWritten', wintypes.FILETIME),
        ('CredentialBlobSize', wintypes.DWORD),
        ('CredentialBlob', ctypes.POINTER(ctypes.c_char)),
        ('Persist', wintypes.DWORD),
        ('AttributeCount', wintypes.DWORD),
        ('Attributes', ctypes.c_void_p),
        ('TargetAlias', wintypes.LPWSTR),
        ('UserName', wintypes.LPWSTR),
    ]

def get_current_credential_blob():
    """Membaca blob autentikasi aktif gemini:antigravity dari Windows Credential Manager."""
    cred_ptr = ctypes.POINTER(CREDENTIAL)()
    res = advapi32.CredReadW('gemini:antigravity', 1, 0, ctypes.byref(cred_ptr))
    if not res:
        return None
    c = cred_ptr.contents
    raw = ctypes.string_at(c.CredentialBlob, c.CredentialBlobSize)
    advapi32.CredFree(cred_ptr)
    return raw

def set_credential_blob(blob_bytes):
    """Menulis blob autentikasi ke target gemini:antigravity di Windows Credential Manager."""
    new_cred = CREDENTIAL()
    new_cred.Flags = 0
    new_cred.Type = 1 # CRED_TYPE_GENERIC
    new_cred.TargetName = 'gemini:antigravity'
    new_cred.Comment = None
    new_cred.CredentialBlobSize = len(blob_bytes)
    new_cred.CredentialBlob = ctypes.cast(ctypes.create_string_buffer(blob_bytes), ctypes.POINTER(ctypes.c_char))
    new_cred.Persist = 2 # CRED_PERSIST_LOCAL_MACHINE
    new_cred.AttributeCount = 0
    new_cred.Attributes = None
    new_cred.TargetAlias = None
    new_cred.UserName = 'antigravity'
    
    res = advapi32.CredWriteW(ctypes.byref(new_cred), 0)
    return bool(res)

def delete_current_credential():
    """Menghapus target gemini:antigravity agar AGY memicu login browser baru."""
    res = advapi32.CredDeleteW('gemini:antigravity', 1, 0)
    return bool(res)

def load_metadata():
    os.makedirs(PROFILES_DIR, exist_ok=True)
    if os.path.exists(META_FILE):
        try:
            with open(META_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {'active': '', 'accounts': []}

def save_metadata(meta):
    os.makedirs(PROFILES_DIR, exist_ok=True)
    with open(META_FILE, 'w', encoding='utf-8') as f:
        json.dump(meta, f, indent=2)

def save_profile(name):
    """Menyimpan sesi login Google saat ini sebagai profile."""
    blob = get_current_credential_blob()
    if not blob:
        print("[!] Error: Tidak ditemukan credential aktif 'gemini:antigravity'. Silakan login di AGY terlebih dahulu.")
        return False
    
    path = os.path.join(PROFILES_DIR, f"{name}.dat")
    with open(path, 'wb') as f:
        f.write(blob)
    
    meta = load_metadata()
    if name not in meta['accounts']:
        meta['accounts'].append(name)
    meta['active'] = name
    save_metadata(meta)
    
    print(f"[OK] Akun Google '{name}' berhasil disimpan ({len(blob)} bytes).")
    print(f"[*] Akun aktif saat ini: {name}")
    return True

def switch_profile(name, silent=False):
    """Berpindah ke profile Google tertentu."""
    path = os.path.join(PROFILES_DIR, f"{name}.dat")
    if not os.path.exists(path):
        if not silent:
            print(f"[!] Error: Profile akun '{name}' tidak ditemukan di {path}")
        return False
    
    with open(path, 'rb') as f:
        blob = f.read()
    
    if set_credential_blob(blob):
        meta = load_metadata()
        meta['active'] = name
        save_metadata(meta)
        if not silent:
            print(f"[OK] Berhasil beralih ke Akun Google: {name}")
        return True
    else:
        if not silent:
            print(f"[!] Gagal menulis credential untuk {name} ke Windows Credential Manager.")
        return False

def get_next_profile():
    """Mengambil nama akun berikutnya dalam rotasi."""
    meta = load_metadata()
    accs = meta.get('accounts', [])
    if not accs:
        return None
    active = meta.get('active', '')
    if active in accs:
        idx = accs.index(active)
        next_idx = (idx + 1) % len(accs)
        return accs[next_idx]
    return accs[0]

def list_profiles():
    """Menampilkan daftar semua akun Google yang tersimpan."""
    meta = load_metadata()
    accs = meta.get('accounts', [])
    active = meta.get('active', '')
    
    current_blob = get_current_credential_blob()
    
    print("\n=======================================================")
    print("      ANTIGRAVITY CLI (AGY) GOOGLE ACCOUNTS LIST       ")
    print("=======================================================")
    if not accs:
        print(" Belum ada profil akun tersimpan.")
        print(" Gunakan: agy-account save <nama_akun> untuk menyimpan akun saat ini.")
    else:
        for acc in accs:
            path = os.path.join(PROFILES_DIR, f"{acc}.dat")
            exists = os.path.exists(path)
            is_active = (acc == active)
            
            # Verifikasi kecocokan byte dengan credential di memory
            in_sync = False
            if exists and current_blob:
                try:
                    with open(path, 'rb') as f:
                        saved_bytes = f.read()
                    in_sync = (saved_bytes == current_blob)
                except Exception:
                    pass
            
            status_tag = ""
            if is_active or in_sync:
                status_tag = " [SEDANG AKTIF]"
            
            health = "READY" if exists else "FILE MISSING"
            print(f" * {acc.ljust(18)} : {health}{status_tag}")
            
    print("-------------------------------------------------------\n")

def add_new_account(new_name):
    """Panduan interaktif untuk menambah akun Google baru ke AGY."""
    meta = load_metadata()
    current_active = meta.get('active')
    
    # Simpan akun saat ini jika belum ada nama
    current_blob = get_current_credential_blob()
    if current_blob:
        if not current_active:
            current_active = "akun1"
        save_profile(current_active)
        print(f"[*] Akun sebelumnya telah diamankan sebagai: '{current_active}'")
    
    print(f"\n[+] Memulai pendaftaran Akun Google baru: '{new_name}'")
    print("[*] Menghapus sesi lama sementara agar browser membuka form login...")
    delete_current_credential()
    
    print("\n[!] Buka AGY sekarang dan selesaikan login Google di browser.")
    print("    Menjalankan: agy...")
    
    try:
        subprocess.run([AGY_EXE, "-p", "Jawab singkat: Login Berhasil"], check=False)
    except Exception as e:
        print(f"[!] Gagal menjalankan agy: {e}")
        return False
    
    # Periksa apakah credential baru telah tertulis
    time.sleep(1)
    new_blob = get_current_credential_blob()
    if new_blob and new_blob != current_blob:
        save_profile(new_name)
        print(f"\n[SUKSES] Akun Google baru '{new_name}' berhasil didaftarkan dan aktif!")
        return True
    else:
        print("\n[!] Peringatan: Belum mendeteksi login baru. Jika Anda sudah login di browser, jalankan:")
        print(f"    agy-account save {new_name}")
        return False

def run_fallback(resume_session=True):
    """Beralih ke akun Google berikutnya dan lanjutkan sesi."""
    next_acc = get_next_profile()
    meta = load_metadata()
    current_acc = meta.get('active', 'unknown')
    
    if not next_acc or next_acc == current_acc:
        print(f"[!] Hanya ada 1 akun ({current_acc}) tersimpan. Daftarkan akun kedua dengan: agy-account add <nama_akun_kedua>")
        return False
    
    print(f"\n[AUTO-FALLBACK] Beralih akun Google: [{current_acc}] -> [{next_acc}]...")
    if switch_profile(next_acc):
        if resume_session:
            print(f"[AUTO-FALLBACK] Melanjutkan sesi sebelumnya dengan Akun: {next_acc}...\n")
            cmd = [AGY_EXE, "-c"]
            subprocess.run(cmd)
        return True
    return False

def run_command_with_auto_fallback(cmd_args):
    """Menjalankan perintah AGY dengan perlindungan fallback akun otomatis jika kuota habis."""
    meta = load_metadata()
    accs = meta.get('accounts', [])
    if not accs:
        # Jalankan biasa jika belum ada profil tersimpan
        return subprocess.run([AGY_EXE] + cmd_args).returncode

    attempts = 0
    max_attempts = max(2, len(accs))
    target_args = list(cmd_args)

    while attempts < max_attempts:
        attempts += 1
        current_acc = load_metadata().get('active', 'default')
        print(f"\n[AGY-ACCOUNT] [Percobaan {attempts}] Menggunakan Akun Google: {current_acc}")

        proc = subprocess.Popen(
            [AGY_EXE] + target_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace'
        )

        full_output = []
        is_quota_error = False

        while True:
            line = proc.stdout.readline()
            if not line and proc.poll() is not None:
                break
            if line:
                print(line, end='', flush=True)
                full_output.append(line)
                lower_line = line.lower()
                for pattern in QUOTA_ERROR_PATTERNS:
                    if pattern in lower_line:
                        is_quota_error = True

        proc.wait()

        if is_quota_error:
            print(f"\n[!] KUOTA HABIS pada Akun Google: {current_acc}")
            next_acc = get_next_profile()
            if next_acc and next_acc != current_acc:
                print(f"[*] AUTO-FALLBACK: Beralih otomatis ke Akun Google: {next_acc}...")
                switch_profile(next_acc, silent=True)
                # Tambahkan flag continue agar tugas tersambung
                if "-c" not in target_args and "--continue" not in target_args:
                    target_args = ["-c"] + target_args
                time.sleep(1)
                continue
            else:
                print("[!] Semua akun Google yang terdaftar telah habis kuotanya.")
                return proc.returncode
        else:
            return proc.returncode

    return 0

# ----------------- CLI INTERFACE -----------------

def main():
    if len(sys.argv) < 2:
        print("""
Penggunaan agy-account:
  agy-account list              - Lihat semua profil akun Google yang tersimpan
  agy-account save <nama>       - Simpan akun Google yang sedang aktif saat ini
  agy-account switch <nama>     - Beralih ke profil akun Google tertentu
  agy-account add <nama>        - Tambah & login akun Google baru ke AGY
  agy-account fallback [-c]     - Beralih ke akun berikutnya (dan lanjutkan sesi)
  agy-account run <args...>     - Jalankan perintah AGY dengan auto-fallback akun
  agy-account -c                - Langsung beralih akun dan lanjutkan sesi terakhir
""")
        list_profiles()
        return

    cmd = sys.argv[1].lower()

    if cmd in ("list", "status", "ls"):
        list_profiles()
    elif cmd in ("save", "simpan"):
        if len(sys.argv) < 3:
            print("[!] Harap sertakan nama akun. Contoh: agy-account save akun1")
        else:
            save_profile(sys.argv[2])
    elif cmd in ("switch", "pindah", "use"):
        if len(sys.argv) < 3:
            print("[!] Harap sertakan nama akun tujuan. Contoh: agy-account switch akun2")
        else:
            switch_profile(sys.argv[2])
    elif cmd in ("add", "tambah", "new"):
        name = sys.argv[2] if len(sys.argv) >= 3 else f"akun{len(load_metadata().get('accounts', [])) + 1}"
        add_new_account(name)
    elif cmd in ("fallback", "next"):
        resume = ("-c" in sys.argv or "--continue" in sys.argv)
        run_fallback(resume_session=resume)
    elif cmd in ("-c", "--continue", "resume", "lanjut"):
        run_fallback(resume_session=True)
    elif cmd in ("run", "exec"):
        run_command_with_auto_fallback(sys.argv[2:])
    else:
        # Jika argumen diteruskan langsung ke AGY (misal: agy-account -p "...")
        run_command_with_auto_fallback(sys.argv[1:])

if __name__ == "__main__":
    main()
