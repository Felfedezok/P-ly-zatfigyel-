import os
import time
import smtplib
from email.message import EmailMessage
from google import genai
import requests
from bs4 import BeautifulSoup

CEL_OLDALAK = [
    "https://palyazat.gov.hu",
    "https://civil.info.hu",
    "https://sarospatak-online.hu/rovat/varoshaza/",
    "https://kormany.hu",
    "https://www.nonprofit.hu/palyazatok",
    "https://bgazrt.hu",
    "https://www.eon.hu/hu/rolunk/fenntarthatosag/felelosseggel-a-tarsadalomert/tarsadalom/szponzoracio/partnersegek--palyazatok.html",
    "https://profilii.hu",
]

def oldal_szoveg_lekerese(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        # Szigorú timeout: ha 10 másodperc alatt nem válaszol az oldal, megszakítjuk, hogy ne akadjon el!
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        for script in soup(["script", "style"]):
            script.extract()
            
        text = soup.get_text(separator=' ', strip=True)
        return text[:8000] # Kicsit visszavettük a méretet a villámgyors feldolgozásért
    except Exception as e:
        print(f"Figyelem: A(z) {url} elérését kihagytuk (hiba/időtúllépés): {e}")
        return ""

def kereses_es_szures():
    GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
    EMAIL_USER = os.environ.get("GMAIL_USER")
    EMAIL_PASS = os.environ.get("GMAIL_PASS")
    
    if not GEMINI_KEY:
        print("Nincs beállítva a GEMINI_API_KEY titok!")
        return

    client = genai.Client(api_key=GEMINI_KEY)
    osszes_talalat = []

    for url in CEL_OLDALAK:
        print(f"URL elemzése: {url}...")
        tartalom = oldal_szoveg_lekerese(url)
        if not tartalom:
            continue

        prompt = f"""
        Te egy civil szervezet pályázatfigyelő asszisztense vagy. A szervezetünk gyerekek táboroztatásával, működési költségekkel (pl. rezsi, bérek) és épületfelújítással foglalkozik.
        Nézd át az alábbi weboldalról leszedett szöveget. Ha bármelyik részlet releváns civil pályázatra vagy támogatásra utal (tábor, működés, felújítás), írj róla egy tömör, magyar nyelvű összefoglalót a forrás linkjével együtt ({url}).
        Ha nincs semmi releváns, pontosan ezt írd: "NINCS_TALALAT".

        Szöveg ({url}):
        {tartalom}
        """

        try:
            response = client.models.generate_content(
                model='gemini-3.8-flash',
                contents=prompt,
            )
            eredmeny = response.text.strip()
            if "NINCS_TALALAT" not in eredmeny:
                print(f"-> Találat ezen az oldalon: {url}")
                osszes_talalat.append(f"=== Forrás: {url} ===\n{eredmeny}")
            else:
                print(f"-> Nincs releváns találat: {url}")
            
            time.sleep(1)
            
        except Exception as e:
            print(f"AI hiba a(z) {url} elemzésekor: {e}")

    if osszes_talalat:
        vegso_uzenet = "\n\n".join(osszes_talalat)
        msg = EmailMessage()
        msg.set_content(vegso_uzenet)
        msg['Subject'] = '🗂️ Új releváns pályázatok érkeztek a civil szervezetednek!'
        msg['From'] = EMAIL_USER
        msg['To'] = EMAIL_USER 
        
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_USER, EMAIL_PASS)
            smtp.send_message(msg)
        print("E-mail sikeresen elküldve a találatokkal!")
    else:
        print("Egyik megadott oldalon sem volt releváns pályázat.")

if __name__ == "__main__":
    kereses_es_szures()

       
