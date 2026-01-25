import requests
import pandas as pd
import time
import sys
import json
import re
import psutil
import pyotp
from login import login_with_sso, user_agents

version = "1.2.4"  # Auto Session Refresh
motd = 1

def generate_otp(secret_key):
    """Generate OTP menggunakan secret key"""
    totp = pyotp.TOTP(secret_key)
    return totp.now()

def check_vpn_connection():
    """
    Check apakah VPN (FortiClient) terkonek
    Returns: True jika terkonek, False jika tidak
    """
    # Check FortiClient/FortiSSLVPN process
    forticlient_running = False
    vpn_process_names = ['forticlient', 'fortisslvpn', 'fortivpn', 'openvpn']
    
    for proc in psutil.process_iter(['name']):
        try:
            proc_name = proc.info['name'].lower()
            for vpn_name in vpn_process_names:
                if vpn_name in proc_name:
                    forticlient_running = True
                    break
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
        if forticlient_running:
            break
    
    if not forticlient_running:
        return False
    
    # Check VPN IP address (BPS VPN menggunakan 10.x.x.x)
    for interface, addrs in psutil.net_if_addrs().items():
        for addr in addrs:
            if addr.family == 2:  # AF_INET (IPv4)
                # Check if IP is in private range yang biasa dipakai VPN BPS
                if addr.address.startswith('10.'):
                    return True
    
    return False

def check_vpn_or_exit():
    """
    Check VPN connection, exit script jika tidak terkonek
    """
    print("\n" + "="*70)
    print("🔒 Mengecek Koneksi VPN...")
    print("="*70)
    
    if check_vpn_connection():
        print("✅ VPN TERKONEK - Script dapat dilanjutkan")
        print("="*70 + "\n")
        return True
    else:
        print("\n" + "="*70)
        print("❌ VPN TIDAK TERKONEK!")
        print("\nScript memerlukan koneksi VPN untuk mengakses MatchaPro.")
        print("\nLangkah-langkah:")
        print("  1. Buka FortiClient VPN")
        print("  2. Connect ke VPN BPS")
        print("  3. Tunggu sampai status Connected")
        print("  4. Jalankan script ini lagi")
        print("="*70)
        sys.exit(1)

def wait_for_vpn_reconnect(max_wait_seconds=300, check_interval=5):
    """
    Tunggu VPN reconnect dengan countdown
    Args:
        max_wait_seconds: Maksimal waktu tunggu (default 5 menit)
        check_interval: Interval check dalam detik (default 5 detik)
    Returns:
        True jika VPN berhasil reconnect, False jika timeout
    """
    print("\n" + "="*70)
    print("⚠️  VPN TERPUTUS!")
    print("="*70)
    print(f"\nMenunggu VPN reconnect (maksimal {max_wait_seconds} detik)...")
    print("Silakan reconnect VPN secara manual atau tunggu auto-reconnect...\n")
    
    elapsed = 0
    while elapsed < max_wait_seconds:
        remaining = max_wait_seconds - elapsed
        print(f"\r⏳ Mengecek VPN... (sisa waktu: {remaining}s)   ", end='', flush=True)
        
        # Check VPN tanpa print verbose
        if check_vpn_connection():
            print("\n\n" + "="*70)
            print("✅ VPN BERHASIL RECONNECT!")
            print("="*70)
            print("Melanjutkan proses...\n")
            return True
        
        time.sleep(check_interval)
        elapsed += check_interval
    
    print("\n\n" + "="*70)
    print("❌ TIMEOUT - VPN tidak reconnect dalam waktu yang ditentukan")
    print("="*70)
    return False

def monitor_vpn_and_wait_if_disconnected():
    """
    Monitor VPN, jika terputus maka tunggu sampai reconnect
    Returns: True jika VPN aktif (atau berhasil reconnect), False jika gagal
    """
    if not check_vpn_connection():
        # VPN terputus, tunggu reconnect
        if wait_for_vpn_reconnect():
            return True
        else:
            print("\n❌ Script dihentikan karena VPN tidak dapat reconnect")
            return False
    return True

def extract_tokens(page):
    # Tunggu hingga tag meta token CSRF terpasang
    page.wait_for_selector('meta[name="csrf-token"]', state='attached', timeout=10000)

    # Ekstrak _token dari halaman (token CSRF dari tag meta)
    token_element = page.locator('meta[name="csrf-token"]')
    if token_element.count() > 0:
        _token = token_element.get_attribute('content')
    else:
        raise Exception("Gagal mengekstrak _token - tag meta tidak ditemukan")

    # Ekstrak gc_token dari konten halaman
    content = page.content()
    # Mencoba mencocokkan 'let gcSubmitToken' dengan kutip satu atau dua dan spasi fleksibel
    match = re.search(r"let\s+gcSubmitToken\s*=\s*(['\"])([^'\"]+)\1", content)
    if match:
        gc_token = match.group(2)
    else:
        # Analisa konten error
        if "Akses lewat matchapro mobile aja" in content or "Not Authorized" in content:
            print("\n" + "="*50)
            print("❌ ERROR FATAL: AKES DITOLAK SERVER")
            print("Penyebab: Laptop ini terdeteksi sebagai Desktop, bukan Mobile.")
            print("SOLUSI: Pastikan file 'login.py' di laptop ini SUDAH DIPERBARUI")
            print("        agar sama persis dengan yang ada di laptop utama.")
            print("="*50 + "\n")
        
        # Simpan konten halaman untuk debugging jika token tidak ditemukan
        try:
            with open("debug_page_content.html", "w", encoding="utf-8") as f:
                f.write(content)
            print("Gagal menemukan gc_token. Konten halaman telah disimpan ke debug_page_content.html")
        except Exception as e:
            print(f"Gagal menyimpan debug page: {e}")
            
        raise Exception("Token tidak ditemukan (Cek pesan error di atas)")
    
    return _token, gc_token

def main():
    # Check VPN connection terlebih dahulu
    check_vpn_or_exit()
    
    # Pengecekan versi
    try:
        response = requests.get("https://dev.ketut.web.id/ver.txt", timeout=10)
        if response.status_code == 200:
            remote_version = response.text.strip()
            if remote_version != version:
                print(f"Versi saat ini: {version}")
                print(f"Versi terbaru: {remote_version}")
                print("Gunakan versi terbaru. Silakan unduh dari:")
                print("https://github.com/ketut/SsscriptGC")
                time.sleep(5)
                sys.exit(1)
        else:
            print("Gagal mengambil versi terbaru. Melanjutkan...")
    except Exception as e:
        print(f"Gagal mengecek versi: {e}. Melanjutkan...")

    # Cek MOTD dan tampilkan pesan jika motd = 1
    try:
        motd_response = requests.get("https://dev.ketut.web.id/TGlrZWxpaG9vZA.txt", timeout=10)
        if motd_response.status_code == 200:
            motd_text = motd_response.text.strip()
            print(f"{motd_text}")  # Debug
            try:
                motd_data = motd_response.json()
                if motd_data.get("motd") == 1:
                    print(motd_data.get("message", ""))
            except:
                # Jika bukan JSON, asumsikan teks adalah motd
                if motd_text == "1":
                    print("Pesan MOTD aktif")  # Placeholder, ganti dengan pesan sebenarnya jika ada
    except Exception as e:
        print(f"[DEBUG] Gagal cek MOTD: {e}")

    if len(sys.argv) < 3:
        print("Usage: python tandaiKirim.py <username> <password> [secret_key untuk OTP] [nomor_baris]")
        sys.exit(1)

    username = sys.argv[1]
    password = sys.argv[2]
    secret_key = sys.argv[3] if len(sys.argv) > 3 else None  # Secret key untuk generate OTP
    nomor_baris = int(sys.argv[4]) if len(sys.argv) > 4 else None
    
    # Generate OTP jika ada secret_key
    otp_code = None
    if secret_key:
        otp_code = generate_otp(secret_key)
        print(f"[INFO] OTP Generated: {otp_code}")
    
    # Jika nomor_baris tidak diberikan, baca dari baris.txt
    if nomor_baris is None:
        try:
            with open('baris.txt', 'r') as f:
                nomor_baris = int(f.read().strip())
        except FileNotFoundError:
            nomor_baris = 0

    # Lakukan login dan dapatkan objek halaman
    page, browser = login_with_sso(username, password, otp_code)

    if page:
        try:
            # DEBUG: Cek identitas browser
            ua = page.evaluate("navigator.userAgent")
            print(f"\n[INFO] Browser User Agent: {ua}")
            if "Android" not in ua and "Mobile" not in ua:
                print("⚠️  WARNING: Script tidak berjalan dalam mode Mobile!")
                print("    Kemungkinan file 'login.py' belum diupdate di laptop ini.")
            else:
                print("[INFO] Mode Mobile aktif. Melanjutkan...\n")

            # Navigasi ke /dirgc
            url_gc = "https://matchapro.web.bps.go.id/dirgc"
            page.goto(url_gc)
            page.wait_for_load_state('networkidle')

            # Ekstrak tokens
            _token, gc_token = extract_tokens(page)
            print(f"Ekstrak _token: {_token}")
            print(f"gc_token: {gc_token}")

            # Dapatkan cookies
            cookies = page.context.cookies()
            session_cookies = {cookie['name']: cookie['value'] for cookie in cookies}

            url = "https://matchapro.web.bps.go.id/dirgc/konfirmasi-user"

            # Baca CSV
            encodings_to_try = ['utf-8', 'cp1252', 'latin1']
            df = None
            for enc in encodings_to_try:
                try:
                    df = pd.read_csv('data_gc_profiling_bahan_kirim.csv', encoding=enc)
                    print(f"Berhasil membaca dengan encoding: {enc}")
                    break
                except UnicodeDecodeError:
                    print(f"Gagal dengan encoding: {enc}, mencoba yang lain...")
                    continue
            if df is None:
                raise ValueError("Tidak bisa membaca file dengan encoding yang dicoba.")

            headers = {
                "host": "matchapro.web.bps.go.id",
                "connection": "keep-alive",
                "sec-ch-ua": "\"Android WebView\";v=\"143\", \"Chromium\";v=\"143\", \"Not A(Brand\";v=\"24\"",
                "sec-ch-ua-mobile": "?1",
                "sec-ch-ua-platform": "\"Android\"",
                "upgrade-insecure-requests": "1",
                "user-agent": user_agents,
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "x-requested-with": "com.matchapro.app",
                "sec-fetch-site": "same-origin",
                "sec-fetch-mode": "navigate",
                "sec-fetch-user": "?1",
                "sec-fetch-dest": "document",
                "referer": "https://matchapro.web.bps.go.id/",
                "accept-encoding": "gzip, deflate, br, zstd",
                "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
            }

            # Session refresh configuration
            request_count = 0
            total_processed = 0  # Counter untuk emergency refresh (429 error)
            SESSION_REFRESH_THRESHOLD = 1000  # Refresh session setiap 1000 request
            
            print(f"\n{'='*70}")
            print(f"🔄 AUTO SESSION REFRESH: Aktif setiap {SESSION_REFRESH_THRESHOLD} request")
            print(f"{'='*70}\n")

            # Loop untuk setiap baris mulai dari nomor_baris
            for index in range(nomor_baris, len(df)):
                # Check apakah perlu refresh session (normal atau karena 429 error)
                if (request_count > 0 and request_count % SESSION_REFRESH_THRESHOLD == 0) or total_processed == 999:
                    if total_processed == 999:
                        print("\n" + "="*70)
                        print(f"🚨 EMERGENCY SESSION REFRESH: Triggered by 429 error")
                        print("="*70)
                    else:
                        print("\n" + "="*70)
                        print(f"🔄 SESSION REFRESH: {request_count} request tercapai")
                        print("="*70)
                    
                    print("Re-login untuk mendapatkan session baru...")
                    
                    # Reset counters
                    total_processed = 0
                    request_count = 0  # Reset request counter untuk session baru
                    
                    try:
                        # Close browser lama
                        browser.close()
                        time.sleep(2)
                        
                        # Generate OTP baru untuk re-login (jika menggunakan OTP)
                        if secret_key:
                            otp_code = generate_otp(secret_key)
                            print(f"[INFO] OTP baru di-generate: {otp_code}")
                        
                        # Login ulang dengan credentials yang sama
                        print(f"Login ulang sebagai: {username}")
                        page, browser = login_with_sso(username, password, otp_code)
                        
                        if not page or not browser:
                            print("❌ Re-login gagal! Menghentikan script.")
                            sys.exit(1)
                        
                        # Navigasi ulang ke halaman GC
                        page.goto(url_gc)
                        page.wait_for_load_state('networkidle')
                        
                        # Ekstrak tokens baru
                        _token, gc_token = extract_tokens(page)
                        print(f"✅ Session baru berhasil!")
                        print(f"   New _token: {_token}")
                        print(f"   New gc_token: {gc_token}")
                        print("="*70 + "\n")
                        
                        # Tunggu sebentar sebelum melanjutkan
                        time.sleep(3)
                        
                    except Exception as refresh_error:
                        print(f"❌ Error saat refresh session: {refresh_error}")
                        print("Mencoba melanjutkan dengan session lama...")
                
                row = df.iloc[index]
                perusahaan_id = row['perusahaan_id']
                latitude = row['latitude']
                longitude = row['longitude']
                hasilgc = row['hasilgc']
                
                # Pengecekan hasilgc
                if hasilgc is None or str(hasilgc).strip() == '' or hasilgc not in [99, 1, 3, 4]:
                    print(f"Pemberitahuan: hasilgc untuk baris {index} kosong atau tidak valid ({hasilgc}). Nilai yang diperbolehkan: 99, 1, 3, atau 4.")
                    choice = input("Apakah Anda ingin berhenti (y) atau lanjut ke baris berikutnya (n)? ").strip().lower()
                    if choice == 'y':
                        print("Proses dihentikan.")
                        sys.exit(0)
                    elif choice == 'n':
                        print("Melanjutkan ke baris berikutnya.")
                        continue
                    else:
                        print("Input tidak valid. Melanjutkan ke baris berikutnya.")
                        continue
                
                # Pengecekan tambahan: jika hasilgc = 1, latitude dan longitude harus ada
                if hasilgc == 1:
                    if pd.isna(latitude) or str(latitude).strip() == '' or pd.isna(longitude) or str(longitude).strip() == '':
                        print(f"Pemberitahuan: Untuk hasilgc=1 pada baris {index}, latitude dan longitude harus diisi. Latitude: {latitude}, Longitude: {longitude}.")
                        choice = input("Apakah Anda ingin berhenti (y) atau lanjut ke baris berikutnya (n)? ").strip().lower()
                        if choice == 'y':
                            print("Proses dihentikan.")
                            sys.exit(0)
                        elif choice == 'n':
                            print("Melanjutkan ke baris berikutnya.")
                            continue
                        else:
                            print("Input tidak valid. Melanjutkan ke baris berikutnya.")
                            continue
                
                # Gunakan Playwright API Request untuk mengirim data (lebih aman dari blokir)
                max_request_retries = 5
                request_success = False
                
                for request_attempt in range(max_request_retries):
                    try:
                        # Randomize time_on_page untuk lebih natural (5-15 detik)
                        import random
                        time_on_page = random.randint(16, 32)
                        
                        form_data = {
                            "perusahaan_id": str(perusahaan_id),
                            "latitude": str(latitude),
                            "longitude": str(longitude),
                            "hasilgc": str(hasilgc),
                            "gc_token": gc_token,
                            "edit_nama": "0",  # Tambahan parameter dari payload asli
                            "edit_alamat": "0",  # Tambahan parameter dari payload asli
                            "nama_usaha": "",  # Kosong jika tidak edit
                            "alamat_usaha": "",  # Kosong jika tidak edit
                            "time_on_page": str(time_on_page),  # Randomize untuk simulasi user behavior
                            "_token": _token
                        }
                        
                        # Headers tambahan spesifik untuk POST ini - matching HTTP Toolkit
                        post_headers = {
                            "accept": "*/*",
                            "accept-encoding": "gzip, deflate, br, zstd",
                            "accept-language": "en-US,en;q=0.9",
                            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
                            "origin": "https://matchapro.web.bps.go.id",
                            "referer": "https://matchapro.web.bps.go.id/dirgc",
                            "sec-ch-ua": '"Android WebView";v="143", "Chromium";v="143"',
                            "sec-ch-ua-mobile": "?1",
                            "sec-ch-ua-platform": '"Android"',
                            "sec-fetch-dest": "empty",
                            "sec-fetch-mode": "cors",
                            "sec-fetch-site": "same-origin",
                            "x-requested-with": "XMLHttpRequest"
                        }

                        # Kirim request menggunakan context browser (cookies & session otomatis terpakai)
                        response = page.request.post(url, form=form_data, headers=post_headers, timeout=30000)
                        
                        status_code = response.status
                        response_text = response.text()
                        
                        # Handle 429 Too Many Requests
                        if status_code == 429:
                            try:
                                # Try to parse JSON response
                                try:
                                    resp_json = response.json()
                                    message = resp_json.get('message', 'Terlalu banyak permintaan.')
                                    retry_after = resp_json.get('retry_after', 120)  # default 2 menit saja
                                except (json.JSONDecodeError, ValueError):
                                    # Response bukan JSON, gunakan default
                                    message = 'Terlalu banyak permintaan (Rate Limit).'
                                    retry_after = 120  # 2 menit saja, cukup untuk session refresh
                                    print(f"⚠️  429 response bukan JSON, menggunakan default wait time")
                                
                                print("\n" + "="*50)
                                print(f"❌ STATUS 429: {message}")
                                print("="*50)
                                
                                # Parse waktu dari message jika ada (contoh: "10 menit")
                                wait_time_seconds = retry_after
                                
                                # Coba ekstrak waktu dari message
                                import re
                                time_match = re.search(r'(\d+)\s*(menit|detik|jam)', message.lower())
                                if time_match:
                                    time_value = int(time_match.group(1))
                                    time_unit = time_match.group(2)
                                    
                                    if time_unit == 'menit':
                                        wait_time_seconds = time_value * 60
                                    elif time_unit == 'detik':
                                        wait_time_seconds = time_value
                                    elif time_unit == 'jam':
                                        wait_time_seconds = time_value * 3600
                                
                                # Jangan tambahkan buffer lagi, langsung pakai nilai retry_after
                                # (sudah cukup konservatif di 2 menit)
                                
                                print(f"💡 Akan melakukan session refresh untuk reset rate limit...")
                                print(f"   Menutup browser dan akan login ulang...")
                                
                                # Tutup browser untuk trigger session refresh
                                try:
                                    if page:
                                        page.close()
                                    if browser:
                                        browser.close()
                                except:
                                    pass
                                
                                # Reset counter untuk force session refresh di iterasi berikutnya
                                total_processed = 999
                                
                                print(f"✅ Browser ditutup. Session akan di-refresh LANGSUNG pada iterasi berikutnya.")
                                print(f"🚀 Tidak menunggu, langsung buka session baru...")
                                print("="*50 + "\n")
                                
                                # Set flag untuk skip baris ini dan force session refresh
                                request_success = False
                                break  # Keluar dari retry loop
                            except Exception as e:
                                print(f"⚠️  Error processing 429 response: {e}")
                                print(f"💡 Tetap melakukan session refresh meskipun ada error...")
                                
                                # Tutup browser untuk trigger session refresh
                                try:
                                    if page:
                                        page.close()
                                    if browser:
                                        browser.close()
                                except:
                                    pass
                                
                                # Reset counter untuk force session refresh
                                total_processed = 999
                                
                                print(f"✅ Browser ditutup. Session akan di-refresh LANGSUNG pada iterasi berikutnya.")
                                print(f"🚀 Tidak menunggu, langsung buka session baru...")
                                
                                # Set flag untuk skip baris ini dan force session refresh
                                request_success = False
                                break  # Keluar dari retry loop
                        
                        # Handle 419 CSRF Token Mismatch
                        if status_code == 419:
                            try:
                                resp_json = response.json()
                                message = resp_json.get('message', '')
                                if 'CSRF token mismatch' in message:
                                    print("\n" + "="*50)
                                    print(f"❌ STATUS 419: {message}")
                                    print("="*50)
                                    print(f"💡 CSRF token mismatch terdeteksi. Melakukan session refresh dan retry baris ini...")
                                    
                                    # Lakukan session refresh langsung di sini
                                    print("Re-login untuk mendapatkan session baru...")
                                    
                                    # Reset counters
                                    total_processed = 0
                                    request_count = 0  # Reset request counter untuk session baru
                                    
                                    try:
                                        # Close browser lama
                                        browser.close()
                                        time.sleep(2)
                                        
                                        # Generate OTP baru untuk re-login (jika menggunakan OTP)
                                        if secret_key:
                                            otp_code = generate_otp(secret_key)
                                            print(f"[INFO] OTP baru di-generate: {otp_code}")
                                        
                                        # Login ulang dengan credentials yang sama
                                        print(f"Login ulang sebagai: {username}")
                                        page, browser = login_with_sso(username, password, otp_code)
                                        
                                        if not page or not browser:
                                            print("❌ Re-login gagal! Menghentikan script.")
                                            sys.exit(1)
                                        
                                        # Navigasi ulang ke halaman GC
                                        page.goto(url_gc)
                                        page.wait_for_load_state('networkidle')
                                        
                                        # Ekstrak tokens baru
                                        _token, gc_token = extract_tokens(page)
                                        print(f"✅ Session baru berhasil!")
                                        print(f"   New _token: {_token}")
                                        print(f"   New gc_token: {gc_token}")
                                        print("="*50 + "\n")
                                        
                                        # Tunggu sebentar sebelum retry
                                        time.sleep(3)
                                        
                                        # Retry request dengan session baru (continue loop)
                                        continue
                                        
                                    except Exception as refresh_error:
                                        print(f"❌ Error saat refresh session: {refresh_error}")
                                        print("Melanjutkan dengan session lama...")
                                        continue
                            except Exception as e:
                                print(f"⚠️  Error processing 419 response: {e}")
                                print(f"💡 Tetap mencoba melanjutkan...")
                                continue
                        
                        # Check if it's an error that needs retry on the same row
                        is_retryable_error = False
                        if status_code == 400:
                            try:
                                resp_json = response.json()
                                message = resp_json.get('message', '')
                                if (resp_json.get('status') == 'error' and 
                                    'Token invalid atau sudah terpakai. Silakan refresh halaman.' in message):
                                    is_retryable_error = True
                            except Exception:
                                pass
                        elif status_code == 503:
                            try:
                                resp_json = response.json()
                                message = resp_json.get('message', '')
                                if (resp_json.get('status') == 'error' and 
                                    'Server sedang sibuk. Silakan coba lagi dalam beberapa detik.' in message):
                                    is_retryable_error = True
                            except Exception:
                                pass
                        
                        if is_retryable_error:
                            if request_attempt < max_request_retries - 1:
                                print(f"Token invalid error for row {index} (attempt {request_attempt + 1}/{max_request_retries}). Refreshing tokens...")
                                # Refresh tokens
                                try:
                                    page.reload()
                                    page.wait_for_load_state('networkidle')
                                    _token, gc_token = extract_tokens(page)
                                    print(f"Refreshed _token: {_token}")
                                    print(f"Refreshed gc_token: {gc_token}")
                                    time.sleep(5)  # Brief pause before retry
                                    continue  # Retry the request with new tokens
                                except Exception as token_refresh_error:
                                    print(f"Failed to refresh tokens: {token_refresh_error}")
                                    if request_attempt < max_request_retries - 1:
                                        print("Retrying request without token refresh...")
                                        time.sleep(5)
                                        continue
                                    else:
                                        print(f"Max retries reached for row {index} after token refresh failure")
                                        break
                            else:
                                print(f"Token invalid error for row {index}: max retries reached")
                                break
                        else:
                            # Success or other error - exit retry loop
                            print(f"Row {index}: {status_code} - {response_text}")
                            request_success = True
                            break
                        
                    except Exception as e:
                        error_message = str(e).lower()
                        if "timeout 30000ms exceeded" in error_message:
                            print(f"Error processing 429 response: {e}")
                            print("Menunggu 10 menit sebagai fallback...")
                            time.sleep(600)  # 10 menit
                            continue
                        
                        # Check VPN jika ada network error
                        is_retryable_error = (
                            "timed out" in error_message or 
                            "timeout" in error_message or
                            "econnreset" in error_message or
                            "connection reset" in error_message or
                            "connection refused" in error_message or
                            "connection aborted" in error_message or
                            "network" in error_message or
                            "socket" in error_message
                        )
                        
                        if is_retryable_error:
                            print(f"\n⚠️  Network error terdeteksi: {e}")
                            print("🔍 Checking VPN connection...")
                            if not monitor_vpn_and_wait_if_disconnected():
                                print("\n❌ VPN terputus dan tidak dapat reconnect. Script dihentikan.")
                                break
                        
                        if is_retryable_error:
                            if request_attempt < max_request_retries - 1:
                                print(f"Connection error untuk row {index} (attempt {request_attempt + 1}/{max_request_retries}): {e}. Retrying in 5 seconds...")
                                time.sleep(5)
                                continue
                            else:
                                print(f"Error during request logging for row {index}: {e} (max retries reached)")
                        else:
                            # Error lain yang tidak bisa di-retry, langsung log dan lanjut
                            print(f"Error during request logging for row {index}: {e}")
                            break
                
                # Jika browser sudah ditutup karena 429, skip processing dan lanjut ke iterasi berikutnya
                # (yang akan trigger session refresh karena total_processed = 999)
                if total_processed == 999:
                    print(f"⏭️  Skipping baris {index}, akan retry setelah session refresh...")
                    continue
                
                # Jika request berhasil, lanjutkan dengan pemrosesan response
                if request_success:
                    # Increment request counter untuk session refresh
                    request_count += 1
                    
                    # Catat baris terakhir
                    try:
                        with open('baris.txt', 'w') as f:
                            f.write(str(index))
                    except PermissionError:
                        print(f"Warning: Tidak bisa menulis ke baris.txt untuk baris {index}")
                    
                    # Update gc_token if present (for successful responses)
                    if status_code == 200:
                        try:
                            resp_json = response.json()
                            if 'new_gc_token' in resp_json:
                                gc_token = resp_json['new_gc_token']
                                print(f"Updated gc_token: {gc_token}")
                        except Exception:
                            pass
                    
                    # Display progress
                    print(f"[Progress: {request_count}/{SESSION_REFRESH_THRESHOLD} dalam session ini]")
                    
                    # Sleep sesuai time_on_page untuk simulasi user behavior yang konsisten
                    # User benar-benar spend waktu di halaman sesuai yang dilaporkan
                    print(f"⏳ Simulasi user behavior: waiting {time_on_page} detik (sesuai time_on_page)...")
                    time.sleep(time_on_page)
                    
                    # Cek error untuk logging (hanya untuk response yang bukan token error)
                    try:
                        resp_json = response.json()
                        if resp_json.get('status') == 'error':
                            message = resp_json.get('message', '')
                            if ('Usaha ini sudah diground check' not in message and
                                'Token invalid atau sudah terpakai. Silakan refresh halaman.' not in message and
                                'Server sedang sibuk. Silakan coba lagi dalam beberapa detik.' not in message):
                                try:
                                    with open('error.txt', 'a') as f:
                                        f.write(f"Row {index}: {response_text}\n")
                                except Exception as e:
                                    print(f"Warning: Tidak bisa menulis ke error.txt untuk baris {index}: {e}")
                    except Exception:
                        # Jika bukan JSON atau status bukan 200, catat jika bukan token error
                        if status_code != 200:
                            try:
                                with open('error.txt', 'a') as f:
                                    f.write(f"Row {index}: Status {status_code} - {response_text}\n")
                            except Exception as e:
                                print(f"Warning: Tidak bisa menulis ke error.txt untuk baris {index}: {e}")
                
                # Check VPN sebelum delay
                if not monitor_vpn_and_wait_if_disconnected():
                    print("\n❌ Script dihentikan karena VPN terputus dan tidak dapat reconnect")
                    break
                
            print("Semua pengiriman selesai.")

        except Exception as e:
            print(f"Error: {e}")
        finally:
            # Close browser
            browser.close()
    else:
        print("Login gagal, tidak dapat melanjutkan permintaan.")

if __name__ == "__main__":
    main()




