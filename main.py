import os
import smtplib
from email.message import EmailMessage
from google import genai
import requests
from bs4 import BeautifulSoup

# ==========================================
# IDE ÍRD BE A FIGYELNI KÍVÁNT OLDALAK CÍMÉT:
# ==========================================
CEL_OLDALAK = [
    "https://palyazat.gov.hu",  # Példa: Hivatalos pályázati portál
    # Ide írhatsz továbbiakat is, vesszővel elválasztva, például:
    # "https://civil.hu/hirek",
]

def oldal_szoveg_lekerese(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        for script in soup(["script", "style"]):
            script.extract()
            
        text = soup.get_text(separator=' ', strip=True)
        return text[:15000]
    except Exception as e:
        print(f"Hiba történt a(z) {url} letöltésekor: {e}")
        return ""

def kereses_es_szures():
    GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
    EMAIL_USER = os.environ.get("GMAIL_USER")
    EMAIL_PASS = os.environ.get("GMAIL_PASS")
    
    if not GEMINI_KEY:
        print("Nincs beállítva a GEMINI_API_KEY titok!")
        return

    client = genai.Client(api_key=GEMINI_KEY)

    osszesitett_szoveg = ""
    for url in CEL_OLDALAK:
        print(f"URL elemzése: {url}...")
        tartalom = oldal_szoveg_lekerese(url)
        if tartalom:
            osszesitett_szoveg += f"\n--- FORRÁS URL: {url} ---\n{tartalom}\n"

    if not osszesitett_szoveg.strip():
        print("Nem sikerült adatot lekérni a megadott oldalakról.")
        return

    prompt = f"""
    Te egy civil szervezet pályázatfigyelő asszisztense vagy. A szervezetünk gyerekek táboroztatásával, működési költségekkel (pl. rezsi, bérek) és épületfelújítással foglalkozik.
    Itt vannak a megfigyelt weboldalakról leszedett friss szövegek. Kérlek, nézd át őket, és ha bármelyik szövegrészlet releváns civil pályázatra vagy támogatásra utal (tábor, működés, felújítás), válaszd ki, és írj róla egy tömör, magyar nyelvű összefoglalót a forrás linkjével együtt.
    Ha egyik oldalon sincs semmi releváns, akkor pontosan ezt írd: "NINCS_TALALAT".

    Letöltött szövegek:
    {osszesitett_szoveg}
    """

    response = client.models.generate_content(
        model='gemini-3.8-flash',
        contents=prompt,
    )
    
    eredmeny = response.text
    print("AI válasz:", eredmeny)
    
    if "NINCS_TALALAT" not in eredmeny:
        msg = EmailMessage()
        msg.set_content(eredmeny)
        msg['Subject'] = '🗂️ Új releváns pályázat érkezett a civil szervezetednek!'
        msg['From'] = EMAIL_USER
        msg['To'] = EMAIL_USER 
        
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_USER, EMAIL_PASS)
            smtp.send_message(msg)
        print("E-mail elküldve!")
    else:
        print("Az AI nem talált releváns pályázatot a megadott oldalakon.")

if __name__ == "__main__":
    kereses_es_szures()
