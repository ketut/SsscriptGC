import sys
import time
import re
import base64
import json
import os
import argparse
from difflib import SequenceMatcher
from rapidfuzz import fuzz
import pandas as pd
from login import login_with_sso

RESUME_FILE = "baris.txt"

def clean_text(text):
    """Hapus karakter non-latin (Jepang, Korea, China, dll), sisakan huruf latin, angka, tanda baca umum"""
    # Hanya simpan karakter ASCII printable + karakter latin extended (aksen, dll)
    cleaned = re.sub(r'[^\x20-\x7E\u00C0-\u024F]', '', text)
    # Hapus spasi berlebih
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned

def similarity(a, b):
    """Hitung kemiripan nama usaha menggunakan rapidfuzz token_sort_ratio.
    
    token_sort_ratio: memecah jadi kata, sort, lalu bandingkan.
    Mengabaikan urutan kata, case-insensitive.
    
    Contoh:
    - "Dilan tailor" vs "ULAN TAILOR" → ~74% (beda kata kunci)
    - "Dilan tailor" vs "Dilan Tailor" → 100% (sama persis)
    - "Warung Makan Ibu Sari" vs "Ibu Sari Warung Makan" → 100% (urutan beda, isi sama)
    """
    return fuzz.token_sort_ratio(a, b)

def main():
    parser = argparse.ArgumentParser(description="Tambah usaha ke SBR via Matcha Pro")
    parser.add_argument("username", help="Username SSO")
    parser.add_argument("password", help="Password SSO")
    parser.add_argument("otp_code", nargs="?", default=None, help="OTP code (optional)")
    parser.add_argument("--csv", required=True, help="Nama file CSV yang akan dikirim")
    args = parser.parse_args()

    username = args.username
    password = args.password
    otp_code = args.otp_code
    csv_file = args.csv

    page, browser = login_with_sso(username, password, otp_code)

    if page:
        try:
            url_gc = "https://matchapro.web.bps.go.id/dirgc"
            page.goto(url_gc)
            page.wait_for_load_state('networkidle')

            page.wait_for_selector('meta[name="csrf-token"]', state='attached', timeout=10000)

            token_element = page.locator('meta[name="csrf-token"]')
            if token_element.count() > 0:
                _token = token_element.get_attribute('content')
                print(f"Extracted _token: {_token}")
            else:
                print("Failed to extract _token - meta tag not found")
                print(f"Page title: {page.title()}")
                browser.close()
                return

            # Ambil cookies
            cookies = page.context.cookies()
            session_cookies = {cookie['name']: cookie['value'] for cookie in cookies}

            # Baca file CSV
            try:
                df = pd.read_csv(csv_file)
                print(f"Loaded {len(df)} rows from {csv_file}")
            except FileNotFoundError:
                print(f"File {csv_file} not found")
                browser.close()
                return

            post_url = "https://matchapro.web.bps.go.id/dirgc/draft-tambah-usaha"

            def send_post(page, url, payload_dict):
                """Kirim POST via fetch di browser Playwright - pakai sesi browser langsung"""
                js_code = """
                async (args) => {
                    const [url, body] = args;
                    const params = new URLSearchParams(body);
                    const resp = await fetch(url, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                            'X-Requested-With': 'XMLHttpRequest',
                            'Accept': 'application/json, text/javascript, */*; q=0.01',
                        },
                        body: params.toString(),
                    });
                    const text = await resp.text();
                    return { status: resp.status, body: text };
                }
                """
                result = page.evaluate(js_code, [url, payload_dict])
                return result

            def refresh_token(page, url_gc):
                """Refresh halaman dan ambil token CSRF baru"""
                nonlocal _token
                page.goto(url_gc)
                page.wait_for_load_state('networkidle')
                page.wait_for_selector('meta[name="csrf-token"]', state='attached', timeout=10000)
                new_token = page.locator('meta[name="csrf-token"]').get_attribute('content')
                if new_token:
                    _token = new_token
                    return new_token
                return _token

            def confirm_submit(page, post_url, url_gc, payload, index, nama_usaha_raw, max_sim):
                """Kirim confirm submit dengan retry jika gagal (403/body kosong)"""
                nonlocal _token
                payload["confirmSubmit"] = "true"
                max_retries = 2
                for attempt in range(max_retries):
                    try:
                        resp2 = send_post(page, post_url, payload)
                        # Jika 403 atau body kosong, refresh token dan retry
                        if resp2['status'] == 403 or not resp2['body'].strip():
                            print(f"Row {index+1}: CONFIRM gagal (status {resp2['status']}), refresh token... (attempt {attempt+1}/{max_retries})")
                            time.sleep(2)
                            new_token = refresh_token(page, url_gc)
                            payload["_token"] = new_token
                            time.sleep(1)
                            continue
                        result2 = json.loads(resp2['body'])
                        status2 = result2.get('status', '')
                        if status2 == 'success' or status2 == 'warning':
                            print(f"Row {index+1}: CONFIRM SUKSES - {nama_usaha_raw} (max similarity {max_sim:.1f}%)")
                            return True
                        else:
                            print(f"Row {index+1}: CONFIRM {status2} - {result2.get('message', '')} - {nama_usaha_raw}")
                            return False
                    except Exception as e:
                        print(f"Row {index+1}: CONFIRM error (attempt {attempt+1}/{max_retries}) - {e}")
                        time.sleep(2)
                        try:
                            new_token = refresh_token(page, url_gc)
                            payload["_token"] = new_token
                        except:
                            pass
                print(f"Row {index+1}: CONFIRM GAGAL setelah {max_retries} attempt - {nama_usaha_raw}")
                return False

            # Baca baris terakhir dari baris.txt untuk resume
            start_row = 0
            if os.path.exists(RESUME_FILE):
                try:
                    with open(RESUME_FILE, 'r') as f:
                        start_row = int(f.read().strip())
                    print(f"Resuming from row {start_row + 1} (baris.txt found)")
                except:
                    start_row = 0

            # Proses setiap baris
            
            for index, row in df.iterrows():
                # Lewati baris yang sudah diproses
                if index < start_row:
                    continue

                nama_usaha_raw = clean_text(str(row['name']))
                alamat_raw = clean_text(str(row['address']))

                payload = {
                    "_token": _token,
                    "id_table": "",
                    "nama_usaha": base64.b64encode(nama_usaha_raw.encode('utf-8')).decode('utf-8'),
                    "alamat": base64.b64encode(alamat_raw.encode('utf-8')).decode('utf-8'),
                    "provinsi": str(int(row['provinsi'])),
                    "kabupaten": str(int(row['kabupaten'])),
                    "kecamatan": str(int(row['kecamatan'])),
                    "desa": str(int(row['desa'])),
                    "latitude": str(row['lat']),
                    "longitude": str(row['lon']),
                    "confirmSubmit": "false",
                    "totalSimilar": "0"
                }

                # Ulangi percobaan untuk seluruh alur
                row_done = False
                for row_attempt in range(3):
                    try:
                        resp = send_post(page, post_url, payload)
                    except Exception as e:
                        print(f"Row {index+1}: Gagal fetch (percobaan {row_attempt+1}/3) - {e}")
                        time.sleep(3)
                        # Muat ulang halaman
                        try:
                            page.goto(url_gc)
                            page.wait_for_load_state('networkidle')
                        except:
                            pass
                        continue

                    try:
                        result = json.loads(resp['body'])
                    except Exception:
                        print(f"Row {index+1}: Bukan JSON (percobaan {row_attempt+1}/3) Status {resp['status']} - {resp['body'][:200]}")
                        time.sleep(3)
                        # Muat ulang halaman dan token
                        try:
                            page.goto(url_gc)
                            page.wait_for_load_state('networkidle')
                            page.wait_for_selector('meta[name="csrf-token"]', state='attached', timeout=10000)
                            new_token = page.locator('meta[name="csrf-token"]').get_attribute('content')
                            if new_token:
                                _token = new_token
                                payload["_token"] = _token
                                print(f"Row {index+1}: Token diperbarui")
                        except:
                            pass
                        continue

                    status = result.get('status', '')

                    if status == 'success':
                        print(f"Row {index+1}: SUKSES - {nama_usaha_raw}")
                        row_done = True
                        break
                    elif status == 'warning':
                        # Cek kemiripan nama usaha + nama desa yang sama
                        similar_data = result.get('similarData', [])
                        desa_input = str(row.get('nmdesa_gc', '')).strip().upper()
                        max_sim = 0
                        max_sim_same_desa = 0
                        matched_nama = ""
                        matched_nama_same_desa = ""
                        matched_desa = ""
                        for item in similar_data:
                            sim = similarity(nama_usaha_raw, item.get('nama', ''))
                            # Cek nama desa dari similarData
                            item_desa = str(item.get('nmdesa', '')).strip().upper()
                            same_desa = item_desa != '' and item_desa == desa_input

                            if sim > max_sim:
                                max_sim = sim
                                matched_nama = item.get('nama', '')
                            if sim > max_sim_same_desa and same_desa:
                                max_sim_same_desa = sim
                                matched_nama_same_desa = item.get('nama', '')
                                matched_desa = item_desa

                        # SKIP hanya jika similarity > 80% DAN berada di desa yang sama
                        if max_sim_same_desa > 80:
                            print(f"Row {index+1}: SKIP - USAHA SUDAH ADA \"{nama_usaha_raw}\" (similarity {max_sim_same_desa:.1f}% dengan \"{matched_nama_same_desa}\", desa: {matched_desa})")
                            row_done = True
                            break
                        elif max_sim > 80:
                            print(f"Row {index+1}: NAMA MIRIP tapi BEDA DESA - \"{nama_usaha_raw}\" (similarity {max_sim:.1f}% dengan \"{matched_nama}\", desa input: {desa_input}), tetap submit...")
                            payload["totalSimilar"] = str(len(similar_data))
                            row_done = confirm_submit(page, post_url, url_gc, payload, index, nama_usaha_raw, max_sim)
                            payload["confirmSubmit"] = "false"
                            payload["totalSimilar"] = "0"
                            break
                        else:
                            # Konfirmasi submit
                            payload["totalSimilar"] = str(len(similar_data))
                            row_done = confirm_submit(page, post_url, url_gc, payload, index, nama_usaha_raw, max_sim)
                            payload["confirmSubmit"] = "false"
                            payload["totalSimilar"] = "0"
                            break
                    elif resp['status'] >= 500:
                        print(f"Row {index+1}: Server error (percobaan {row_attempt+1}/3), memuat ulang... - {nama_usaha_raw}")
                        time.sleep(3)
                        try:
                            page.goto(url_gc)
                            page.wait_for_load_state('networkidle')
                            page.wait_for_selector('meta[name="csrf-token"]', state='attached', timeout=10000)
                            new_token = page.locator('meta[name="csrf-token"]').get_attribute('content')
                            if new_token:
                                _token = new_token
                                payload["_token"] = _token
                                print(f"Row {index+1}: Token diperbarui")
                        except:
                            pass
                        continue
                    else:
                        print(f"Row {index+1}: {status} - {result.get('message', resp['body'][:200])}")
                        row_done = True
                        break

                if not row_done:
                    print(f"Row {index+1}: GAGAL setelah 3 attempt - {nama_usaha_raw}")
                
                # Simpan progres ke baris.txt
                with open(RESUME_FILE, 'w') as f:
                    f.write(str(index + 1))
                
                # Jeda antar request
                time.sleep(2)

            print(f"\nSelesai! Total {len(df)} baris diproses.")
            # Hapus baris.txt jika semua selesai
            if os.path.exists(RESUME_FILE):
                os.remove(RESUME_FILE)
                print("baris.txt dihapus (semua data selesai).")

        except Exception as e:
            print(f"Error: {e}")
        finally:
            browser.close()
    else:
        print("Login failed, cannot proceed with request.")

if __name__ == "__main__":
    main()