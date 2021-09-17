# coding=utf-8
# Copyright (C) 2017 hubsif (hubsif@gmx.de)
#
# This program is free software; you can redistribute it and/or modify it under the terms
# of the GNU General Public License as published by the Free Software Foundation;
# either version 2 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program;
# if not, see <http://www.gnu.org/licenses/>.

##############
# preparations
##############

import xbmc, xbmcplugin, xbmcgui, xbmcaddon
import os, sys, re, json, string, random, time
import xml.etree.ElementTree as ET
import urllib.parse as urllib
#import urllib2
import urllib.request
import urllib.error
#import urlparse
import urllib.parse as urlparse
import time
#import md5
import hashlib as md5
from datetime import datetime, timedelta
from random import randint
from hashlib import sha256
from re import search
import importlib

importlib.reload(sys)
#sys.setdefaultencoding('utf8')

_addon_id      = 'plugin.video.telekomsport'
_addon         = xbmcaddon.Addon(id=_addon_id)
_addon_name    = _addon.getAddonInfo('name')
_addon_handler = int(sys.argv[1])
_addon_url     = sys.argv[0]
_addon_path    = xbmc.translatePath(_addon.getAddonInfo("path") )
__language__   = _addon.getLocalizedString
#_icons_path    = _addon_path + "/resources/icons/"
#_fanart_path   = _addon_path + "/resources/fanart/"

xbmcplugin.setContent(_addon_handler, 'episodes')

base_url = "https://www.magentasport.de"
base_api = "/api/v" # + str(api_version) # wird unten angefügt
base_image_url = "https://www.magentasport.de"
oauth_url = "https://accounts.login.idm.telekom.com/oauth2/tokens"
jwt_url = "https://www.magentasport.de/service/auth/app/login/jwt"
stream_url = "https://www.magentasport.de/service/player/v2/streamAccess"
main_page = "/navigation"
schedule_url = "/components/programm/18"
#schedule_url = "/epg/28" # alt
api_salt = '55!#r%Rn3%xn?U?PX*k'
accesstoken = ''
api_version = 0

###########
# functions
###########

# helper functions

def build_url(query):
    return _addon_url + '?' + urlparse.urlencode(query)

def prettydate(dt, addtime=True):
    dt = dt + utc_offset()
    if addtime:
        return dt.strftime(xbmc.getRegion("datelong") + ", " + xbmc.getRegion("time").replace(":%S", "").replace("%H%H", "%H"))
    else:
        return dt.strftime(xbmc.getRegion("datelong"))

def prettytime(dt, addtime=True):
    dt = dt + utc_offset()
    if addtime:
        return dt.strftime(xbmc.getRegion("time").replace(":%S", "").replace("%H%H", "%H"))
    else:
        return "xx:xx"

def utc_offset():
    ts = time.time()
    return (datetime.fromtimestamp(ts) - datetime.utcfromtimestamp(ts))

def get_jwt(username, password):
    data = { "claims": "{'id_token':{'urn:telekom.com:all':null}}", "client_id": "10LIVESAM30000004901TSMAPP00000000000000", "grant_type": "password", "scope": "tsm offline_access", "username": username, "password": password }
    #xbmc.log("hieradf: "+str(urllib.request.Request(oauth_url, urllib.parse.urlencode(data), {'Content-Type': 'application/json'})).read())
    response = urllib.request.urlopen(urllib.request.Request(oauth_url, urllib.parse.urlencode(data).encode(), {'Content-Type': 'application/json'})).read()
    jsonResult = json.loads(response)

    if 'access_token' in jsonResult:
        response = urllib.request.urlopen(urllib.request.Request(jwt_url, json.dumps({"token": jsonResult['access_token']}).encode(), {'Content-Type': 'application/json'})).read()
        jsonResult = json.loads(response)
        if 'status' in jsonResult and jsonResult['status'] == "success" and 'data' in jsonResult and 'token' in jsonResult['data']:
            return jsonResult['data']['token']

def generate_hash256(text):
    return sha256(text.encode('utf-8')).hexdigest()

def urlopen(urlEnd, *args):
    eventTreeIDUebergabe = ''
    for ar in args:
        if eventTreeIDUebergabe == '':
            eventTreeIDUebergabe = ar + '&'
            break

    response = ''
    if api_version == 3:
        utc = int(
            ((datetime.now() - timedelta(hours=5)).replace(hour=0, minute=0, second=0, microsecond=0) - datetime(1970,
                                                                                                                 1,
                                                                                                                 1)).total_seconds())
        accesstoken = generate_hash256('{0}{1}{2}'.format(api_salt, utc, base_api + urlEnd))
        xbmc.log('Token erzeugt für '+str(base_api + urlEnd))
        #xbmc.log('hier000 ' + str(base_url + base_api + urlEnd + '?' + eventTreeIDUebergabe + 'token=' + accesstoken))
        response = urllib.request.urlopen(base_url + base_api + urlEnd + '?' + eventTreeIDUebergabe + 'token=' + accesstoken).read()
    else:
        response = urllib.request.urlopen(base_url + base_api + urlEnd).read()
        #xbmc.log('hier000 ' + str(base_url + base_api + urlEnd))

    #xbmc.log('hier111 ' + str(response))
    return response

def doppelterBodenLiveEvent():
    #xbmc.log('Ich gehe hier durch: doppelterBodenLiveEvent')
    counterLive = 0
    liveevent = False
    ausgabeCounterLive1 = ''
    schedule = json.loads(urlopen(schedule_url))
    for datas in schedule['data']['data']:
        url = ""
        # schauen ob Liveevent vorhanen:
        for slots in datas['slots']:
            scheduled_start = datetime.utcfromtimestamp(int(slots['slot_time']['utc_timestamp']))
            for events in slots['events']:
                if not events['type'] == 'fcbEvent' or events['metadata']['name'][:4] == 'LIVE':
                    scheduled_start = datetime.utcfromtimestamp(
                        int(events['metadata']['scheduled_start']['utc_timestamp']))

                    if (slots['is_live'] or events['metadata']['state'] == 'live') and not events['metadata']['state'] == 'canceled':
                        counterLive = counterLive + 1
                        ausgabeCounterLive1 = events['metadata']['name'] + " (" + events['metadata'][
                            'description_bold'] + ' - ' + events['metadata']['description_regular'] + ')'
                        liveevent = True

    if liveevent:
        ueberschrift = ''
        if counterLive == 1:
            ueberschrift = '[B]' + __language__(30004) + ': [/B]' + ausgabeCounterLive1
        else:
            ueberschrift = '[B]' + __language__(30004) + ': [/B]' + str(counterLive) + ' Events'

        url = build_url({'mode': 'EPG', 'onlyLiveYesNo': '1'})
        li = xbmcgui.ListItem(ueberschrift)
        xbmcplugin.addDirectoryItem(handle=_addon_handler, url=url, listitem=li, isFolder=True)

def doppelterBodenFCBayernTVlive\
                (jsonResult):
    #xbmc.log('Ich gehe hier durch: doppelterBodenFCBayernTVlive')
    erstesEvent = False
    for content in jsonResult['data']['league_filter']:
        if content['title'].lower() == 'fc bayern.tv live':
            jsonFCBayern = json.loads(urlopen(content['target']))
            for header in jsonFCBayern['data']['navigation']['header']:
                if header['title'].lower() == 'programm':
                    url = build_url({'mode': header['target_type'], 'eventLane': header['target'], 'event_tree_id': str(content['event_tree_id']), 'title': content['title']})
                    jsonFCBayern = json.loads(urlopen(header['target'], 'eventTreeId='+str(content['event_tree_id'])))
                    for slots in jsonFCBayern['data']['content'][0]['group_elements'][0]['data'][0]['slots']:
                        if slots['is_live']:
                            if erstesEvent == False:
                                scheduled_end = datetime.utcfromtimestamp(
                                    int(slots['events'][0]['metadata']['scheduled_end']['utc_timestamp']))
                                ausgabe = slots['events'][0]['metadata']['title']
                                li = xbmcgui.ListItem('[B]FC Bayern.tv live:[/B] ' + ausgabe + ' (bis ' + str(
                                    prettytime(scheduled_end)) + ' Uhr) [B](24/7-Programm)[/B]')
                                li.setArt({'icon': base_image_url + slots['events'][0]['metadata']['images']['editorial']})
                                xbmcplugin.addDirectoryItem(handle=_addon_handler, url=url, listitem=li,
                                                            isFolder=True)
                                erstesEvent = True
                                break

                    #kein Event gefunden
                    if erstesEvent == False:
                        ausgabe = ''
                        li = xbmcgui.ListItem('[B]FC Bayern.tv live:[/B] keine Programminfo verfügbar - starte Livestream hier [B](24/7-Programm)[/B]')
                        li.setArt({'icon': base_image_url + slots['events'][0]['metadata']['images']['editorial']})
                        xbmcplugin.addDirectoryItem(handle=_addon_handler, url=url, listitem=li,
                                                    isFolder=True)
# plugin call modes
def getMain():

    jsonResult = json.loads(urlopen(main_page))
    jsonLive = json.loads(urlopen(jsonResult['data']['main']['target']))
    if api_version == 3:
        #hier noch live richtig einfügen
        doppelterBodenLiveEvent()
        doppelterBodenFCBayernTVlive(jsonResult)
    else:
        # get currently running games
        counterLive = 0
        liveevent = False
        ausgabeCounterLive1 = 'tbd'
        for content in jsonLive['data']['content']:
            if content['title'] == 'Live':
                for group_element in content['group_elements']:
                    if group_element['type'] == "eventLane":
                        for data in group_element['data']:
                            if data['metadata']['state'] == 'live':
                                liveevent = True
                                counterLive = counterLive + 1
                                ausgabeCounterLive1 = data['metadata']['name']+" ("+data['metadata']['description_bold'] + ' - ' + data['metadata']['description_regular']+')'

        if liveevent:
            url = build_url({'mode': group_element['type'], group_element['type']: group_element['data_url'], 'onlylive': True})
            ueberschrift = ''
            if counterLive == 1:
                ueberschrift = '[B]' + __language__(30004) + ': [/B]'+ausgabeCounterLive1
            else:
                ueberschrift = '[B]' + __language__(30004) + ': [/B]'+str(counterLive)+' Events'
            li = xbmcgui.ListItem(ueberschrift)
            li.setArt({'icon': jsonLive['data']['metadata']['web']['image']})
            xbmcplugin.addDirectoryItem(handle=_addon_handler, url=url, listitem=li, isFolder=True)
        else:
            #doppelter Boden, falls es davor nicht klappt
            doppelterBodenLiveEvent()

        #--------------------------------------------------------------------------------
        erstesEvent = False
        for content in jsonLive['data']['content']:
            if content['title'] == 'FC Bayern.tv live':
                for group_element in content['group_elements']:
                    if group_element['type'] == "eventLane":
                        liveevent = False
                        for data in group_element['data']:
                            ausgabe = data['metadata']['name']

                            #.decode('ascii', 'ignore')
                            #if data['metadata']['name'][:5] == 'LIVE:':
                             #   liveevent = True

                            if erstesEvent == False:
                                url = build_url({'mode': group_element['type'], group_element['type']: group_element['data_url']})
                                li = xbmcgui.ListItem('[B]FC Bayern.tv live:[/B] '+ausgabe+ ' [B](24/7-Programm)[/B]')
                                li.setArt({'icon': jsonLive['data']['metadata']['web']['image']})
                                xbmcplugin.addDirectoryItem(handle=_addon_handler, url=url, listitem=li, isFolder=True)
                                erstesEvent = True
                                break

        if erstesEvent == False:
            #doppelter Boden: noch anderweitig die Daten herbekommen:
            doppelterBodenFCBayernTVlive(jsonResult)

    url = build_url({'mode': 'EPG', 'onlyLiveYesNo': '0'})
    li = xbmcgui.ListItem('[B]Programmvorschau[/B] (nächste Liveevents)')
    xbmcplugin.addDirectoryItem(handle=_addon_handler, url=url, listitem=li, isFolder=True)

    for content in jsonResult['data']['league_filter']:
        url = build_url({'mode': content['target_type'], content['target_type']: content['target'], 'event_tree_id': content['event_tree_id']})
        li = xbmcgui.ListItem(content['title'])
        li.setArt({'icon': base_image_url + content['logo']})
        xbmcplugin.addDirectoryItem(handle=_addon_handler, url=url, listitem=li, isFolder=True)

    url = build_url({'mode': ''})
    li = xbmcgui.ListItem('--- Info: Api-Version: V'+str(api_version) + ' ---')
    xbmcplugin.addDirectoryItem(handle=_addon_handler, url="", listitem=li, isFolder=True)

    xbmcplugin.endOfDirectory(_addon_handler)

def createEPG(datas, onlyLiveYesNo, bereitsangelegtnurLive, bereitsangelegtnurLiveInfo, bayernTVAll):
    #onlyLiveYesNo
    #0: alles
    #1: nur live
    scheduled_start_Vorgaenger = ''
    eventStreamLink = ''
    url = ""
    for slots in datas['slots']:
        scheduled_start = datetime.utcfromtimestamp(int(slots['slot_time']['utc_timestamp']))
        for events in slots['events']:
            if not events['metadata']['state'] == 'post':
                if not events['type'] == 'fcbEvent' or events['metadata']['name'][:4] == 'LIVE' or bayernTVAll:
                    scheduled_start = datetime.utcfromtimestamp(
                        int(events['metadata']['scheduled_start']['utc_timestamp']))
                    if not scheduled_start_Vorgaenger == prettydate(scheduled_start, False):
                        if not bereitsangelegtnurLiveInfo:
                            li = xbmcgui.ListItem(
                                "Hinweis: Falls ein Livestream nicht startet bitte via der Ligaauswahl auf der Startseite starten!")
                            xbmcplugin.addDirectoryItem(handle=_addon_handler, url=url, listitem=li,
                                                        isFolder=True)
                            li = xbmcgui.ListItem(
                                "Hinweis: Falls der Stream kein Livebild zeigt: Livestream vorspulen!")
                            xbmcplugin.addDirectoryItem(handle=_addon_handler, url=url, listitem=li,
                                                        isFolder=True)
                            bereitsangelegtnurLiveInfo = True

                        if (onlyLiveYesNo == '1' and not bereitsangelegtnurLive) or onlyLiveYesNo == '0':
                            li = xbmcgui.ListItem("[COLOR gold]" + prettydate(scheduled_start, False) + "[/COLOR]")
                            xbmcplugin.addDirectoryItem(handle=_addon_handler, url=url, listitem=li,
                                                        isFolder=True)
                            scheduled_start_Vorgaenger = prettydate(scheduled_start, False)
                            bereitsangelegtnurLive = True

                    url = ""
                    eventinfo = events['metadata']['description_bold'] + ' - ' + events['metadata'][
                        'description_regular']

                    if events['metadata']['state'] == 'live' or slots['is_live']:
                        title = ''
                        if events['metadata']['state'] == 'canceled':
                            title = __language__(30030) + " - "
                        title = title + __language__(30004) + ': ' + events['metadata']['name']
                        eventinfo = events['metadata']['description_bold'] + ' - ' + events['metadata'][
                            'description_regular']

                        li = xbmcgui.ListItem('[B]' + title + '[/B] (' + eventinfo + ')')
                        li.setArt({'icon': base_image_url + events['metadata']['images']['editorial']})
                        li.setProperty('icon',
                                       base_image_url + events['metadata']['images']['editorial'])
                        li.setInfo('video', {'plot': prettydate(scheduled_start)})
                        li.setProperty('IsPlayable', 'true')
                        li.setInfo('video', {})
                        url = build_url({'mode': 'event', 'event': str(events['target']) + '/' + str(
                            events['metadata']['active_video_id']), 'live': True})

                        xbmcplugin.addDirectoryItem(handle=_addon_handler, url=url, listitem=li)

                    else:
                        if onlyLiveYesNo == '0':
                            title = ''
                            if events['metadata']['state'] == 'canceled':
                                title = __language__(30030) + " - "
                            title = title + str(prettytime(scheduled_start)) + " Uhr: " + events['metadata']['name']
                            li = xbmcgui.ListItem('[B]' + title + '[/B] (' + eventinfo + ')')
                            li = xbmcgui.ListItem('[B]' + title + '[/B] (' + eventinfo + ')')
                            li.setArt({'icon': base_image_url + events['metadata']['images']['editorial']})
                            li.setInfo('video', {'plot': prettydate(scheduled_start)})
                            xbmcplugin.addDirectoryItem(handle=_addon_handler, url=url, listitem=li)

def getEPG():
    #onlyLiveYesNo
    #0: alles
    #1: nur live
    bereitsangelegtnurLive = False
    bereitsangelegtnurLiveInfo = False
    schedule = json.loads(urlopen(schedule_url))

    for datas in schedule['data']['data']:
        createEPG(datas, args['onlyLiveYesNo'][0], bereitsangelegtnurLive, bereitsangelegtnurLiveInfo, False)
        bereitsangelegtnurLive = True
        bereitsangelegtnurLiveInfo = True

    xbmcplugin.endOfDirectory(_addon_handler)

def getstandings():
    xbmcgui.Dialog().ok(_addon_name, 'Tabellenfunktion wird noch nicht unterstützt')
    xbmcplugin.setResolvedUrl(_addon_handler, False, xbmcgui.ListItem())

def getschedule():
    title = "[B][COLOR gold]" + args['title'] + " Spielplan:[/COLOR][/B]"
    url = ''
    li = xbmcgui.ListItem(title)
    xbmcplugin.addDirectoryItem(handle=_addon_handler, url=url, listitem=li, isFolder=True)

    if args['event_tree_id'] == '':
        eventTreeID_Uebergabe = ''
    else:
        eventTreeID_Uebergabe = 'eventTreeId=' + args['event_tree_id']
    program = json.loads(urlopen(args['eventLane'], eventTreeID_Uebergabe))
    bereitsangelegtnurLive = False
    bereitsangelegtnurLiveInfo = False
    #xbmc.log('adgadsg' + str(args['eventLane']))

    for datas in program['data']['epg']['elements']:
        createEPG(datas, '0', bereitsangelegtnurLive, bereitsangelegtnurLiveInfo, False)
        bereitsangelegtnurLive = True
        bereitsangelegtnurLiveInfo = True

    xbmcplugin.endOfDirectory(_addon_handler)

def getprogram():
    title = "[B][COLOR gold]" + args['title'] + " Programm:[/COLOR][/B]"
    url = ''
    li = xbmcgui.ListItem(title)
    xbmcplugin.addDirectoryItem(handle=_addon_handler, url=url, listitem=li, isFolder=True)

    if args['title'].lower() == 'fc bayern.tv live':
        #Bayern TV - doppelter Boden:
        title = 'Start Livestream (24/7-Programm)'
        li = xbmcgui.ListItem('[B]' + title + '[/B]')
        li.setProperty('IsPlayable', 'true')
        li.setInfo('video', {})
        url = build_url({'mode': 'event', 'event': '/event/5021', 'live': True})

        xbmcplugin.addDirectoryItem(handle=_addon_handler, url=url, listitem=li)

        title = "--------------------------------------------------------"
        url = ''
        li = xbmcgui.ListItem(title)
        xbmcplugin.addDirectoryItem(handle=_addon_handler, url=url, listitem=li, isFolder=True)

    if args['event_tree_id'] == '':
        eventTreeID_Uebergabe = ''
    else:
        eventTreeID_Uebergabe = 'eventTreeId=' + args['event_tree_id']
    program = json.loads(urlopen(args['eventLane'], eventTreeID_Uebergabe))
    bereitsangelegtnurLive = False
    bereitsangelegtnurLiveInfo = False
    for datas in program['data']['content'][0]['group_elements'][0]['data']:
        #xbmc.log(str(datas))
        createEPG(datas, '0', bereitsangelegtnurLive, bereitsangelegtnurLiveInfo, True)
        bereitsangelegtnurLive = True
        bereitsangelegtnurLiveInfo = True

    xbmcplugin.endOfDirectory(_addon_handler)


def getpage():
    jsonResult = json.loads(urlopen(args['page']))
    title = "[B][COLOR gold]" + jsonResult['data']['metadata']['title'] + ":[/COLOR][/B]"
    url = ''
    li = xbmcgui.ListItem(title)
    li.setArt({'icon': jsonResult['data']['metadata']['web']['image']})
    xbmcplugin.addDirectoryItem(handle=_addon_handler, url=url, listitem=li, isFolder=True)
    #programm
    for header in jsonResult['data']['navigation']['header']:
        title = "[B]" + header['title'] + "[/B]"
        url = build_url({'mode': header['target_type'], 'eventLane': header['target'], 'event_tree_id': args['event_tree_id'], 'title': jsonResult['data']['metadata']['title']})

        li = xbmcgui.ListItem(title)
        #li.setArt({'icon': jsonResult['data']['metadata']['web']['image']})
        xbmcplugin.addDirectoryItem(handle=_addon_handler, url=url, listitem=li, isFolder=True)
    title = "--------------------------------------------------------"
    url = ''
    li = xbmcgui.ListItem(title)
    xbmcplugin.addDirectoryItem(handle=_addon_handler, url=url, listitem=li, isFolder=True)

    count = 0
    for content in jsonResult['data']['content']:
        for group_element in content['group_elements']:
            if group_element['type'] in ['eventLane', 'editorialLane']:
                count += 1

    for content in jsonResult['data']['content']:
        for group_element in content['group_elements']:
            if group_element['type'] in ['eventLane', 'editorialLane']:
                if count <= 1:
                    args['eventLane'] = group_element['data_url']
                    geteventLane()
                else:
                    if content['title'] and group_element['title']:
                        li = xbmcgui.ListItem("[COLOR gold]" + content['title'].upper() + "[/COLOR]")
                        li.setProperty("IsPlayable", "false")
                        xbmcplugin.addDirectoryItem(handle=_addon_handler, url="", listitem=li)

                    title = group_element['title'] if group_element['title'] else "[B]" + content['title'].upper() + "[/B]"
                    if not title.strip():
                        title = __language__(30003)
                    url = build_url({'mode': 'eventLane', 'eventLane': group_element['data_url']})
                    li = xbmcgui.ListItem(title)
                    li.setArt({'icon': jsonResult['data']['metadata']['web']['image']})
                    xbmcplugin.addDirectoryItem(handle=_addon_handler, url=url, listitem=li, isFolder=True)

    xbmcplugin.endOfDirectory(_addon_handler)

def geteventLane():
    jsonResult = json.loads(urlopen(args['eventLane']))
    eventday = None;
    for event in jsonResult['data']['data']:
        if event['target_type'] == 'event':
            scheduled_start = datetime.utcfromtimestamp(int(event['metadata']['scheduled_start']['utc_timestamp']))
            if (eventday is None or (event['metadata']['state'] == "post" and scheduled_start.date() < eventday) or (event['metadata']['state'] != "post" and scheduled_start.date() > eventday)
                and not (event['metadata']['state'] != 'live' and ('onlylive' in args and args['onlylive']))):
                li = xbmcgui.ListItem("[COLOR gold]" + prettydate(scheduled_start, False) + "[/COLOR]")
                li.setProperty("IsPlayable", "false")
                xbmcplugin.addDirectoryItem(handle=_addon_handler, url="", listitem=li)
                eventday = scheduled_start.date()

            title = __language__(30003)

            if event['metadata']['title']:
                if event['type'] in ['teamEvent', 'skyTeamEvent', 'fcbEvent']:
                    if event['metadata']['state'] == 'live':
                        title = __language__(30004) + ': ' + event['metadata']['name']
                    else:
                        title = str(prettytime(scheduled_start)) + " Uhr: " + event['metadata']['name']
                else:
                    #Top 10 etc.
                    title = event['metadata']['title']
            else:
                if event['type'] in ['teamEvent', 'skyTeamEvent'] and 'details' in event['metadata'] and 'home' in event['metadata']['details']:
                    if event['metadata']['state'] == 'live':
                        title = __language__(30004) + ': ' + event['metadata']['details']['home']['name_full'] + ' - ' + event['metadata']['details']['away']['name_full']
                    else:
                        title = str(prettytime(scheduled_start)) + " Uhr: "+event['metadata']['details']['home']['name_full'] + ' - ' + event['metadata']['details']['away']['name_full']
                elif event['metadata']['description_bold']:
                    if event['metadata']['state'] == 'live':
                        title = __language__(30004) + ': ' + event['metadata']['description_bold']
                    else:
                        title = str(prettytime(scheduled_start)) + " Uhr: " + event['metadata']['description_bold']

            eventinfo = event['metadata']['description_bold'] + ' - ' + event['metadata']['description_regular']
            li = xbmcgui.ListItem('[B]' + title + '[/B] (' + eventinfo + ')')
            li.setArt({'icon': base_image_url + event['metadata']['images']['editorial']})
            li.setInfo('video', {'plot': prettydate(scheduled_start)})
            li.setProperty('icon', base_image_url + event['metadata']['images']['editorial'])

            if event['metadata']['state'] == 'live':
                li.setProperty('IsPlayable', 'true')
                li.setInfo('video', {})
                url = build_url({'mode': 'event', 'event': event['target'], 'live': True})
                xbmc.log('streamlink: '+str(event['target']))
                xbmcplugin.addDirectoryItem(handle=_addon_handler, url=url, listitem=li)
            elif not ('onlylive' in args and args['onlylive']):
                url = build_url({'mode': 'event', 'event': event['target']})
                xbmcplugin.addDirectoryItem(handle=_addon_handler, url=url, listitem=li, isFolder=True)

    xbmcplugin.endOfDirectory(_addon_handler)

def getevent():
    xbmc.log('ich starte das event '+str(args['event']))
    jsonResult = json.loads(urlopen(args['event']))
    if jsonResult['data']['content'][0]['group_elements'][0]['type'] == 'noVideo':
        scheduled_start = datetime.utcfromtimestamp(int(jsonResult['data']['content'][0]['group_elements'][0]['data']['metadata']['scheduled_start']['utc_timestamp']))
        if jsonResult['data']['content'][0]['group_elements'][0]['data']['metadata']['state'] == 'pre' and scheduled_start > datetime.utcnow():
            xbmcgui.Dialog().ok(_addon_name, __language__(30001), "", prettydate(scheduled_start))
        else:
            xbmcgui.Dialog().ok(_addon_name, __language__(30002))
        xbmcplugin.endOfDirectory(_addon_handler, succeeded=False)
    elif 'live' in args and args['live']:
        if jsonResult['data']['content'][0]['group_elements'][0]['type'] == 'player':
            eventVideo = jsonResult['data']['content'][0]['group_elements'][0]['data'][0]
            #global args
            #args = {'videoid': eventVideo['videoID'], 'isPay': 'True' if ('pay' in eventVideo and eventVideo['pay']) else 'False'}
            getvideo2(eventVideo['videoID'], 'True' if ('pay' in eventVideo and eventVideo['pay']) else 'False')
    else:
        for index, content in enumerate(jsonResult['data']['content']):
            for group_element in content['group_elements']:
                if group_element['type'] == 'eventVideos':
                    for eventVideo in group_element['data']:
                        isPay = 'pay' in eventVideo and eventVideo['pay']
                        url = build_url({'mode': 'video', 'videoid': eventVideo['videoID'], 'isPay': isPay})
                        li = xbmcgui.ListItem(eventVideo['title'])
                        li.setArt({'icon': base_image_url + eventVideo['images']['editorial']})
                        li.setProperty('icon', base_image_url + eventVideo['images']['editorial'])
                        li.setProperty('IsPlayable', 'true')
                        li.setInfo('video', {})
                        xbmcplugin.addDirectoryItem(handle=_addon_handler, url=url, listitem=li)
        xbmcplugin.endOfDirectory(_addon_handler)

def getvideo():
    getvideo2(args['videoid'], args['isPay'])

def getvideo2(videoid, isPay):
    jwt = None
    if isPay == 'True':
        if not _addon.getSetting('username'):
            xbmcgui.Dialog().ok(_addon_name, __language__(30007))
            _addon.openSettings()
            return
        else:
            try:
                jwt = get_jwt(_addon.getSetting('username'), _addon.getSetting('password'))
            except urllib.error.HTTPError as e:
                response = json.loads(e.read())
                msg = __language__(30005)
                if 'error_description' in response:
                    msg += '\n\n'
                    msg += __language__(30011)
                    msg += '\n"' + response['error_description'] + '"'
                xbmcgui.Dialog().ok(_addon_name, msg)
                xbmcplugin.setResolvedUrl(_addon_handler, False, xbmcgui.ListItem())
                return

    jwt = jwt or 'empty'
    response = urllib.request.urlopen(urllib.request.Request(stream_url, json.dumps({'videoId': videoid}).encode(),
                                                             {'xauthorization': jwt,
                                                              'Content-Type': 'application/json'})).read()
    jsonResult = json.loads(response)

    streamAuswahlListe = []
    streamURLListe = []
    hlsDashListe = []
    playlisturl = ''
    drmToken = ''
    drmPixel = ''
    try:
        drmToken = jsonResult['data']['drmToken']
        drmPixel = jsonResult['data']['drmPixel']
    except:
        xbmc.log('No drmToken')

    try:
        url = 'https:' + jsonResult['data']['stream-access'][0]
        response = urllib.request.urlopen(url).read()
        xmlroot = ET.ElementTree(ET.fromstring(response))
        playlisturl = xmlroot.find('token').get('url')
        auth = xmlroot.find('token').get('auth')
        streamURLListe.append(playlisturl + "?hdnea=" + auth)
        streamAuswahlListe.append('XML-Stream (hls)')
        hlsDashListe.append('hls')
    except:
        xbmc.log("XML-Stream not available")

    try:
        streamURLListe.append(jsonResult['data']['stream']['dash'])
        streamAuswahlListe.append('Hauptstream (dash)')
        hlsDashListe.append('dash')
    except:
        xbmc.log("Hauptstream dash not available")

    try:
        streamURLListe.append(jsonResult['data']['stream']['hls'])
        streamAuswahlListe.append('Hauptstream (hls)')
        hlsDashListe.append('hls')
    except:
        xbmc.log("Hauptstream hls not available")

    try:
        streamURLListe.append(jsonResult['data']['backup']['dash'])
        streamAuswahlListe.append('Backupstream (dash)')
        hlsDashListe.append('dash')
    except:
        xbmc.log("Backupstream dash not available")

    try:
        streamURLListe.append(jsonResult['data']['backup']['hls'])
        streamAuswahlListe.append('Backupstream (hls)')
        hlsDashListe.append('hls')
    except:
        xbmc.log("Backupstream hls not available")

    streamURLListe.append('leer')
    streamAuswahlListe.append('Hinweis: Ggf. Stream vorspulen!!!')
    hlsDashListe.append('leer')
    Dialog = xbmcgui.Dialog()

    auswahl = Dialog.select("Stream auswählen", streamAuswahlListe)
    if auswahl > -1:
        if hlsDashListe[auswahl] != 'leer':
            xbmc.log("Stream Nr " + str(auswahl) + " selected: "+streamAuswahlListe[auswahl])
            xbmc.log("Stream-URL: "+streamURLListe[auswahl])
            #xbmc.log("DRM-Token: "+drmToken)
            listitem = xbmcgui.ListItem(path=streamURLListe[auswahl])
            if auswahl != 0:
                listitem.setProperty('inputstream.adaptive.license_type', 'com.widevine.alpha')
                listitem.setProperty('inputstream.adaptive.license_key', drmToken)
            #listitem.setProperty('inputstream.adaptive.stream_headers', 'User-Agent=the_user_agent&Cookie=the_cookies')
            # +"|Content-Type=&User-Agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:92.0) Gecko/20100101 Firefox/92.0
            listitem.setProperty('inputstream', 'inputstream.adaptive')
            if hlsDashListe[auswahl] == 'hls':
                listitem.setProperty('inputstream.adaptive.manifest_type', 'hls')
            else:
                listitem.setProperty('inputstream.adaptive.manifest_type', 'mpd')
            xbmcplugin.setResolvedUrl(_addon_handler, True, listitem)


##############
# main routine
##############

if api_version == 0:
    api_version = 0
    if _addon.getSetting('api_version') == 'V2':
        api_version = 2
    elif _addon.getSetting('api_version') == 'V3':
        api_version = 3

    base_api = base_api + str(api_version)
    xbmc.log('Api-Version: '+str(api_version))
    #match = search('.*?(\/api\/v3\/[^?]*)', base_url + base_api + main_page)
    #if match:
    #
    #else:

# get arguments
args = dict(urlparse.parse_qsl(sys.argv[2][1:]))
mode = args.get('mode', None)
xbmc.log('ich gehe hier nun hin: '+str(mode))
if mode is None:
    mode = 'Main'
locals()['get' + mode]()
