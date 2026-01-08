#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Kodi felirat kiegészítő a https://feliratok.eu oldalhoz

A kiegészítő feliratok letöltését teszi lehetővé filmekhez illetve sorozatokhoz a https://feliratok.eu oldalról.
"""

__author__ = "g0m3z"
__copyright__ = "Copyright 2026, Babel felirat kiegészítő projekt Kodihoz"
__license__ = "GNU GPLv2"
__version__ = "1.0.1"
__maintainer__ = "g0m3z"
__email__ = ""
__status__ = "Development"

# Szükséges modulok beimportálása

import os
import sys
import xbmcgui
import xbmcplugin
import xbmc
import xbmcvfs
from urllib.parse import parse_qsl
from urllib.parse import urlencode
import urllib.request

# Az 're' modult használjuk az adatok kinyeréséhez a https://feliratok.eu
# oldalról mert az a Python része alapból, így nem kell függőségeket
# installálni mint pl. az lxml esetén és így nagy valószínűséggel régi Kodi
# verziókkal is kompatibilis lesz a kiegészítő.

import re
import io

# Nyelveket tartalmazó könyvtár létrehozása.

languages = {
    "Albán": "sq",
    "Angol": "en",
    "Arab": "ar",
    "Bolgár": "bg",
    "Brazíliai portugál": "pt-br",
    "Cseh": "cs",
    "Dán": "da",
    "Finn": "fi",
    "Flamand": "nl",  # A flamand a holland egyik változata
    "Francia": "fr",
    "Görög": "el",
    "Héber": "he",
    "Holland": "nl",
    "Horvát": "hr",
    "Koreai": "ko",
    "Lengyel": "pl",
    "Magyar": "hu",
    "Német": "de",
    "Norvég": "no",
    "Olasz": "it",
    "Orosz": "ru",
    "Portugál": "pt",
    "Román": "ro",
    "Spanyol": "es",
    "Svéd": "sv",
    "Szerb": "sr",
    "Szlovák": "sk",
    "Szlovén": "sl",
    "Török": "tr"
}

# A felirat letöltési link domain nevének tárolása egy változóban.
main_link = "https://feliratok.eu"

# User-Agent definiálása, hogy a weboldal ne nézze illegális robotnak a
# kiegészítőt.
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

def log_netmozi_metadata():
    """
    Megvizsgálja és a kodi.log-ba írja a Kodi által épp lejátszott média meta adatait. Erre azért van szükség mert ha ezek az információk átadódnak (pl. évad és rész) sokkal pontosabban tudunk keresni releváns feliratra.

    Args:
        None

    Returns:
        Nem tér vissza semmivel. Az eredményt a kodi.log-ba írja.

    Raises:
        None
    """

    # Ellenőrizzük, hogy van-e lejátszás
    if xbmc.Player().isPlayingVideo():
        # Lekérjük az aktuális tag-et (ez a modern módszer)
        tag = xbmc.Player().getVideoInfoTag()
        
        # Összegyűjtjük a kritikus adatokat egy szótárba
        debug_info = {
            "### DEBUG TITLE ###": tag.getTitle(),
            "### DEBUG MEDIATYPE ###": tag.getMediaType(),
            "### DEBUG TVSHOW ###": tag.getTVShowTitle(),
            "### DEBUG SEASON ###": tag.getSeason(),
            "### DEBUG EPISODE ###": tag.getEpisode(),
            "### DEBUG IMDB ID ###": tag.getIMDBNumber(),
            "### DEBUG PLOT ###": tag.getPlot()[:50] + "..." # Csak az eleje, hogy ne szemetelje tele a logot
        }
        
        # Kiírjuk a logba szépen formázva
        xbmc.log("================= ADDON METAADAT ELLENŐRZÉS ================", level=xbmc.LOGINFO)
        for key, value in debug_info.items():
            # Kezeljük le, ha esetleg nincs adat (None)
            val_str = str(value) if value else "NINCS ADAT"
            xbmc.log(f"{key}: {val_str}", level=xbmc.LOGINFO)
        xbmc.log("=============================================================", level=xbmc.LOGINFO)
    else:
        xbmc.log("### DEBUG ###: Jelenleg nem fut videó.", level=xbmc.LOGINFO)

def get_html_content(url):
    """
    Letölti az adott HTML oldal tartalmát az URL paraméterben megadott webcímről és visszatér vele string típusként.

    Args:
        url: A weboldal címe aminek a HTML tartalmát szeretnénk visszakapni string típusként.

    Returns:
        string: A weboldal tartalma utf-8-as kódolású plain text-ben.

    Raises:
        ConnectionError: Ha a távoli szerver nem érhető el.
    """
    try:
        req = urllib.request.Request(url, headers=headers)
        response = urllib.request.urlopen(req)
        content = response.read().decode('utf-8', errors='ignore')
        return content
    except Exception as error:
        xbmc.log(f"Babel: A keresés hívása sikertelen: {error}", xbmc.LOGERROR)

def get_content_by_regex(html, regex, search_type):
    """
    Adott HTML tartalomból visszatér a RegEx által definiált tartalommal.
    Két keresési típust ismer: search - az első adott találatig megy a keresés és visszatér az eredménnyel. findall - minden a RegExnek megfelelő tartalommal visszatér.
    Args:
        html: A HTML tartalom amin a RegEx keresés végre kell hajtani.

        regex: A RegEx kifejezés ami alapján a keresést végre kell hajtani.

        search_type : A keresés típusa. Két értéket vehet fel. 'search' vagy 'findall' attól függően hogy csak az első előfordulást keressük a HTML-ben vagy at összeset.

    Returns:
        search esetén: match objektummal tér vissza.
        
        findall esetén: listával tér vissza

    Raises:
        None
    """
    if search_type == 'search':
        return re.search(regex, html, re.DOTALL)
    if search_type == 'findall':
        return re.findall(regex, html)

def search(media_title):
    """
    A tényleges film illetve sorozatcím keresése a https://feliratok.hu oldalon. Az itt kapott eredményt adódik át a download() függvénynek tényleges letöltésre.
    Args:
        media_title: Az éppen lejátszott média címe.

    Returns:
        None. A params_to_send változóba teszi be a download callback függvény számára szükséges infomrációkat, így amikor a felhasználó a listázott felirat nevére kattint a download() függvény hívódik meg.

    Raises:
        None
    """

    # A query string paramétereinek definiálása. Ebből állítjuk elő a keresési
    # URL-t amit majd meghívunk.

    http_query_params = {
        'search': media_title,
        'soriSorszam': '',
        'nyelv': '',
        'sorozatnev': '',
        'sid': '',
        'complexsearch': 'true',
        'knyelv': 0,
        'evad': '',
        'epizod1': '',
        'elotag': 0,
        'minoseg': 0,
        'rlsr': 0,
        'tab': 'all',
        'page': 1,
    }

    # Az ékezetes filmcím százalékos kódolása, hogy a webböngésző számára
    # értelmezhető legyen és a végleges keresési URL összeállítása.
    query_string = urlencode(http_query_params)
    url = main_link + f'/index.php?{query_string}'
  
    # A keresési URL logba írása, hogy lássuk pontosan mit hívunk meg
    xbmc.log(f"Babel: A Kodi által meghívott URL: {url}", xbmc.LOGINFO)
    
    # Az összeállított keresési URL meghívása és a weboldal válaszának
    # betöltése a 'html_content' változóba.
    html_content = get_html_content(url)

    # Ha a https:// feliratok.hu oldal karbantartás miatt ne melérhető akkor
    # azt jelzi egy felugró figyelmeztető üzenettel.
    if html_content == "Karbantartas, hamarosan jovunk vissza!":
        xbmc.log(f"Babel: A https://feliratok.eu karbantartás alatt.", xbmc.LOGINFO)
        xbmcgui.Dialog().notification(
            'Babel',                  # Címsor
            'A https://feliratok.eu karbantartás alatt.', # Üzenet
            xbmcgui.NOTIFICATION_WARNING,     # Ikon (sárga felkiáltójel)
            5000                              # Meddig látszódjon (ms) -> 5 mp
        )
    else:
        # Az eredmény oldalszámát egyre állítjuk.
        no_of_pages = 1

        # RegEx minta megadása az oldalak linkjének kinyerésére a HTML
        # tartalomból több oldalas találati lista esetére
        pagination_pattern=r'<div class="pagination">(.*?)</div>'
        pagination_snipet = get_content_by_regex(html_content, pagination_pattern, 'search')

        # Ha több oldal van és létezik a lapozáshoz szükséges HTML kódrészlet akkor kinyerjük a tartalmát és megszámoljuk a benne lévő linkeket. A
        # linkek száma fogja megmondani, hány oldalunk van pontosan. Az
        # összeset be kell dolgoznunk ha több oldal van. Ha nem létezik a
        # pagination HTML snipet akkor az oldal számláló marad 1. 
        if pagination_snipet:
            # A .group(1) adja vissza az első zárójelpár tartalmát
            pagination_content = pagination_snipet.group(1)

            # Kiszedjük a lapozás linkjeit a HTML tartalomból
            links = get_content_by_regex(pagination_content, r'<a\s+href=[^>]+>', 'findall')

            # Megszámoljuk a linkeket. Ennyi oldalunk van.
            no_of_pages = len(links)

        # Az oldalak számát kiírjuk a logba ellenőrzés céljából
        xbmc.log(f"Babel: Felirat oldalak száma: {no_of_pages}", xbmc.LOGINFO)

        # Végigmegyünk az összes oldalon és a 'matches' változób tesszük az
        # összes felirat nyelvét, címét és letöltési URL-jét. A 'matches'
        # változót létre kell hoznunk előre mert a ciklusban már hozzá
        # szeretnénk fűzni és ahhoz már léteznie kell.
        matches = list()

        for i in range(1, no_of_pages + 1):

            # RegEx minta megadása a film nyelvének, címének és a letöltési linknek a kinyerésére.
            pattern = r'<tr id="vilagit".*?<small>(.*?)</small>.*?class="magyar">(.*?)</div>.*?href="([^"]*?action=letolt[^"]*)"'

            # A nyelv, címek és linkek kinyerése a válasz HTML-ből
            matches += re.findall(pattern, html_content, re.DOTALL)

            # Találati oldalszám növelése és a következő oldal HTML tartalmának
            # lekérése, majd a film nyelvének, címének és letöltési URL-jének a
            # kinyerése a következő ciklus körben.
            http_query_params['page'] = i + 1
            query_string = urlencode(http_query_params)
            url = main_link + f'/index.php?{query_string}'
            html_content = get_html_content(url)


        # Az addonhoz tartozó Kodi folyamat azonosító lekérése
        handle = int(sys.argv[1])
        xbmcplugin.setContent(handle, 'subtitles')

        # Beállítjuk minden visszaadott felirat nyelvét, címét és letöltési
        # URL-jét.

        for lang, title_html, download_link in matches:
            # Megfelelő zászló ikon rövidítésének beállítása
            v_flag = languages[lang]

            # Film címének beállítása
            clean_title = re.sub(r'<[^>]*>', '', title_html).strip()
            
            # Letöltési link beállítása
            clean_link = download_link.replace('&amp;', '&')
            full_url = main_link + clean_link if clean_link.startswith('/') else clean_link

            if clean_title:
                # Az egyes feliratokhoz tartozó értékek átadása a Kodinak.
                # Ezek a list_itemek lesznek láthatók a felirat legördülő
                # listában.
                list_item = xbmcgui.ListItem(label=clean_title, label2=clean_title)
                
                # Beállítjuk a zászlót ikonnak és bélyegképnek
                list_item.setArt({
                    'icon': v_flag,
                    'thumb': v_flag
                }) 
                
                # Megfelelő feliratnyelv beállítása
                list_item.setProperty("Language", languages[lang])
                
                try:
                    info_tag = list_item.getVideoInfoTag()
                    info_tag.setTitle(clean_title)
                except:
                    list_item.setInfo('video', {'title': clean_title})

                # A params-ba beletesszük a címet is, hogy a download függvény
                # lássa.
                params_to_send = {
                    'action': 'download',
                    'url': full_url,
                    'title': clean_title
                }
                callback_url = f"{sys.argv[0]}?{urlencode(params_to_send)}"
                
                xbmcplugin.addDirectoryItem(handle, callback_url, list_item, isFolder=False)

        xbmcplugin.endOfDirectory(handle)

def download(url):
    """
    A serch() függvényben kiválasztott feliratot tölti le és adja át a Kodi számára.
    Args:
        url: A serch() függvény által visszaadott felirat URL-je amire a felhasználó kattint a felirat kiválasztásakor.

    Returns:
        None.

    Raises:
        Exception: Ha bármi hiba adódik a letöltéssel azt a kodi.log-ba írja. 
    """
    # A Kodi által küldött célútvonal lekérése
    dest_path = params.get('destfile')
    
    # Ha nincs megadva (pl. kézi teszteléskor), csinálunk egyet a temp mappába
    if not dest_path:
        temp_dir = xbmcvfs.translatePath('special://temp')
        dest_path = os.path.join(temp_dir, 'felirat.srt')

    xbmc.log(f"Babel: Közvetlen SRT letöltés: {url} -> {dest_path}", xbmc.LOGINFO)

    try:
        # User-Agent itt is fontos, mert a szerver blokkolhatja az alap Python
        # kérést. Megpróbáljuk letölteni a kiválasztott feliratot.
        req = urllib.request.Request(url, headers=headers)
        
        with urllib.request.urlopen(req) as response:
            data = response.read()
            
            # Közvetlen kiírás a célfájlba (bináris módban 'wb' vagy
            # xbmcvfs-sel). Az xbmcvfs.File a legbiztosabb minden platformon (
            #Android/Windows/Linux)
            with xbmcvfs.File(dest_path, 'w') as target:
                success = target.write(data)
            
            if success:
                xbmc.log("Babel: Felirat sikeresen mentve.", xbmc.LOGINFO)
                
                # Nagyon fontos: Jeleznünk kell a Kodinak, hogy a fájl készen
                # áll! Ehhez a letöltött fájl útvonalát kell hozzáadni a
                # könyvtárhoz.
                list_item = xbmcgui.ListItem(label="Felirat")
                xbmcplugin.addDirectoryItem(int(sys.argv[1]), dest_path, list_item)
                return True
                
    except Exception as e:
        xbmc.log(f"Babel: Hiba a közvetlen letöltésnél: {e}", xbmc.LOGERROR)
        xbmcgui.Dialog().notification("Babel Hiba", "Nem sikerült a felirat letöltése.")
    
    return False

# Fő vezérlés
if __name__ == '__main__':

    # Paraméterek kinyerése a Kodi által használt sys.argv[2]-ből
    # A [1:] levágja a kezdő kérdőjelet (?)
    param_string = sys.argv[2][1:] if len(sys.argv) > 2 else ""
    
    # A paraméter stringet szótárrá (dict) alakítjuk, így a 'searchstring' és
    # a 'resume' külön kulcsok lesznek.
    params = dict(parse_qsl(param_string))

    # Az action lekérése (action: manuális vagy automatikus keresés)
    action = params.get('action')
    
    xbmc.log(f"Babel Log: Kapott action: {action}", xbmc.LOGDEBUG)

    # Keresési logika kezelése (automata és manuális)
    if action == 'search' or action == 'manualsearch':
        
        if action == 'manualsearch':
            # Manuális keresésnél a user által beírt szöveget használjuk
            # A parse_qsl miatt itt már NEM lesz benne a 'resume:false' plusz
            # string amit a Kodi néha hozzáfűz az átadott keresendő szöveghez.
            query = params.get('searchstring', '')
            xbmc.log(f"Babel Log: Manuális keresés indítása: {query}", xbmc.LOGINFO)
        else:
            # Automata keresésnél a lejátszott fájl címe az irányadó
            query = xbmc.getInfoLabel("VideoPlayer.Title")
            xbmc.log(f"Babel Log: Automata keresés indítása: {query}", xbmc.LOGINFO)

        # Ha van keresendő szöveg, meghívjuk a kereső függvényt
        if query:
            search(query)
        else:
            xbmc.log("Babel Log: Hiba - üres keresési kulcsszó!", xbmc.LOGERROR)

    # Letöltési logika kezelése
    elif action == 'download':
        download_url = params.get('url')
        if download_url:
            download(download_url)
        else:
            xbmc.log("Babel Log: Hiba - hiányzó letöltési URL!", xbmc.LOGERROR) 