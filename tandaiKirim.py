import requests
import pandas as pd
import time
import sys
import json
import re
from login import login_with_sso

version = "1.2.1"

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
        # Simpan konten halaman untuk debugging jika token tidak ditemukan
        try:
            with open("debug_page_content.html", "w", encoding="utf-8") as f:
                f.write(content)
            print("Gagal menemukan gc_token. Konten halaman telah disimpan ke debug_page_content.html")
        except Exception as e:
            print(f"Gagal menyimpan debug page: {e}")
            
        raise Exception("Token tidak ditemukan")
    
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

    if len(sys.argv) < 3:
        print("Usage: python tandaiKirim.py <username> <password> [otp_code] [nomor baris]")
        sys.exit(1)

    username = sys.argv[1]
    password = sys.argv[2]
    otp_code = sys.argv[3] if len(sys.argv) > 3 else None
    nomor_baris = int(sys.argv[4]) if len(sys.argv) > 4 else None

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
            df = pd.read_csv('data_gc_profiling_bahan_kirim.csv')

            headers = {
                "host": "matchapro.web.bps.go.id",
                "connection": "keep-alive",
                "sec-ch-ua": "\"Android WebView\";v=\"143\", \"Chromium\";v=\"143\", \"Not A(Brand\";v=\"24\"",
                "sec-ch-ua-mobile": "?1",
                "sec-ch-ua-platform": "\"Android\"",
                "upgrade-insecure-requests": "1",
                "user-agent": "Mozilla/5.0 (Linux; Android 12; M2010J19CG Build/SKQ1.211202.001; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/143.0.7499.192 Mobile Safari/537.36",
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
                
                payload = f"perusahaan_id={perusahaan_id}&latitude={latitude}&longitude={longitude}&hasilgc={hasilgc}&gc_token={gc_token}&_token={_token}"
                
                response = requests.post(url, data=payload, headers=headers, cookies=session_cookies)
                
                print(f"Row {index}: {response.status_code} - {response.text}")
                
                # Catat baris terakhir
                try:
                    with open('baris.txt', 'w') as f:
                        f.write(str(index))
                except PermissionError:
                    print(f"Warning: Tidak bisa menulis ke baris.txt untuk baris {index}")
                
                if response.status_code != 200:
                    # Refresh tokens with retry mechanism
                    print("Status code != 200, refreshing tokens...")
                    max_retries = 3
                    for attempt in range(max_retries):
                        try:
                            page.reload()
                            page.wait_for_load_state('networkidle')
                            _token, gc_token = extract_tokens(page)
                            print(f"Refreshed _token: {_token}")
                            print(f"Refreshed gc_token: {gc_token}")
                            # Update cookies
                            cookies = page.context.cookies()
                            session_cookies = {cookie['name']: cookie['value'] for cookie in cookies}
                            break  # Success, exit retry loop
                        except Exception as e:
                            print(f"Attempt {attempt + 1} failed: {e}")
                            if attempt < max_retries - 1:
                                print("Retrying in 5 seconds...")
                                time.sleep(5)
                            else:
                                print("Max retries reached. Silakan jalankan ulang script.")
                                sys.exit(1)
                else:
                    # Update gc_token if present
                    try:
                        resp_json = response.json()
                        if 'new_gc_token' in resp_json:
                            gc_token = resp_json['new_gc_token']
                            print(f"Updated gc_token: {gc_token}")
                    except json.JSONDecodeError:
                        pass
                
                # Cek error untuk logging
                try:
                    resp_json = response.json()
                    if resp_json.get('status') == 'error':
                        message = resp_json.get('message', '')
                        if 'Usaha ini sudah diground check' not in message:
                            try:
                                with open('error.txt', 'a') as f:
                                    f.write(f"Row {index}: {response.text}\n")
                            except Exception as e:
                                print(f"Warning: Tidak bisa menulis ke error.txt untuk baris {index}: {e}")
                except json.JSONDecodeError:
                    # Jika bukan JSON, catat jika status code bukan 200
                    if response.status_code != 200:
                        try:
                            with open('error.txt', 'a') as f:
                                f.write(f"Row {index}: Status {response.status_code} - {response.text}\n")
                        except Exception as e:
                            print(f"Warning: Tidak bisa menulis ke error.txt untuk baris {index}: {e}")
                
                # Delay untuk menghindari rate limit
                time.sleep(5)

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
