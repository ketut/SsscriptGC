import requests
import pandas as pd
import time
import sys
import json
import re
from login import login_with_sso

version = "1.1.0"

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
    match = re.search(r"let gcSubmitToken = '([^']+)';", content)
    if match:
        gc_token = match.group(1)
    else:
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
                print("Versi tidak cocok. Silakan update script.")
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
                "sec-ch-ua-platform": "\"Windows\"",
                "x-requested-with": "XMLHttpRequest",
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
                "accept": "*/*",
                "sec-ch-ua": "\"Google Chrome\";v=\"143\", \"Chromium\";v=\"143\", \"Not A(Brand\";v=\"24\"",
                "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
                "sec-ch-ua-mobile": "?0",
                "origin": "https://matchapro.web.bps.go.id",
                "sec-fetch-site": "same-origin",
                "sec-fetch-mode": "cors",
                "sec-fetch-dest": "empty",
                "referer": "https://matchapro.web.bps.go.id/dirgc",
                "accept-encoding": "gzip, deflate, br, zstd",
                "accept-language": "en-US,en;q=0.9",
            }

            # Loop untuk setiap baris mulai dari nomor_baris
            for index in range(nomor_baris, len(df)):
                row = df.iloc[index]
                perusahaan_id = row['perusahaan_id']
                latitude = row['latitude']
                longitude = row['longitude']
                hasilgc = row['hasilgc']
                
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
                    # Refresh tokens
                    print("Status code != 200, refreshing tokens...")
                    page.reload()
                    page.wait_for_load_state('networkidle')
                    try:
                        _token, gc_token = extract_tokens(page)
                        print(f"Refreshed _token: {_token}")
                        print(f"Refreshed gc_token: {gc_token}")
                        # Update cookies
                        cookies = page.context.cookies()
                        session_cookies = {cookie['name']: cookie['value'] for cookie in cookies}
                    except Exception as e:
                        print(f"Failed to refresh tokens: {e}")
                        # Continue with old tokens or break?
                        continue
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
