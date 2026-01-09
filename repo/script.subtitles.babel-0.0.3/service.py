 #!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Kodi subtitle addon for the https://feliratok.eu subtitle webpage

Allows subtitle downloads for movies and tv series from https://feliratok.eu
"""

__author__ = "g0m3z"
__copyright__ = "Copyright 2026, Babel subtitle addon for Kodi"
__license__ = "GNU GPLv2"
__version__ = "0.0.3"
__maintainer__ = "g0m3z"
__email__ = "g0m3z78 [at] googel's email service"
__status__ = "Beta"

# Importing required Python modules

import os
import sys
import xbmcgui
import xbmcplugin
import xbmc
import xbmcvfs
from urllib.parse import parse_qsl
from urllib.parse import urlencode
import urllib.request

# Using the 're' module to collect data from HTML pages because it's part of
# the basic Python package, thus no dependecy installation is required and
# provides compatibility with older Kodi versions also

import re
import io

# Creating dict with ISO language equivalents

languages = {
    "Albán": "sq",
    "Angol": "en",
    "Arab": "ar",
    "Bolgár": "bg",
    "Brazíliai portugál": "pt-br",
    "Cseh": "cs",
    "Dán": "da",
    "Finn": "fi",
    "Flamand": "nl",  # A version of Dutch
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

# Storing the main URL in a variable for easier use..
main_link = "https://feliratok.eu"

# Defining a User-Agent to avoid banning the script from https://feliratok.eu

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

def log_netmozi_metadata():
    """
    Examines the metadata of the media currently played by Kodi. If those are available (such as the series and episode number) the subtitle can be searched on a more precise way. This function is not in use yet but required for upcoming release

    Args:
        None

    Returns:
        None. Writes the result to the kodi.log file

    Raises:
        None
    """

    # Checking if the media is playing
    if xbmc.Player().isPlayingVideo():
        # Getting the actual tags
        tag = xbmc.Player().getVideoInfoTag()
        
        # Collecting the required data into a dictionary
        debug_info = {
            "### DEBUG TITLE ###": tag.getTitle(),
            "### DEBUG MEDIATYPE ###": tag.getMediaType(),
            "### DEBUG TVSHOW ###": tag.getTVShowTitle(),
            "### DEBUG SEASON ###": tag.getSeason(),
            "### DEBUG EPISODE ###": tag.getEpisode(),
            "### DEBUG IMDB ID ###": tag.getIMDBNumber(),
            "### DEBUG PLOT ###": tag.getPlot()[:50] + "..." # Getting the first 50 char of the plot not to spam the kodi.log.
        }
        
        # Writing into the kodi.log on a formatted way
        xbmc.log("================= BABEL META DATA CHECK ====================", level=xbmc.LOGINFO)
        for key, value in debug_info.items():
            # If there's no data then it's mentioned in the log also.
            val_str = str(value) if value else "NO DATA"
            xbmc.log(f"{key}: {val_str}", level=xbmc.LOGINFO)
        xbmc.log("=============================================================", level=xbmc.LOGINFO)
    else:
        xbmc.log("### DEBUG ###: No media is played.", level=xbmc.LOGINFO)

def get_html_content(url):
    """
    Retrieves the HTML content of the given URL as a plain text

    Args:
        url: URL of the webpage for whose content is required

    Returns:
        string: Plain text content of the webpage decoded in utf-8

    Raises:
        ConnectionError: If the website is not responding.
    """
    try:
        req = urllib.request.Request(url, headers=headers)
        response = urllib.request.urlopen(req)
        content = response.read().decode('utf-8', errors='ignore')
        return content
    except Exception as error:
        xbmc.log(f"Babel: Connection error: {error}", xbmc.LOGERROR)

def get_content_by_regex(html, regex, search_type):
    """
    Retrieves data from the given HTML page defined by the regular expression. It uses two search types: search - retrieves the first instance found by the RegEx; findall - retrieves all instances found by the RegEx
    Args:
        html: The HTML content on which the RegEx should be applied

        regex: The regular expression based on the serch should be executed on the HTML content

        search_type : Type of the search. It accepts two values:

            search - retrieves the first instance found by the RegEx

            findall - retrieves all instances found by the RegEx

    Returns:
        in case of search: match object
        
        in case of findall: list()

    Raises:
        None
    """
    if search_type == 'search':
        return re.search(regex, html, re.DOTALL)
    if search_type == 'findall':
        return re.findall(regex, html)

def search(media_title):
    """
    Actual subtitle serach of the media on the https://feliratok.hu website. Result of this search is handed over to the download() function which executes the actual subtitle download.

    Args:
        media_title: Title of the media currently played or the search term submitted by the user through the 'Manual search' option from Kodi

    Returns:
        None. Prepares a 'params_to_send' variable that contains all neccessary information for the download callback function. If the user clicks on a particular subtitle listed on the Kodi result window this variable is haded over to the download() function

    Raises:
        None
    """

    # Defining parameters of the query string that is used to complie the final URL that is called for the web search

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

    # If the media title contains special characters percent coding is
    # required to make the final query URL interpretable for
    # https://feliratok.eu website
    query_string = urlencode(http_query_params)
    url = main_link + f'/index.php?{query_string}'
  
    # Writing the final search URL to log to see what is submitted to the
    # website
    xbmc.log(f"Babel: Search URL called by Kodi: {url}", xbmc.LOGINFO)
    
    # Getting the HTML response of the search URL from https//feliratok.eu
    html_content = get_html_content(url)

    # If the https://feliratok.hu is down becasue of maintenance it's written
    # in the kodi.log and a short notice is provided in a Kodi pop-up window
    # also
    if html_content == "Karbantartas, hamarosan jovunk vissza!":
        xbmc.log(f"Babel: https://feliratok.eu is under maintenance.", xbmc.LOGINFO)
        xbmcgui.Dialog().notification(
            'Babel',                  # Title
            'https://feliratok.eu is under maintenance.', # Message
            xbmcgui.NOTIFICATION_WARNING,     # Icon (yellow exclamation mark)
            5000                              # Message appearance time -> 5 mp
        )
    else:
        # Setting the number of result pages to 1
        no_of_pages = 1

        # Collecting the links of pagination pages in case of multipage result
        pagination_pattern=r'<div class="pagination">(.*?)</div>'
        pagination_snipet = get_content_by_regex(html_content, pagination_pattern, 'search')

        # Search for the pagination HTML snipet. If the serch returns with
        # multipage results we count how many pagination links can be found in
        # it as all should be processed by setting the count of the 'page:'
        # paramtere of the 'http_query_params' string to parse all of the 
        # result pages. If the pagination snipet doesn't exist the 
        # 'no_of_pages' variable stays 1
        if pagination_snipet:
            # .group(1) returns the content of the first parenthesis pair
            pagination_content = pagination_snipet.group(1)

            # Getting the links of pagination from the HTML content
            links = get_content_by_regex(pagination_content, r'<a\s+href=[^>]+>', 'findall')

            # Counting the no. of links. This gives us the number of result
            # pages
            no_of_pages = len(links)

        # Writing no. of pages to the log for control check purpose
        xbmc.log(f"Babel: Felirat oldalak száma: {no_of_pages}", xbmc.LOGINFO)

        # Iterating through all the result pages and collecting the flag,
        # title and download URL of all subtitles. 'matches' variable should be
        # created in advance as we are adding additional content to it 
        # iteration by iteration
        matches = list()

        for i in range(1, no_of_pages + 1):

            # Provising RegEx pattern to get the flag, title and download URL
            # of the subtitle
            pattern = r'<tr id="vilagit".*?<small>(.*?)</small>.*?class="magyar">(.*?)</div>.*?href="([^"]*?action=letolt[^"]*)"'

            # Getting the flag, title and download URL from the response HTML
            # and adding it to the 'matches' variable
            matches += re.findall(pattern, html_content, re.DOTALL)

            # Increasing the count of the 'page' parameter in the 
            #'http_query_params' query string and downloading and parsing the
            # next result page. After that getting the flag, title and
            # download URL of all the subtitles on the page in the next
            # iteration
            http_query_params['page'] = i + 1
            query_string = urlencode(http_query_params)
            url = main_link + f'/index.php?{query_string}'
            html_content = get_html_content(url)


        # Querying the Kodi process ID of the addon
        handle = int(sys.argv[1])
        xbmcplugin.setContent(handle, 'subtitles')

        # Setting the flag, title and download URL of all returned subtitles
        for lang, title_html, download_link in matches:
            # Setting the proper flag icon based on the 'languages'
            # translation dict defined at the beginning of this code
            v_flag = languages[lang]

            # Setting title of subtitle
            clean_title = re.sub(r'<[^>]*>', '', title_html).strip()
            
            # Setting the download link of the subtitle
            clean_link = download_link.replace('&amp;', '&')
            full_url = main_link + clean_link if clean_link.startswith('/') else clean_link

            if clean_title:
                # Handing over the final list of subtiles with all
                # supplementary information to Kodi. These 'list_items' appear
                # in the result dropdown list of Kodi
                list_item = xbmcgui.ListItem(label=clean_title, label2=clean_title)
                
                # Setting the flag as icon and thumbnail
                list_item.setArt({
                    'icon': v_flag,
                    'thumb': v_flag
                }) 
                
                # Setting the appropriate subtitle language
                list_item.setProperty("Language", languages[lang])
                
                try:
                    info_tag = list_item.getVideoInfoTag()
                    info_tag.setTitle(clean_title)
                except:
                    list_item.setInfo('video', {'title': clean_title})

                # Adding title of subtitle to the 'params_to_send' variable to
                # make it visible for the download() function
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
    Downloads the subtile selected from the Kodi dorpdown list provided by the search() function

    Args:
        url: Download URL of the subtitle provided by the search() function and selected by the end user

    Returns:
        None.

    Raises:
        Exception: If nay excpetion occures during the download the function writes it to the kodi.log
    """
    # Getting the destination file path provided by Kodi
    dest_path = params.get('destfile')
    
    # If the destiantion file path doesn't exist we create one into the 'temp'
    # folder
    if not dest_path:
        temp_dir = xbmcvfs.translatePath('special://temp')
        dest_path = os.path.join(temp_dir, 'felirat.srt')

    xbmc.log(f"Babel: Direct SRT download: {url} -> {dest_path}", xbmc.LOGINFO)

    try:
        # Defining a User-Agent to avoid banning the script from
        # https://feliratok.eu
        req = urllib.request.Request(url, headers=headers)
        
        with urllib.request.urlopen(req) as response:
            data = response.read()
            
            # Writing directly to the destiantion file on a binary way or with
            # xbmcvfs. xbmcvfs.File is the most reliable format on every
            # platform (Android/Windows/Linux)
            with xbmcvfs.File(dest_path, 'w') as target:
                success = target.write(data)
            
            if success:
                xbmc.log("Babel: Subtitle saved successfully.", xbmc.LOGINFO)
                
                # Important! We have to notify Kodi that the subtitle file is
                # ready. For this we have to add the path of the downloaded
                # subtitle file to the directory
                list_item = xbmcgui.ListItem(label="Felirat")
                xbmcplugin.addDirectoryItem(int(sys.argv[1]), dest_path, list_item)
                return True
                
    except Exception as e:
        xbmc.log(f"Babel: Error with direct downlad: {e}", xbmc.LOGERROR)
        xbmcgui.Dialog().notification("Babel Error", "Couldn't download subtitle file.")
    
    return False

# Main function
if __name__ == '__main__':

    # Getting parameters from sys.argv[2] used by Kodi
    # [1:] cuts the questionmark (?) at the beginning
    param_string = sys.argv[2][1:] if len(sys.argv) > 2 else ""
    
    # Transforming the parameter string to dict, thus 'searchstring' and
    # 'resume' become separate keys
    params = dict(parse_qsl(param_string))

    # Getting the action (action: auto or manual search)
    action = params.get('action')
    
    xbmc.log(f"Babel Log: Action type: {action}", xbmc.LOGDEBUG)

    # Manage search logic (auto and manual)
    if action == 'search' or action == 'manualsearch':
        
        if action == 'manualsearch':
            # In case of manual search we use the search string provided by
            # the end-user. Sometimes Kodi adds the 'resume:false' string to
            # the search string hence 'parse_qsl' used above removes this 
            # unnecssary text.
            query = params.get('searchstring', '')
            xbmc.log(f"Babel Log: Initiating manual search: {query}", xbmc.LOGINFO)
        else:
            # In case of auto search the title of the media provided by Kodi is used for the search
            query = xbmc.getInfoLabel("VideoPlayer.Title")
            xbmc.log(f"Babel Log: Initiating auto search: {query}", xbmc.LOGINFO)

        # If serch string is provided we call the search() function with it
        if query:
            search(query)
        else:
            xbmc.log("Babel Log: Error - Empty search phrase!", xbmc.LOGERROR)

    # Managing download logic
    elif action == 'download':
        download_url = params.get('url')
        if download_url:
            download(download_url)
        else:
            xbmc.log("Babel Log: Error - Missing download URL!", xbmc.LOGERROR) 