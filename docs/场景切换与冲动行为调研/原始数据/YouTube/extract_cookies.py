"""Extract YouTube cookies from copied Chrome profile, decrypt, export Netscape format."""
import os, json, base64, sqlite3, shutil, sys
from pathlib import Path

try:
    import win32crypt
except ImportError:
    os.system(f'"{sys.executable}" -m pip install pywin32 -q')
    import win32crypt

try:
    from Crypto.Cipher import AES
except ImportError:
    os.system(f'"{sys.executable}" -m pip install pycryptodome -q')
    from Crypto.Cipher import AES

BASE = Path(r"D:\11.project\iwen-codex\codex-list\training-tracker-docker\docs\场景切换与冲动行为调研\原始数据\YouTube\_chrome_copy")
LOCAL_STATE = BASE / "Local State"
COOKIES_DB = BASE / "Default" / "Network" / "Cookies"
OUT = Path(r"D:\11.project\iwen-codex\codex-list\training-tracker-docker\docs\场景切换与冲动行为调研\原始数据\YouTube\cookies.txt")

# 1. Get encrypted master key from Local State
ls = json.loads(LOCAL_STATE.read_text(encoding="utf-8"))
encrypted_key_b64 = ls["os_crypt"]["encrypted_key"]
encrypted_key = base64.b64decode(encrypted_key_b64)
# Remove "DPAPI" prefix (5 bytes)
assert encrypted_key[:5] == b"DPAPI"
encrypted_key = encrypted_key[5:]
# DPAPI decrypt
master_key = win32crypt.CryptUnprotectData(encrypted_key, None, None, None, 0)[1]

def decrypt_cookie(enc_value: bytes) -> str:
    if not enc_value:
        return ""
    # v20+ starts with "v20" or "v10"
    prefix = enc_value[:3]
    if prefix in (b"v10", b"v20"):
        iv = enc_value[3:15]
        payload = enc_value[15:-16]
        tag = enc_value[-16:]
        cipher = AES.new(master_key, AES.MODE_GCM, nonce=iv)
        try:
            dec = cipher.decrypt_and_verify(payload, tag)
            return dec.decode("utf-8", errors="replace")
        except Exception as e:
            # Maybe v10 uses DPAPI directly
            try:
                return win32crypt.CryptUnprotectData(enc_value, None, None, None, 0)[1].decode("utf-8", errors="replace")
            except Exception:
                return ""
    else:
        # Older DPAPI-encrypted
        try:
            return win32crypt.CryptUnprotectData(enc_value, None, None, None, 0)[1].decode("utf-8", errors="replace")
        except Exception:
            return ""

# 2. Copy sqlite db to temp (avoid lock)
tmp_db = BASE / "cookies_copy.db"
shutil.copy(COOKIES_DB, tmp_db)

conn = sqlite3.connect(tmp_db)
cur = conn.cursor()
cur.execute("SELECT host_key, name, value, encrypted_value, path, expires_utc, is_secure FROM cookies")
rows = cur.fetchall()

# Filter YouTube cookies
yt_cookies = [r for r in rows if "youtube" in r[0] or "google" in r[0]]
print(f"Total cookies: {len(rows)}, YT/Google cookies: {len(yt_cookies)}")

# 3. Write Netscape cookies.txt
# Netscape format: domain  flag  path  secure  expiration  name  value
def chrome_exp_to_unix(chrome_exp):
    # Chrome time: microseconds since 1601-01-01
    if chrome_exp == 0:
        return 0
    unix = int(chrome_exp / 1_000_000 - 11644473600)
    return unix

with OUT.open("w", encoding="utf-8") as f:
    f.write("# Netscape HTTP Cookie File\n")
    for host, name, value, enc_value, path, exp, secure in yt_cookies:
        dec_value = value if value else decrypt_cookie(enc_value)
        flag = "TRUE" if host.startswith(".") else "FALSE"
        sec = "TRUE" if secure else "FALSE"
        exp_unix = chrome_exp_to_unix(exp)
        f.write(f"{host}\t{flag}\t{path}\t{sec}\t{exp_unix}\t{name}\t{dec_value}\n")

print(f"Wrote {OUT}")
# Show sample
with OUT.open() as f:
    for i, line in enumerate(f):
        if i < 15:
            print(line.rstrip())
