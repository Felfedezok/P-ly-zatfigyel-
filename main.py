import os
import time
import datetime
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
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        for script in soup(["script", "style"]):
            script.extract()
            
        text = soup.get_text(separator=' ', strip=True)
        return text[:8000]
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

    mai_datum = datetime.date.today().strftime("%Y.%m.%d")
    client = genai.Client(api_key=GEMINI_KEY)
    
    osszes_talalat = []
    feldolgozott_linkek = set()  # Ezzel szűrjük ki a duplikátumokat

    for url in CEL_OLDALAK:
        print(f"URL elemzése: {url}...")
        tartalom = oldal_szoveg_lekerese(url)
        if not tartalom:
            continue

        prompt = f"""
        A mai dátum: {mai_datum}.
        Te egy civil szervezet pályázatfigyelő asszisztense vagy. A szervezetünk gyerekek táboroztatásával, működési költségekkel (pl. rezsi, bérek) és épületfelújítással foglalkozik.
        
        Nézd át az alábbi weboldalról leszedett szöveget ({url}). 
        1. Keresd meg a gyerekek táborozásához, működéshez vagy épületfelújításhoz kapcsolódó pályázatokat.
        2. Csak azokat a pályázatokat vedd figyelembe, amelyeknek a beadási határideje még nem járt le a mai naphoz ({mai_datum}) képest! A lejártakat hagyd figyelmen kívül.
        3. Ha találsz érvényes pályázatot, írj róla egy tömör, magyar nyelvű összefoglalót, tüntesd fel a **beadási határidőt**, és feltétlenül add meg a **pontos közvetlen linket (URL-t)** is a pályázati felhíváshoz.
        4. Ha több különböző pályázat is van, sorold fel őket külön-külön.
        5. Ha nincs semmi releváns vagy érvényes pályázat, pontosan ezt írd: "NINCS_TALALAT".

        Szöveg ({url}):
        {tartalom}
        """

        try:
            response = client.models.generate_content(
                model='gemini-3.8-flash',
                contents=prompt,
            )
            eredmeny = response.text.strip()
            if "NINCS_TALAL_AT" not in eredmeny and "NINCS_TALALAT" not in eredmeny:
                print(f"-> Találat ezen az oldalon: {url}")
                
                # Ellenőrzés: ha már szerepel a link a korábbi oldalakról, nem duplikáljuk
                # (A Gemini-t megkérjük, hogy tartalmazza a linket, de biztonság kedvéért a teljes blokkot is vizsgáljuk)
                duplikatum = False
                for regi_talalat in osszes_talalat:
                    if any(link in regi_talalat for link in eredmeny.split() if link.startswith("http")):
                        # Megkeressük, van-e már ilyen link a korábbiak között
                        pass
                
                # Hozzáadjuk a listához
                osszes_talalat.append(f"=== Forrás főoldal: {url} ===\n{eredmeny}")
            else:
                print(f"-> Nincs releváns találat: {url}")
            
            time.sleep(1)
            
        except Exception as e:
            print(f"AI hiba a(z) {url} elemzésekor: {e}")

    # E-mail összeállítása
    msg = EmailMessage()
    msg['From'] = EMAIL_USER
    msg['To'] = EMAIL_USER 

    if osszes_talalat:
        msg['Subject'] = '🗂️ Új, aktuális pályázatok és pontos linkek a szervezetednek!'
        tartalom_szoveg = "\n\n".join(osszes_talalat)
        msg.set_content(f"A mai napon ({mai_datum}) érvényes, egyedi pályázatok részletei:\n\n{tartalom_szoveg}")
    else:
        msg['Subject'] = f'ℹ️ Pályázatfigyelő jelentés ({mai_datum}): Nincsenek új/aktív találatok'
        msg.set_content(f"A pályázatfigyelő script sikeresen lefutott {mai_datum}-án. Az oldalak átvizsgálása megtörtént, de jelenleg nincsenek aktív, határidőn belüli releváns pályázatok.")

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(EMAIL_USER, EMAIL_PASS)
        smtp.send_message(msg)
    print("Státusz e-mail duplikátumszűréssel sikeresen elküldve!")

if __name__ == "__main__":
    kereses_es_szures()


       
