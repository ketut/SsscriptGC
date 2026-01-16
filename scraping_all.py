import requests
import time
import pandas as pd
from tqdm import tqdm
from login import login_with_sso
import re

# ------------------------------------------------------
# KONFIGURASI - HARUS DIUPDATE SESUAI STATUS TERBARU
# ------------------------------------------------------
BASE_URL = "https://matchapro.web.bps.go.id/direktori-usaha/data-gc-card"

HEADERS = {
    "host": "matchapro.web.bps.go.id",
    "connection": "keep-alive",
    "sec-ch-ua-platform": "\"Windows\"",
    "x-requested-with": "XMLHttpRequest",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "accept": "*/*",
    "sec-ch-ua": "\"Google Chrome\";v=\"131\", \"Chromium\";v=\"131\", \"Not_A Brand\";v=\"24\"",
    "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
    "sec-ch-ua-mobile": "?0",
    "origin": "https://matchapro.web.bps.go.id",
    "sec-fetch-site": "same-origin",
    "sec-fetch-mode": "cors",
    "sec-fetch-dest": "empty",
    "referer": "https://matchapro.web.bps.go.id/dirgc",
    "accept-language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
    # !!! WAJIB GANTI !!!
    "cookie": "BIGipServeriapps_webhost_mars_443.app~iapps_webhost_mars_443_pool=1418199050.20480.0000; TS0151fc2b=0167a1c861a692c4c516ea14cef77f079192991528078a048c37cd54af05dc68e3bbdd55effe6a9d9a6447ad6a4cbbf0f206c773d6; XSRF-TOKEN=eyJpdiI6IjFRUGp1N2lTMVVCcW5kWmg0dGozMEE9PSIsInZhbHVlIjoiOWlrM2ZYSmI4UWV6YzMwd1dKdENPdzgrTVZISkNSSzJtMi9OUWplMDRpZlo3UTBIZUkwczNtQTlnNXJQUkpnK3JHajJ5TGJUTnVTaVY2UVJia2FkUFZzVWl2Z0I2aGpwWGZ2a2xWRE8xelRkaEx6dGRuaEphaGVOQWdoR25uQlQiLCJtYWMiOiIwYzVhODNlZGJjYWZjNzQxMjljNDYyNzEwYjdjOGI2Zjk0NTQxMGRkNWJhYTc3NmEwZGE5ZmJlM2U5OGEwMDhkIiwidGFnIjoiIn0%3D; laravel_session=eyJpdiI6IkI5SHN4My9WY3Nkc3hXdHdzVkN1R2c9PSIsInZhbHVlIjoiYnNUcUd6Ynd2ZHdXRGxyN1E3STZKaFBYczd3RlI5ZE9JbFdBZ0tTUnRwK29STnFtMXVDMkpLVW1CNXg1M29mQWloWlRDNEt2T0xKdHYzTzllUEt6WmRCSVlsNEliTWgxNks4eVpBUm1jTnJ0d3VyeGNFSnRrVmFYMDhMelVOVHUiLCJtYWMiOiI2MmJkMmYyN2JhNWJkMGIwMjIyOGVhMzUyZWY4YjcxMWQ5OTc4MTYwZTM0OTIxOWYyZmI4ZGQwOTRlZWE2NTNhIiwidGFnIjoiIn0%3D; TS1a53eee7027=0815dd1fcdab2000ead5618125788d97a7b8eecb3c910422f443944af41075f98354ebfab66871a8088d9fcc1e1130009eb4655c9019dcd2648c18388ab84ebf5f44df9d38e4035a68a6c8481af5e0a6ff2c2b8df2dec2198abeb80fff0b5242"
}

# Payload dasar
BASE_PAYLOAD = {
    "_token": "",  # Will be set automatically
    "start": 0,
    "length": 1000,           # Kurangi dari 2000 untuk menghindari response terpotong
    "nama_usaha": "",
    "alamat_usaha": "",
    "provinsi": "",        # akan diisi dari parsing cari_kode.htm
    "kabupaten": "",      # akan diisi dari parsing cari_kode.htm
    "kecamatan": "",
    "desa": "",
    "status_filter": "semua",
    "rtotal": "0",
    "sumber_data": "",
    "skala_usaha": "",
    "idsbr": "",
    "history_profiling": ""
}

# Nama file output
OUTPUT_EXCEL = "direktori_usaha_full_all_columns_2026.xlsx"
OUTPUT_CSV_FALLBACK = "direktori_usaha_full_all_columns_2026.csv"

DELAY_BETWEEN_REQUEST = 1.3     # detik, jangan terlalu kecil
# ------------------------------------------------------


def fetch_page(start, length):
    payload = BASE_PAYLOAD.copy()
    payload["start"] = str(start)
    payload["length"] = str(length)

    try:
        r = requests.post(BASE_URL, data=payload, headers=HEADERS, timeout=20)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"Error saat mengambil data (start={start}): {e}")
        return None


def main():
    print("Melakukan login otomatis...\n")

    # Login credentials - update as needed
    username = input("Masukkan username: ")
    password = input("Masukkan password: ")
    otp_code = input("Masukkan OTP (kosongkan jika tidak ada): ").strip() or None

    # Perform login
    page, browser = login_with_sso(username, password, otp_code)

    if not page:
        print("Login gagal. Tidak dapat melanjutkan scraping.")
        return

    try:
        # Navigate to /dirgc to get _token and parse HTML for provinsi/kabupaten
        url_gc = "https://matchapro.web.bps.go.id/dirgc"
        page.goto(url_gc)
        page.wait_for_load_state('networkidle')

        # Wait for CSRF token meta tag to be attached
        page.wait_for_selector('meta[name="csrf-token"]', state='attached', timeout=10000)

        # Extract _token
        token_element = page.locator('meta[name="csrf-token"]')
        if token_element.count() > 0:
            _token = token_element.get_attribute('content')
            BASE_PAYLOAD["_token"] = _token
            print(f"_token diperoleh: {_token}")
        else:
            print("Gagal mendapatkan _token")
            browser.close()
            return

        # Get cookies
        cookies = page.context.cookies()
        cookie_string = "; ".join([f"{cookie['name']}={cookie['value']}" for cookie in cookies])
        HEADERS["cookie"] = cookie_string
        print("Cookies diperoleh dan diset ke headers")

        # Parse HTML dari request ke direktori-usaha untuk mendapatkan kode provinsi dan kabupaten
        url_direktori = "https://matchapro.web.bps.go.id/direktori-usaha"
        try:
            response = requests.get(url_direktori, headers=HEADERS, timeout=20)
            response.raise_for_status()
            html_content = response.text
            
            # Cari kode provinsi
            prov_match = re.search(r'<select id="f_provinsi".*?<option value="(\d+)" selected>', html_content, re.DOTALL)
            if prov_match:
                kode_provinsi_ver_matchapro = prov_match.group(1)
            else:
                kode_provinsi_ver_matchapro = "122"  # default BALI
            
            # Cari kode kabupaten
            kab_match = re.search(r'<select id="f_kabupaten".*?<option value="(\d+)" selected>', html_content, re.DOTALL)
            if kab_match:
                kode_kabupaten_ver_matchapro = kab_match.group(1)
            else:
                kode_kabupaten_ver_matchapro = "2437"  # default BADUNG
            
            # Update BASE_PAYLOAD
            BASE_PAYLOAD["provinsi"] = kode_provinsi_ver_matchapro
            BASE_PAYLOAD["kabupaten"] = kode_kabupaten_ver_matchapro
            
            print(f"Kode provinsi: {kode_provinsi_ver_matchapro}")
            print(f"Kode kabupaten: {kode_kabupaten_ver_matchapro}")
        
        except Exception as e:
            print(f"Error saat parsing HTML dari direktori-usaha: {e}")
            # Gunakan default
            BASE_PAYLOAD["provinsi"] = "122"
            BASE_PAYLOAD["kabupaten"] = "2437"

    except Exception as e:
        print(f"Error saat login atau ekstraksi: {e}")
        browser.close()
        return

    # Close browser after getting credentials
    browser.close()

    print("Login berhasil. Memulai pengambilan data...\n")

    # Cek total data & ambil response pertama
    first_response = fetch_page(0, 100)  # Gunakan 100 untuk cek total
    if not first_response or "recordsTotal" not in first_response:
        print("Gagal mendapatkan informasi awal.")
        print("Periksa kembali autentikasi dan koneksi internet")
        return

    total_records = first_response["recordsTotal"]
    print(f"Total data yang tersedia : {total_records:,} record")
    print(f"Output akan disimpan ke : {OUTPUT_EXCEL}\n")

    all_records = []
    length_per_request = 1000  # Kurangi dari 2000 untuk menghindari response terpotong

    with tqdm(total=total_records, desc="Progress", unit="record") as pbar:
        start = 0
        while start < total_records:
            data = fetch_page(start, length_per_request)

            if not data or "data" not in data or not isinstance(data["data"], list):
                print(f"\nGagal di posisi start={start}. Mencoba lagi setelah jeda...")
                time.sleep(6)
                continue

            page_data = data["data"]
            all_records.extend(page_data)

            fetched_this_time = len(page_data)
            pbar.update(fetched_this_time)

            start += fetched_this_time

            time.sleep(DELAY_BETWEEN_REQUEST)

    if not all_records:
        print("\nTidak ada data yang berhasil dikumpulkan.")
        return

    print(f"\nSelesai mengumpulkan {len(all_records):,} record")

    # Jadikan DataFrame (semua kolom otomatis ikut)
    df = pd.DataFrame(all_records)

    print(f"Jumlah kolom yang didapat: {len(df.columns)}")
    print("Nama kolom:", ", ".join(df.columns.tolist()))

    # Simpan ke CSV
    try:
        df.to_csv(OUTPUT_CSV_FALLBACK, index=False, encoding='utf-8-sig')
        print(f"\nBerhasil disimpan ke: {OUTPUT_CSV_FALLBACK}")
        print(f"\nTips: Jika membuka csv di excel pilih dont convert")
    except Exception as e:
        print(f"Gagal menyimpan CSV: {e}")


if __name__ == "__main__":
    main()
