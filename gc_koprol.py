import requests
import pandas as pd
import time
import sys
import json
import re
from login import login_with_sso, user_agents


version = "1.2.3"

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

    # Muat pengguna dari user.txt jika tersedia. Format per baris: username,password ATAU username password ATAU username:password
    users = []
    try:
        with open('user.txt', 'r', encoding='utf-8') as uf:
            for ln in uf:
                ln = ln.strip()
                if not ln or ln.startswith('#'):
                    continue
                creds = None
                if ',' in ln:
                    creds = ln.split(',', 1)
                elif ':' in ln:
                    creds = ln.split(':', 1)
                else:
                    parts = ln.split()
                    if len(parts) >= 2:
                        creds = [parts[0], parts[1]]
                if creds and len(creds) >= 2:
                    users.append((creds[0].strip(), creds[1].strip()))
    except FileNotFoundError:
        users = []

    # Wajibkan user.txt: jika tidak ada pengguna ditemukan, keluar dengan instruksi
    if not users:
        print("Error: user.txt tidak ditemukan atau kosong. Buat file user.txt dengan format: username,password per baris.")
        print("Contoh:\nuser1,password1\nuser2,password2")
        sys.exit(1)

    # nomor_baris dapat diberikan via argv sebagai arg ke-4, jika ada
    nomor_baris = int(sys.argv[4]) if len(sys.argv) > 4 else None

    # Opsional: durasi tidur (detik) sebagai argumen pertama: `python gc_koprol.py 10`
    # Jika arg pertama adalah angka, gunakan sebagai `sleep_seconds`.
    sleep_seconds = 10
    if len(sys.argv) > 1:
        try:
            maybe = int(sys.argv[1])
            sleep_seconds = maybe
        except Exception:
            pass

    # Jika nomor_baris tidak diberikan, baca dari baris.txt
    if nomor_baris is None:
        try:
            with open('baris.txt', 'r') as f:
                nomor_baris = int(f.read().strip())
        except FileNotFoundError:
            nomor_baris = 0

    # Lakukan login dan dapatkan objek halaman (mulai dengan user pertama)
    current_user_index = 0
    username, password = users[current_user_index]
    otp_code = None
    try:
        page, browser = login_with_sso(username, password, otp_code)
    except Exception as e:
        print(f"Login gagal untuk user {username}: {e}")
        raise

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
                    df = pd.read_csv('GC_TDK_DITEMUKAN.csv', encoding=enc)
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

            # Loop untuk setiap baris mulai dari nomor_baris
            # lacak waktu untuk memutar pengguna setiap 4 menit (240 detik)
            rotate_interval = 4 * 60
            last_rotate = time.time()

            for index in range(nomor_baris, len(df)):
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

                # Putar pengguna jika interval telah berlalu (lakukan ini di antara baris, bukan selama upaya permintaan)
                try:
                    if time.time() - last_rotate >= rotate_interval and len(users) > 1:
                        old_index = current_user_index
                        current_user_index = (current_user_index + 1) % len(users)
                        new_username, new_password = users[current_user_index]
                        print(f"\n[INFO] Rotating user: {old_index} -> {current_user_index} ({new_username})")
                        try:
                            # close old browser and login as new user
                            try:
                                browser.close()
                            except Exception:
                                pass
                            page, browser = login_with_sso(new_username, new_password, None)
                            page.goto(url_gc)
                            page.wait_for_load_state('networkidle')
                            _token, gc_token = extract_tokens(page)
                            print(f"[INFO] Switched user, refreshed tokens: {_token} / {gc_token}")
                        except Exception as e:
                            print(f"[WARN] Gagal switch user ke {new_username}: {e}")
                        last_rotate = time.time()
                except Exception:
                    pass
                
                # Gunakan Playwright API Request untuk mengirim data (lebih aman dari blokir)
                max_request_retries = 5
                request_success = False
                
                for request_attempt in range(max_request_retries):
                    try:
                        form_data = {
                            "perusahaan_id": str(perusahaan_id),
                            "latitude": str(latitude),
                            "longitude": str(longitude),
                            "hasilgc": str(hasilgc),
                            "gc_token": gc_token,
                            "_token": _token
                        }
                        
                        # Headers tambahan spesifik untuk POST ini
                        post_headers = {
                            "origin": "https://matchapro.web.bps.go.id",
                            "referer": "https://matchapro.web.bps.go.id/dirgc"
                        }

                        # Kirim request menggunakan context browser (cookies & session otomatis terpakai)
                        response = page.request.post(url, form=form_data, headers=post_headers, timeout=30000)
                        
                        status_code = response.status
                        response_text = response.text()
                        
                        # Tangani 429 Terlalu Banyak Permintaan
                        if status_code == 429:
                            try:
                                resp_json = response.json()
                                message = resp_json.get('message', 'Terlalu banyak permintaan.')
                                retry_after = resp_json.get('retry_after', 600)  # default 10 menit
                                
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
                                
                                # Tambahkan 10 detik sebagai buffer
                                wait_time_seconds += 10

                                print(f"⏳ Menunggu {wait_time_seconds} detik ({wait_time_seconds//60} menit {wait_time_seconds%60} detik)...")
                                print("="*50 + "\n")

                                # Jika multi-pengguna, putar ke pengguna berikutnya segera alih-alih menunggu lama
                                if len(users) > 1:
                                    try:
                                        old_index = current_user_index
                                        current_user_index = (current_user_index + 1) % len(users)
                                        new_username, new_password = users[current_user_index]
                                        print(f"[INFO] 429 received — switching user: {old_index} -> {current_user_index} ({new_username})")
                                        try:
                                            try:
                                                browser.close()
                                            except Exception:
                                                pass
                                            page, browser = login_with_sso(new_username, new_password, None)
                                            page.goto(url_gc)
                                            page.wait_for_load_state('networkidle')
                                            _token, gc_token = extract_tokens(page)
                                            print(f"[INFO] Switched user after 429, refreshed tokens: {_token} / {gc_token}")
                                        except Exception as e:
                                            print(f"[WARN] Gagal switch user setelah 429: {e}")
                                        last_rotate = time.time()
                                        # jeda singkat sebelum mencoba ulang dengan pengguna baru
                                        time.sleep(5)
                                        if request_attempt < max_request_retries - 1:
                                            continue
                                        else:
                                            print(f"Max retries reached untuk baris {index} setelah 429 error")
                                            break
                                    except Exception as e:
                                        print(f"Error saat mencoba switch user setelah 429: {e}")
                                        # fallback ke menunggu jika switch gagal
                                        time.sleep(wait_time_seconds)
                                else:
                                    # Pengguna tunggal: tunggu durasi penuh
                                    time.sleep(wait_time_seconds)
                                    # Refresh tokens setelah menunggu
                                    print("Refreshing tokens setelah menunggu...")
                                    page.reload()
                                    page.wait_for_load_state('networkidle')
                                    _token, gc_token = extract_tokens(page)
                                    print(f"Refreshed _token: {_token}")
                                    print(f"Refreshed gc_token: {gc_token}")
                                    # Retry request yang sama
                                    if request_attempt < max_request_retries - 1:
                                        time.sleep(5)
                                        continue
                                    else:
                                        print(f"Max retries reached untuk baris {index} setelah 429 error")
                                        break
                            except Exception as e:
                                print(f"Error processing 429 response: {e}")
                                print("Menunggu 10 menit sebagai fallback...")
                                time.sleep(610)  # 10 menit + 10 detik
                                continue
                        
                        # Periksa apakah ini adalah error yang perlu dicoba ulang pada baris yang sama
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
                        is_retryable_error = (
                            "timed out" in error_message or 
                            "timeout" in error_message or
                            "econnreset" in error_message or
                            "connection reset" in error_message or
                            "connection refused" in error_message or
                            "connection aborted" in error_message or
                            "network" in error_message or
                            "socket" in error_message or
                            "target page" in error_message or
                            "has been closed" in error_message
                        )
                        
                        if is_retryable_error:
                            if request_attempt < max_request_retries - 1:
                                print(f"Connection error untuk row {index} (attempt {request_attempt + 1}/{max_request_retries}): {e}. Retrying in 5 seconds...")
                                # If browser/page was closed, try to re-login current user before retrying
                                if "target page" in error_message or "has been closed" in error_message:
                                    try:
                                        print("[INFO] Detected closed page/browser. Re-login current user...")
                                        uname, pwd = users[current_user_index]
                                        try:
                                            browser.close()
                                        except Exception:
                                            pass
                                        page, browser = login_with_sso(uname, pwd, None)
                                        page.goto(url_gc)
                                        page.wait_for_load_state('networkidle')
                                        _token, gc_token = extract_tokens(page)
                                        print("[INFO] Re-login berhasil.")
                                    except Exception as re:
                                        print(f"[WARN] Re-login gagal: {re}")
                                time.sleep(5)
                                continue
                            else:
                                print(f"Error during request logging for row {index}: {e} (max retries reached)")
                        else:
                            # Error lain yang tidak bisa di-retry, langsung log dan lanjut
                            print(f"Error during request logging for row {index}: {e}")
                            break
                
                # Jika request berhasil, lanjutkan dengan pemrosesan response
                if request_success:
                    # Catat baris terakhir
                    try:
                        with open('baris.txt', 'w') as f:
                            f.write(str(index))
                    except PermissionError:
                        print(f"Warning: Tidak bisa menulis ke baris.txt untuk baris {index}")
                    
                    # Perbarui gc_token jika ada (untuk respons yang berhasil)
                    if status_code == 200:
                        try:
                            resp_json = response.json()
                            if 'new_gc_token' in resp_json:
                                gc_token = resp_json['new_gc_token']
                                print(f"Updated gc_token: {gc_token}")
                        except Exception:
                            pass
                    
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
                
                # Delay untuk menghindari rate limit
                time.sleep(sleep_seconds)

            print("Semua pengiriman selesai.")

        except Exception as e:
            print(f"Error: {e}")
        finally:
            # Tutup browser
            browser.close()
    else:
        print("Login gagal, tidak dapat melanjutkan permintaan.")

if __name__ == "__main__":
    main()

