from playwright.sync_api import sync_playwright
import sys

def login_with_sso(username, password, otp_code=None):
    """
    Lakukan login SSO ke MatchaPro dan kembalikan objek halaman jika berhasil.
    Returns: objek halaman jika login berhasil, None jika tidak.
    """
    p = sync_playwright().start()
    browser = p.chromium.launch(headless=False)  # Set to True for headless
    
    # Emulate mobile to avoid "Not Authorized" / "Akses lewat matchapro mobile aja"
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Linux; Android 12; M2010J19CG Build/SKQ1.211202.001; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/143.0.7499.192 Mobile Safari/537.36",
        viewport={"width": 412, "height": 915},
        is_mobile=True,
        has_touch=True,
        extra_http_headers={
            "x-requested-with": "com.matchapro.app",
            "sec-ch-ua": "\"Android WebView\";v=\"143\", \"Chromium\";v=\"143\", \"Not A(Brand\";v=\"24\"",
            "sec-ch-ua-mobile": "?1",
            "sec-ch-ua-platform": "\"Android\""
        }
    )
    page = context.new_page()

    try:
        # Navigasi ke halaman login
        page.goto("https://matchapro.web.bps.go.id/login")

        # Klik tombol login SSO
        page.click('#login-sso')

        # Tunggu navigasi ke halaman SSO
        page.wait_for_load_state('networkidle')

        # Sekarang di halaman SSO, isi username dan password
        page.fill('input[name="username"]', username)
        page.fill('input[name="password"]', password)

        # Klik tombol submit
        page.click('input[type="submit"]')

        # Tunggu navigasi
        page.wait_for_load_state('networkidle')

        # Cek apakah OTP diperlukan (TOTP)
        try:
            otp_input = page.locator('input[name="otp"]').first
            if otp_input.is_visible(timeout=5000):
                if otp_code is None:
                    otp_code = input("Masukkan kode OTP: ")
                otp_input.fill(otp_code)
                page.click('input[type="submit"]')  # Submit OTP
                page.wait_for_load_state('networkidle')
        except:
            pass  # Tidak perlu OTP

        # Tunggu hingga URL berubah ke matchapro
        page.wait_for_url("https://matchapro.web.bps.go.id/**", timeout=30000)

        # Cek apakah login berhasil
        current_url = page.url
        if "matchapro.web.bps.go.id" in current_url and "login" not in current_url:
            print("Login berhasil!")
            return page, browser  # Mengembalikan halaman dan browser untuk menjaga sesi
        else:
            print("Login gagal. Periksa kredensial.")
            print(f"Current URL: {current_url}")
            browser.close()
            return None, None

    except Exception as e:
        print(f"Error selama login: {e}")
        browser.close()
        return None, None

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python login.py <username> <password> [otp_code]")
        sys.exit(1)

    username = sys.argv[1]
    password = sys.argv[2]
    otp_code = sys.argv[3] if len(sys.argv) > 3 else None

    page, browser = login_with_sso(username, password, otp_code)
    if page:
        print("Objek halaman diperoleh.")
        browser.close()
    else:
        print("Gagal memperoleh objek halaman.")
