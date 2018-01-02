# Acknowledgements: Lots of code from Mikey1234. Thanks.

from xbmcswift2 import Plugin, ListItem
from xbmcswift2 import actions
import xbmc,xbmcaddon,xbmcvfs,xbmcgui,xbmcplugin
import re
import requests,urllib
import os,sys
import xml.etree.ElementTree as ET
import base64
import datetime

from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

plugin = Plugin()
big_list_view = False

def log(v):
    xbmc.log(repr(v),xbmc.LOGERROR)

def get_icon_path(icon_name):
    addon_path = xbmcaddon.Addon().getAddonInfo("path")
    return os.path.join(addon_path, 'resources', 'img', icon_name+".png")

def remove_formatting(label):
    label = re.sub(r"\[/?[BI]\]",'',label)
    label = re.sub(r"\[/?COLOR.*?\]",'',label)
    return label

def escape( str ):
    str = str.replace("'","&#39;")
    str = str.replace("&", "&amp;")
    str = str.replace("<", "&lt;")
    str = str.replace(">", "&gt;")
    str = str.replace("\"", "&quot;")
    return str

def unescape( str ):
    str = str.replace("&lt;","<")
    str = str.replace("&gt;",">")
    str = str.replace("&quot;","\"")
    str = str.replace("&amp;","&")
    str = str.replace("&#39;","'")
    return str

def get(url,proxy=False):
    headers = {'User-Agent':'Mozilla/5.0 (Windows NT 6.1; rv:50.0) Gecko/20100101 Firefox/50.0'}
    if proxy:
        headers['Referer'] = 'http://www.justproxy.co.uk/'
        url = 'http://www.justproxy.co.uk/index.php?q=%s' % base64.b64encode(url)
    #log(url)
    try:
        #log(("GGG",url))
        r = requests.get(url,headers=headers,verify=False)
    except:
        return
    if r.status_code != requests.codes.ok:
        return
    html = r.content
    #log(html)
    return html

@plugin.route('/reset_cached')
def reset_cached():
    cached = plugin.get_storage('cached')
    cached.clear()

@plugin.route('/schedule/<url>/<name>')
def schedule(url,name):
    data = get(url)
    schedule = ET.fromstring(data)
    days = schedule.findall("day")
    items = []
    if plugin.get_setting('autoplay') == 'true':
        autoplay = True
        action = "autoplay"
    else:
        autoplay = False
        action = "list"
    for day in days:
        first = True
        broadcasts = day[0]
        for broadcast in broadcasts:
            pid = broadcast.find("pid").text
            start = broadcast.find("start").text
            if first:
                date = start[0:10]
                first = False
                items.append({
                    'label' : "[COLOR yellow][B]%s[/B][/COLOR]" % date,
                    'thumbnail' : get_icon_path("calendar"),
                    'path' : '',
                    'is_playable' : False,
                })
            end = broadcast.find("end").text
            programme = broadcast.find("programme")
            is_available = programme.find("is_available_mediaset_pc_sd").text
            pid = programme.find("pid").text
            display_titles = programme.find("display_titles")
            image = programme.find("image")
            image_pid = image.find("pid").text
            title = display_titles.find("title").text
            subtitle = display_titles.find("subtitle").text
            if subtitle == None:
                subtitle = ""
            else:
                subtitle = "- %s" % subtitle
            NAME = "[COLOR dimgray]%s-%s[/COLOR] %s %s" % (start[11:16],end[11:16],title,subtitle)
            episode_url = 'http://www.bbc.co.uk/iplayer/episode/%s' % pid
            thumbnail = 'https://ichef.bbci.co.uk/images/ic/336x189/%s.jpg' % image_pid
            play_name = "%s %s" % (title,subtitle)
            if is_available == "1":
                URL = plugin.url_for('play_episode',url=episode_url,name=play_name,thumbnail=thumbnail,action=action)
                NAME = "[COLOR %s]%s[/COLOR]" % (remove_formatting(plugin.get_setting('catchup.colour')),NAME)
            else:
                URL = plugin.url_for('schedule',url=url, name=name)
            context_items = []
            context_items.append(("[COLOR yellow][B]%s[/B][/COLOR] " % 'Add Favourite', 'XBMC.RunPlugin(%s)' %
            (plugin.url_for(add_favourite, name=play_name, url=episode_url, thumbnail=thumbnail, is_episode=True))))
            context_items.append(("[COLOR yellow][B]%s[/B][/COLOR] " % 'Add to PVR', 'XBMC.RunPlugin(%s)' %
            (plugin.url_for(add_pvr, name=play_name, url=episode_url, thumbnail=thumbnail, is_episode=True))))
            context_items.append(("[COLOR yellow][B]%s[/B][/COLOR] " % 'Cache', 'XBMC.RunPlugin(%s)' %
            (plugin.url_for('play_episode',url=episode_url,name=play_name,thumbnail=thumbnail,action="cache"))))
            items.append({
                'label' : NAME,
                'thumbnail' : thumbnail,
                'path' : URL,
                'is_playable' : autoplay,
                'context_menu': context_items,
            })

    return items

@plugin.route('/schedule_period/<url>/<name>/<thumbnail>')
def schedule_period(url,name,thumbnail):
    items = []
    for period in ["today","tomorrow","yesterday","this_week","next_week","last_week"]:
        icon = 'special://home/addons/plugin.video.bbc/resources/img/%s.png' % id
        URL = url.replace('today',period)
        items.append({
            'label' : "%s - %s" % (name,period.replace('_',' ').title()),
            'thumbnail' : icon,
            'path' : plugin.url_for('schedule',url=URL, name=name),
            'is_playable' : False
        })
    return items

@plugin.route('/schedules')
def schedules():
    channels = [
        ('bbc_one_hd', "BBC One", "http://www.bbc.co.uk/bbcone/programmes/schedules/hd/today.xml"),
        ('bbc_two_hd', "BBC Two", "http://www.bbc.co.uk/bbctwo/programmes/schedules/hd/today.xml"),
        ('bbc_four_hd', "BBC Four", "http://www.bbc.co.uk/bbcfour/programmes/schedules/today.xml"),
        ('bbc_news24', "BBC News", "http://www.bbc.co.uk/bbcnews/programmes/schedules/today.xml"),
        ('bbc_parliament', "BBC Parliament", "http://www.bbc.co.uk/bbcparliament/programmes/schedules/today.xml"),
        ('cbbc_hd', "CBBC", "http://www.bbc.co.uk/cbbc/programmes/schedules/today.xml"),
        ('cbeebies_hd', "CBeebies", "http://www.bbc.co.uk/cbeebies/programmes/schedules/today.xml"),
        ('bbc_alba', "Alba", "http://www.bbc.co.uk/bbcalba/programmes/schedules/today.xml"),
        ('s4cpbs', "S4C", "http://www.bbc.co.uk/s4c/programmes/schedules/today.xml"),
        ('bbc_one_hd', "BBC One Cambridgeshire", "http://www.bbc.co.uk/bbcone/programmes/schedules/cambridge/today.xml"),
        ('bbc_one_hd', "BBC One Channel Islands", "http://www.bbc.co.uk/bbcone/programmes/schedules/channel_islands/today.xml"),
        ('bbc_one_hd', "BBC One East", "http://www.bbc.co.uk/bbcone/programmes/schedules/east/today.xml"),
        ('bbc_one_hd', "BBC One East Midlands", "http://www.bbc.co.uk/bbcone/programmes/schedules/east_midlands/today.xml"),
        ('bbc_one_hd', "BBC One Yorks & Lincs", "http://www.bbc.co.uk/bbcone/programmes/schedules/east_yorkshire/today.xml"),
        ('bbc_one_hd', "BBC One HD", "http://www.bbc.co.uk/bbcone/programmes/schedules/hd/today.xml"),
        ('bbc_one_hd', "BBC One London", "http://www.bbc.co.uk/bbcone/programmes/schedules/london/today.xml"),
        ('bbc_one_hd', "BBC One Northern Ireland", "http://www.bbc.co.uk/bbcone/programmes/schedules/ni/today.xml"),
        ('bbc_one_hd', "BBC One Northern Ireland HD", "http://www.bbc.co.uk/bbcone/programmes/schedules/ni_hd/today.xml"),
        ('bbc_one_hd', "BBC One North East & Cumbria", "http://www.bbc.co.uk/bbcone/programmes/schedules/north_east/today.xml"),
        ('bbc_one_hd', "BBC One North West", "http://www.bbc.co.uk/bbcone/programmes/schedules/north_west/today.xml"),
        ('bbc_one_hd', "BBC One Oxfordshire", "http://www.bbc.co.uk/bbcone/programmes/schedules/oxford/today.xml"),
        ('bbc_one_hd', "BBC One Scotland", "http://www.bbc.co.uk/bbcone/programmes/schedules/scotland/today.xml"),
        ('bbc_one_hd', "BBC One Scotland HD", "http://www.bbc.co.uk/bbcone/programmes/schedules/scotland_hd/today.xml"),
        ('bbc_one_hd', "BBC One South", "http://www.bbc.co.uk/bbcone/programmes/schedules/south/today.xml"),
        ('bbc_one_hd', "BBC One South East", "http://www.bbc.co.uk/bbcone/programmes/schedules/south_east/today.xml"),
        ('bbc_one_hd', "BBC One South West", "http://www.bbc.co.uk/bbcone/programmes/schedules/south_west/today.xml"),
        ('bbc_one_hd', "BBC One Wales", "http://www.bbc.co.uk/bbcone/programmes/schedules/wales/today.xml"),
        ('bbc_one_hd', "BBC One Wales HD", "http://www.bbc.co.uk/bbcone/programmes/schedules/wales_hd/today.xml"),
        ('bbc_one_hd', "BBC One West", "http://www.bbc.co.uk/bbcone/programmes/schedules/west/today.xml"),
        ('bbc_one_hd', "BBC One West Midlands", "http://www.bbc.co.uk/bbcone/programmes/schedules/west_midlands/today.xml"),
        ('bbc_one_hd', "BBC One Yorkshire", "http://www.bbc.co.uk/bbcone/programmes/schedules/yorkshire/today.xml"),
        ('bbc_two_hd', "BBC Two Wales", "http://www.bbc.co.uk/bbctwo/programmes/schedules/wales/today.xml"),
        ('bbc_two_hd', "BBC Two Scotland", "http://www.bbc.co.uk/bbctwo/programmes/schedules/scotland/today.xml"),
        ('bbc_two_hd', "BBC Two England", "http://www.bbc.co.uk/bbctwo/programmes/schedules/england/today.xml"),
        ('bbc_two_hd', "BBC Two Northern Ireland", "http://www.bbc.co.uk/bbctwo/programmes/schedules/ni/today.xml"),
    ]
    items = []
    for id, name, url in channels:
        icon = 'special://home/addons/plugin.video.bbc/resources/img/%s.png' % id
        items.append({
            'label' : name,
            'thumbnail' : icon,
            'path' : plugin.url_for('schedule_period',url=url, name=name, thumbnail=icon),
            'is_playable' : False
        })

    return items

@plugin.route('/red_button')
def red_button():
    items = []
    device = 'abr_hdtv'
    provider = 'ak'
    for suffix in ['','b']:
        for i in range(1,25):
            id = "sport_stream_%02d%s" % (i,suffix)
            name = "Red Button %02d%s" % (i,suffix)
            url='http://a.files.bbci.co.uk/media/live/manifesto/audio_video/webcast/hls/uk/%s/%s/%s.m3u8' % (device, provider, id)
            icon = 'special://home/addons/plugin.video.bbc/resources/img/red_button.png'
            if plugin.get_setting('autoplay') == 'true':
                items.append({
                    'label' : name,
                    'thumbnail' : icon,
                    'path' : url,
                    'is_playable' : True
                })
            else:
                items.append({
                    'label' : name,
                    'thumbnail' : icon,
                    'path' : plugin.url_for('live_list',url=url, name=name, thumbnail=icon),
                    'is_playable' : False
                })
    return items

@plugin.route('/make_playlist')
def make_playlist():
    hd = [
        ('bbc_one_hd',                       'BBC One'),
        ('bbc_two_hd',                       'BBC Two'),
        ('bbc_four_hd',                      'BBC Four'),
        ('cbbc_hd',                          'CBBC'),
        ('cbeebies_hd',                      'CBeebies'),
        ('bbc_one_scotland_hd',              'BBC One Scotland'),
        ('bbc_one_northern_ireland_hd',      'BBC One Northern Ireland'),
        ('bbc_one_wales_hd',                 'BBC One Wales'),

    ]
    sd = [
        ('bbc_news24',                       'BBC News Channel'),
        ('bbc_parliament',                   'BBC Parliament'),
        ('bbc_alba',                         'Alba'),
        ('s4cpbs',                           'S4C'),
        ('bbc_two_scotland',                 'BBC Two Scotland'),
        ('bbc_two_northern_ireland_digital', 'BBC Two Northern Ireland'),
        ('bbc_two_wales_digital',            'BBC Two Wales'),
        ('bbc_two_england',                  'BBC Two England'),
        ('bbc_one_london',                   'BBC One London'),
        ('bbc_one_cambridge',                'BBC One Cambridge'),
        ('bbc_one_channel_islands',          'BBC One Channel Islands'),
        ('bbc_one_east',                     'BBC One East'),
        ('bbc_one_east_midlands',            'BBC One East Midlands'),
        ('bbc_one_east_yorkshire',           'BBC One East Yorkshire'),
        ('bbc_one_north_east',               'BBC One North East'),
        ('bbc_one_north_west',               'BBC One North West'),
        ('bbc_one_oxford',                   'BBC One Oxford'),
        ('bbc_one_south',                    'BBC One South'),
        ('bbc_one_south_east',               'BBC One South East'),
        ('bbc_one_west',                     'BBC One West'),
        ('bbc_one_west_midlands',            'BBC One West Midlands'),
        ('bbc_one_yorks',                    'BBC One Yorks')
    ]

    items = []

    device = 'abr_hdtv'
    provider = 'ak'
    urls = []
    for id, name  in hd :
        url='http://a.files.bbci.co.uk/media/live/manifesto/audio_video/simulcast/hls/uk/%s/%s/%s.m3u8' % (device, provider, id)
        urls.append((name,url))
    device = 'hls_mobile_wifi'
    for id, name  in sd :
        url='http://a.files.bbci.co.uk/media/live/manifesto/audio_video/simulcast/hls/uk/%s/%s/%s.m3u8' % (device, provider, id)
        urls.append((name,url))

    playlist = xbmcvfs.File('special://profile/addon_data/plugin.video.bbc/BBC.m3u8','wb')
    playlist.write('#EXTM3U\n')
    for name,url in urls:
        html = get(url)
        match=re.compile('#EXT-X-STREAM-INF:PROGRAM-ID=1,BANDWIDTH=(.+?),CODECS="(.+?)",RESOLUTION=(.+?)\n(.+?)$',flags=(re.DOTALL | re.MULTILINE)).findall(html)
        for bandwidth,codec,resolution,stream_url in sorted(match, key=lambda x: int(x[0]), reverse=True):
            if bandwidth <= plugin.get_setting('live.bandwidth'):
                playlist.write('#EXTINF:0,%s\n%s\n' % (name,stream_url))
                break
    playlist.close()



@plugin.route('/live')
def live():
    hd = [
        ('bbc_one_hd',                       'BBC One'),
        ('bbc_two_hd',                       'BBC Two'),
        ('bbc_four_hd',                      'BBC Four'),
        ('cbbc_hd',                          'CBBC'),
        ('cbeebies_hd',                      'CBeebies'),
        ('bbc_one_scotland_hd',              'BBC One Scotland'),
        ('bbc_one_northern_ireland_hd',      'BBC One Northern Ireland'),
        ('bbc_one_wales_hd',                 'BBC One Wales'),

    ]
    sd = [
        ('bbc_news24',                       'BBC News Channel'),
        ('bbc_parliament',                   'BBC Parliament'),
        ('bbc_alba',                         'Alba'),
        ('s4cpbs',                           'S4C'),
        ('bbc_two_scotland',                 'BBC Two Scotland'),
        ('bbc_two_northern_ireland_digital', 'BBC Two Northern Ireland'),
        ('bbc_two_wales_digital',            'BBC Two Wales'),
        ('bbc_two_england',                  'BBC Two England'),
        ('bbc_one_london',                   'BBC One London'),
        ('bbc_one_cambridge',                'BBC One Cambridge'),
        ('bbc_one_channel_islands',          'BBC One Channel Islands'),
        ('bbc_one_east',                     'BBC One East'),
        ('bbc_one_east_midlands',            'BBC One East Midlands'),
        ('bbc_one_east_yorkshire',           'BBC One East Yorkshire'),
        ('bbc_one_north_east',               'BBC One North East'),
        ('bbc_one_north_west',               'BBC One North West'),
        ('bbc_one_oxford',                   'BBC One Oxford'),
        ('bbc_one_south',                    'BBC One South'),
        ('bbc_one_south_east',               'BBC One South East'),
        ('bbc_one_west',                     'BBC One West'),
        ('bbc_one_west_midlands',            'BBC One West Midlands'),
        ('bbc_one_yorks',                    'BBC One Yorks')
    ]

    items = []

    device = 'abr_hdtv'
    provider = 'ak'
    for id, name  in hd :
        url='http://a.files.bbci.co.uk/media/live/manifesto/audio_video/simulcast/hls/uk/%s/%s/%s.m3u8' % (device, provider, id)
        icon = 'special://home/addons/plugin.video.bbc/resources/img/%s.png' % id
        if plugin.get_setting('autoplay') == 'true':
            items.append({
                'label' : name,
                'thumbnail' : icon,
                'path' : plugin.url_for('play_live',url=url, name=name, thumbnail=icon),
                'is_playable' : True
            })
        else:
            items.append({
                'label' : name,
                'thumbnail' : icon,
                'path' : plugin.url_for('live_list',url=url, name=name, thumbnail=icon),
                'is_playable' : False
            })
    device = 'hls_mobile_wifi'
    for id, name  in sd :
        url='http://a.files.bbci.co.uk/media/live/manifesto/audio_video/simulcast/hls/uk/%s/%s/%s.m3u8' % (device, provider, id)
        icon = 'special://home/addons/plugin.video.bbc/resources/img/%s.png' % id
        if plugin.get_setting('autoplay') == 'true':
            items.append({
                'label' : name,
                'thumbnail' : icon,
                'path' : plugin.url_for('play_live',url=url, name=name, thumbnail=icon),
                'is_playable' : True
            })
        else:
            items.append({
                'label' : name,
                'thumbnail' : icon,
                'path' : plugin.url_for('live_list',url=url, name=name, thumbnail=icon),
                'is_playable' : False
            })

    return items

@plugin.route('/play_live/<url>/<name>/<thumbnail>')
def play_live(url,name,thumbnail):
    html = get(url)
    match=re.compile('#EXT-X-STREAM-INF:PROGRAM-ID=1,BANDWIDTH=(.+?),CODECS="(.+?)",RESOLUTION=(.+?)\n(.+?)$',flags=(re.DOTALL | re.MULTILINE)).findall(html)
    for bandwidth,codec,resolution,url in sorted(match, key=lambda x: int(x[0]), reverse=True):
        #label = "%s [%s bps] %s" % (name,bandwidth,resolution)
        if bandwidth <= plugin.get_setting('live.bandwidth'):
            item = {
                'label' : name,
                'thumbnail' : thumbnail,
                'path' : url,
                'is_playable' : True
            }
            return plugin.set_resolved_url(item)

@plugin.route('/live_list/<url>/<name>/<thumbnail>')
def live_list(url,name,thumbnail):
    html = get(url)
    items = []
    match=re.compile('#EXT-X-STREAM-INF:PROGRAM-ID=1,BANDWIDTH=(.+?),CODECS="(.+?)",RESOLUTION=(.+?)\n(.+?)$',flags=(re.DOTALL | re.MULTILINE)).findall(html)
    for bandwidth,codec,resolution,url in sorted(match, key=lambda x: int(x[0]), reverse=True):
        label = "%s [%s bps] %s" % (name,bandwidth,resolution)
        items.append({
            'label' : label,
            'thumbnail' : thumbnail,
            'path' : url,
            'is_playable' : True
        })
    return items

@plugin.route('/proxy_play_episode/<url>/<name>/<thumbnail>/<action>')
def proxy_play_episode(url,name,thumbnail,action):
    html = get(url)
    vpid = ''
    match = re.search(r'window\.mediatorDefer\=page\(document\.getElementById\(\"tviplayer\"\),(.*?)\);', html, re.DOTALL)
    if match:
        data = match.group(1)
        import json
        json_data = json.loads(data)
        # print json.dumps(json_data, indent=2, sort_keys=True)
        name = json_data['episode']['title']
        description = json_data['episode']['synopses']['large']
        image = json_data['episode']['images']['standard'].replace('{recipe}','832x468')
        for stream in json_data['episode']['versions']:
            if ((stream['kind'] == 'original') or
               (stream['kind'] == 'iplayer-version')):
                vpid = stream_id_st = stream['id']

    if not vpid:
        return

    NEW_URL= "http://open.live.bbc.co.uk/mediaselector/5/select/version/2.0/mediaset/apple-ipad-hls/vpid/%s" % vpid
    html = get(NEW_URL,True)
    urls = []
    match=re.compile('application="(.+?)".+?String="(.+?)".+?identifier="(.+?)".+?protocol="(.+?)".+?server="(.+?)".+?supplier="(.+?)"').findall(html.replace('amp;',''))
    for app,auth , playpath ,protocol ,server,supplier in match:

        port = '1935'
        if protocol == 'rtmpt': port = 80
        if supplier == 'limelight':
            url="%s://%s:%s/ app=%s?%s tcurl=%s://%s:%s/%s?%s playpath=%s" % (protocol,server,port,app,auth,protocol,server,port,app,auth,playpath)
            res = playpath.split('secure_auth/')[1]
            res = res.split('kbps')[0]
            urls.append([url,res])

    items = []
    for url,res in sorted(urls,key = lambda x: int(x[1]), reverse=True):

        items.append({
            'label': "%s [%s kbps]" % (name, res),
            'path': url,
            'thumbnail': thumbnail,
            'is_playable': True
        })

    return items

@plugin.route('/start_pvr_service')
def start_pvr_service():
    xbmc.executebuiltin('XBMC.RunPlugin(plugin://plugin.video.bbc/pvr_service)')

@plugin.route('/pvr_service')
def pvr_service():
    pvrs = plugin.get_storage('pvrs')
    for name in pvrs:
        #log(name)
        split = pvrs[name].split('|')
        url = split[0]
        if len(split) > 0:
            iconimage = split[1]
        else:
            iconimage = ""
        if '/episodes/' in url:
            #log(url)
            cache_all(url)
        else:
            #log((url,name))
            play_episode(url,name,iconimage,"cache")


@plugin.route('/cache_all/<url>')
def cache_all(url):
    #log(("CCC",url))
    headers = {'User-Agent':'Mozilla/5.0 (Windows NT 6.1; rv:50.0) Gecko/20100101 Firefox/50.0'}
    html = get(url)
    if not html:
        return

    items = []
    html_items=html.split('data-ip-id="')
    for p in html_items:
        IPID=p.split('"')[0]
        urls=re.compile('href="(.+?)"').findall (p)

        episode_url = ''
        episodes_url = ''
        for u in urls:
            if u.startswith('/iplayer/episode/'):
                episode_url = 'http://www.bbc.co.uk%s' % u
            elif u.startswith('/iplayer/episodes/'):
                episodes_url = 'http://www.bbc.co.uk%s' % u

        name = re.compile('title="(.+?)"').findall (p)[0]

        series = 0
        episode = None
        match = re.compile('Episode ([0-9]*)$').search (name)
        if match:
            episode = int(match.group(1))
        else:
            match = re.compile('Series ([0-9]*): ([0-9]*)\.').search (name)
            if match:
                series = int(match.group(1))
                episode = int(match.group(2))
            else:
                match = re.compile(', ([0-9]*)\.').search (name)
                if match:
                    episode = int(match.group(1))
        group = ''
        match=re.compile('top-title">(.+?)<').findall (p)
        if match:
            group = match[0]

        iconimage = get_icon_path('tv')
        match=re.compile('img src="(.+?)"').findall (p)
        if match:
            iconimage = match[0]
        else:
            match=re.compile('srcset="(.+?)"').findall (p)
            if match:
                iconimage = match[0]

        if episode:
            label = "%s S%03dE%03d" % (name,series,episode)
            label = re.sub('[%s]' % re.escape(':\/?*><|'),'',label)
            #log((episode_url,label,iconimage))
            play_episode(episode_url,label,iconimage,"cache")


    next_page = re.compile('<span class="next.*?href="(.*?)"',flags=(re.DOTALL | re.MULTILINE)).search (html)
    if next_page:
        url = 'http://www.bbc.co.uk%s' % unescape(next_page.group(1))
        if 'page=' in url:
            cache_all(url)


@plugin.route('/play_episode/<url>/<name>/<thumbnail>/<action>')
def play_episode(url,name,thumbnail,action):
    if action == "cache":
        cached = plugin.get_storage('cached')
        if name in cached:
            return
    html = get(url)
    if not html:
        return
    vpid = ''
    match = re.search(r'window\.mediatorDefer\=page\(document\.getElementById\(\"tviplayer\"\),(.*?)\);', html, re.DOTALL)
    if match:
        data = match.group(1)
        import json
        json_data = json.loads(data)
        # print json.dumps(json_data, indent=2, sort_keys=True)
        json_name = json_data['episode']['title']
        try:
            synopses = json_data['episode']['synopses']
            if 'large' in synopses:
                description = synopses['large']
            elif 'medium' in synopses:
                description = synopses['medium']
            else:
                description = synopses['small']
        except:
            description = ''
        image = json_data['episode']['images']['standard'].replace('{recipe}','832x468')
        stream_id_st = ""
        for stream in json_data['episode']['versions']:
            if ((stream['kind'] == 'original') or
               (stream['kind'] == 'iplayer-version') or
               (stream['kind'] == 'technical-replacement') or
               (stream['kind'] == 'editorial')):
                stream_id_st = stream['id']
            elif (stream['kind'] == 'signed'):
                stream_id_sl = stream['id']
            elif (stream['kind'] == 'audio-described'):
                stream_id_ad = stream['id']
        vpid = stream_id_st
        if not vpid:
            try:
                for i in range(len(json_data['episode']['versions'])):
                    vpid = json_data['episode']['versions'][i]['id']
                    if vpid:
                        break
            except:
                pass

    if not vpid:
        return

    URL=[]
    subtitles = ''
    if int(plugin.get_setting('catchup'))==1:
        NEW_URL= "http://open.live.bbc.co.uk/mediaselector/5/select/version/2.0/mediaset/stb-all-h264/vpid/%s" % vpid
        html = get(NEW_URL)
        if not html:
            return
        match = re.compile('href="([^"]*?subtitles[^"]*?)"').search(html)
        if match:
            subtitles = match.group(1)
        match=re.compile('application="(.+?)".+?String="(.+?)".+?identifier="(.+?)".+?protocol="(.+?)".+?server="(.+?)".+?supplier="(.+?)"').findall(html.replace('amp;',''))
        for app,auth , playpath ,protocol ,server,supplier in match:
            port = '1935'
            if protocol == 'rtmpt': port = 80
            if int(plugin.get_setting('supplier'))==1:
                if supplier == 'limelight':
                    url="%s://%s:%s/ app=%s?%s tcurl=%s://%s:%s/%s?%s playpath=%s" % (protocol,server,port,app,auth,protocol,server,port,app,auth,playpath)
                    res=playpath.split('secure_auth/')[1]
                    resolution=res.split('kbps')[0]
                    URL.append([(eval(resolution)),url])
            elif int(plugin.get_setting('supplier'))==0:
                url="%s://%s:%s/%s?%s playpath=%s?%s" % (protocol,server,port,app,auth,playpath,auth)
                if supplier == 'akamai':
                    res=playpath.split('secure/')[1]
                    resolution=res.split('kbps')[0]
                    URL.append([(eval(resolution)),url])
    else:
        NEW_URL= "http://open.live.bbc.co.uk/mediaselector/5/select/version/2.0/mediaset/iptv-all/vpid/%s" % vpid
        html = get(NEW_URL)
        if not html:
            return
        match = re.compile('href="([^"]*?subtitles[^"]*?)"').search(html)
        if match:
            subtitles = match.group(1)
        html = html.replace('>','>\n')
        lines = html.splitlines()
        for line in lines:
            match = re.compile('media bitrate="(.+?)"').search(line)
            if match:
                bitrate = match.group(1)
            match = re.compile('.*?href="(http://.+?)".*?protocol="(.+?)" supplier="(.+?)" transferFormat="(.+?)"/>').search(line)
            if match:
                url = match.group(1)
                protocol = match.group(2)
                supplier = match.group(3)
                transferFormat = match.group(4)
                if transferFormat == "hls":
                    if plugin.get_setting('supplier') == '0' and 'akamai' in supplier.lower():
                        URL.append([int(bitrate),url])
                    elif plugin.get_setting('supplier') == '1' and 'limelight' in supplier.lower():
                        URL.append([int(bitrate),url])

    if subtitles:
        data = get(subtitles)
        if data:
            lines = data.splitlines()
            i = 0
            f = xbmcvfs.File('special://profile/addon_data/plugin.video.bbc/subtitles.srt','wb')
            for line in lines:
                if line.strip().startswith('<p '):
                    i = i + 1
                    match = re.compile('begin="([^"]*?)"').search(line)
                    if match:
                        begin = match.group(1)
                        begin = begin.replace('.',',')
                        if len(begin.split(',')[-1]) == 2:
                            begin = begin + '0'
                    match = re.compile('end="([^"]*?)"').search(line)
                    if match:
                        end = match.group(1)
                        end = end.replace('.',',')
                        if len(end.split(',')[-1]) == 2:
                            end = end + '0'
                    match = re.compile('>(.*)<').search(line)
                    if match:
                        text = match.group(1).strip()
                        text = text.replace('<br />','\n')
                        text = text.replace('  ','\n')
                        text = re.compile('<[^>]*>').sub('',text)
                    f.write(str(i)+'\n')
                    f.write("%s --> %s\n" % (begin,end))
                    f.write(text+'\n\n')
            f.close()

    if action == "autoplay":
        URL=max(URL)[1]
        item =  {
            'label': name,
            'path': URL,
            'thumbnail': thumbnail
        }
        if subtitles and plugin.get_setting('subtitles') == 'true':
            plugin.set_resolved_url(item,'special://profile/addon_data/plugin.video.bbc/subtitles.srt')
        else:
            plugin.set_resolved_url(item)

    elif action == "list":
        items = []
        for u in sorted(URL, reverse=True):
            items.append({
                'label': "%s [%d kbps]" % (name, u[0]),
                'path': u[1],
                'thumbnail': thumbnail,
                'is_playable': True
            })
        return items
    elif action == "cache":
        cached = plugin.get_storage('cached')
        if name in cached:
            return
        URL=max(URL)[1]
        BASE = re.compile('/[^/]*?$').sub('/',URL)
        #log(URL)
        html = get(URL)
        if not html:
            return

        if "variants" in html:
            lines = html.splitlines()
            last = lines[-1]
            URL = BASE + last
            html = get(URL)

        lines = html.splitlines()
        if not URL.startswith('http'):
            return
        html = get(URL)
        lines = html.splitlines()
        basename = '%s%s' % (plugin.get_setting('cache'), re.sub('[\\/:]','',name))
        xbmcvfs.copy('special://profile/addon_data/plugin.video.bbc/subtitles.srt',"%s.srt" % basename)
        f = xbmcvfs.File("%s.ts" % basename,'wb')
        chunks = [x for x in lines if not x.startswith('#')]
        if plugin.get_setting('cache.progress') == 'true':
            progress = True
        else:
            progress = False
        if progress:
            d = xbmcgui.DialogProgressBG()
            d.create('BBC','%s' % name)
            total = len(chunks)
            count = 0
        else:
            xbmcgui.Dialog().notification("BBC Cache Started",name)
        for chunk in chunks:
            if not chunk.startswith('http'):
                chunk = BASE+chunk
            data = get(chunk)
            f.write(data)
            if progress:
                percent = int(100.0 * count / total)
                d.update(percent, "BBC", "%s" % name)
                count = count + 1
        f.close()
        cached[name] = datetime.datetime.now()
        if progress:
            d.close()
        else:
            xbmcgui.Dialog().notification("BBC Cache Finished",name)



@plugin.route('/alphabet')
def alphabet():
    items = []
    for letter in char_range('A', 'Z'):
        items.append({
            'label': letter,
            'path': plugin.url_for('letter',letter=letter.lower()),
            'thumbnail':get_icon_path('lists'),
        })
    items.append({
        'label': "0-9",
        'path': plugin.url_for('letter',letter="0-9"),
        'thumbnail':get_icon_path('lists'),
    })

    return items

def char_range(c1, c2):
    for c in xrange(ord(c1), ord(c2)+1):
        yield chr(c)

@plugin.route('/letter/<letter>')
def letter(letter):
    url = 'http://www.bbc.co.uk/iplayer/a-z/%s' % letter
    html = get(url)

    items = []
    match=re.compile('<a href="/iplayer/brand/(.+?)".+?<span class="title">(.+?)</span>',re.DOTALL).findall (html)
    for url , name in match:
        url = "http://www.bbc.co.uk/iplayer/episodes/%s" % url
        thumbnail = get_icon_path('lists')
        context_items = []
        context_items.append(("[COLOR yellow][B]%s[/B][/COLOR] " % 'Add Favourite', 'XBMC.RunPlugin(%s)' %
        (plugin.url_for(add_favourite, name=name, url=url, thumbnail=thumbnail, is_episode=False))))
        context_items.append(("[COLOR yellow][B]%s[/B][/COLOR] " % 'Add to PVR', 'XBMC.RunPlugin(%s)' %
        (plugin.url_for(add_pvr, name=name, url=url, thumbnail=thumbnail, is_episode=False))))
        items.append({
            'label': unescape(name),
            'path': plugin.url_for('page',url=url),
            'thumbnail':thumbnail,
            'context_menu': context_items,
        })
    return items


@plugin.route('/channel_a_z')
def channel_a_z():
    channel_list = [
        ('bbcone',           'bbc_one_hd',              'BBC One'),
        ('bbctwo',           'bbc_two_hd',              'BBC Two'),
        ('tv/bbcthree',      'bbc_three_hd',          'BBC Three'),
        ('bbcfour',          'bbc_four_hd',            'BBC Four'),
        ('tv/cbbc',          'cbbc_hd',                    'CBBC'),
        ('tv/cbeebies',      'cbeebies_hd',            'CBeebies'),
        ('tv/bbcnews',       'bbc_news24',     'BBC News Channel'),
        ('tv/bbcparliament', 'bbc_parliament',   'BBC Parliament'),
        ('tv/bbcalba',       'bbc_alba',                   'Alba'),
        ('tv/s4c',           's4cpbs',                      'S4C'),
    ]
    items = []
    for id, img, name in channel_list:
        icon = 'special://home/addons/plugin.video.bbc/resources/img/%s.png' % img
        url = "http://www.bbc.co.uk/%s/a-z" % id
        items.append({
            'label' : name,
            'thumbnail' : icon,
            'path' : plugin.url_for('page',url=url),
            'is_playable' : False
        })
    return items


@plugin.route('/page/<url>')
def page(url):
    global big_list_view
    big_list_view = True
    headers = {'User-Agent':'Mozilla/5.0 (Windows NT 6.1; rv:50.0) Gecko/20100101 Firefox/50.0'}
    html = get(url)

    items = []
    html_items=html.split('data-ip-id="')
    for p in html_items:
        IPID=p.split('"')[0]
        urls=re.compile('href="(.+?)"').findall (p)
        #log(urls)
        episode_url = ''
        episodes_url = ''
        for u in urls:
            if u.startswith('/iplayer/episode/'):
                episode_url = 'http://www.bbc.co.uk%s' % u
            elif u.startswith('/iplayer/episodes/'):
                episodes_url = 'http://www.bbc.co.uk%s' % u
            elif u.startswith('http://www.bbc.co.uk/iplayer/episode/'):
                episode_url = u
            elif u.startswith('http://www.bbc.co.uk/iplayer/episodes/'):
                episodes_url = u

        name = re.compile('title="(.+?)"').findall (p)[0]

        episode = None
        match = re.compile('Episode ([0-9]*)$').search (name)
        if match:
            episode = int(match.group(1))
        else:
            match = re.compile('Series [0-9]*: ([0-9]*)\.').search (name)
            if match:
                episode = int(match.group(1))
            else:
                match = re.compile(', ([0-9]*)\.').search (name)
                if match:
                    episode = int(match.group(1))
        group = ''
        match=re.compile('top-title">(.+?)<').findall (p)
        if match:
            group = match[0]

        iconimage = get_icon_path('tv')
        match=re.compile('img src="(.+?)"').findall (p)
        if match:
            iconimage = match[0]
        else:
            match=re.compile('srcset="(.+?)"').findall (p)
            if match:
                iconimage = match[0]

        day = ''
        month = ''
        year = ''
        match=re.compile('First shown: (.*?) (.*?) (.*)').search (p)
        if match:
            day = match.group(1)
            month = match.group(2)
            year = match.group(3)
        else:
            match=re.compile('First shown: (.*)').search (p)
            if match:
                day = "1"
                month = "Jan"
                year = match.group(1)

        aired = ''
        if month:
            monthDict={
                'Jan':'01', 'Feb':'02', 'Mar':'03', 'Apr':'04', 'May':'05', 'Jun':'06',
                'Jul':'07', 'Aug':'08', 'Sep':'09', 'Oct':'10', 'Nov':'11', 'Dec':'12'}
            if month in monthDict:
                month = monthDict[month]
            aired = year + '-' + month + '-' + day

        plot = ''
        match=re.compile('<p class="synopsis">(.+?)</p>').findall (p)
        if match:
            plot = match[0]

        if plugin.get_setting('autoplay') == 'true':
            autoplay = True
            action = "autoplay"
        else:
            autoplay = False
            action = "list"
        context_items = []
        if episode_url:
            name = unescape(name)
            if plugin.get_setting('proxy') == 'true':
                url = plugin.url_for('proxy_play_episode',url=episode_url,name=name,thumbnail=iconimage,action=action)
                autoplay = False
            else:
                url = plugin.url_for('play_episode',url=episode_url,name=name,thumbnail=iconimage,action=action)
            context_items.append(("[COLOR yellow][B]%s[/B][/COLOR] " % 'Add Favourite', 'XBMC.RunPlugin(%s)' %
            (plugin.url_for(add_favourite, name=name, url=episode_url, thumbnail=iconimage, is_episode=True))))
            context_items.append(("[COLOR yellow][B]%s[/B][/COLOR] " % 'Add to PVR', 'XBMC.RunPlugin(%s)' %
            (plugin.url_for(add_pvr, name=name, url=episode_url, thumbnail=iconimage, is_episode=True))))
            context_items.append(("[COLOR yellow][B]%s[/B][/COLOR] " % 'Cache', 'XBMC.RunPlugin(%s)' %
            (plugin.url_for('play_episode',url=episode_url,name=name,thumbnail=iconimage,action="cache"))))
            items.append({
                'label': name,
                'path': url,
                'thumbnail':iconimage,
                'is_playable' : autoplay,
                'context_menu': context_items,
                'info': {'aired':aired, 'plot':unescape(plot), 'episode': episode},
            })
        context_items = []
        if episodes_url:
            name = unescape(group)
            url = plugin.url_for('page',url=episodes_url)
            context_items.append(("[COLOR yellow][B]%s[/B][/COLOR] " % 'Add Favourite', 'XBMC.RunPlugin(%s)' %
            (plugin.url_for(add_favourite, name=name, url=episodes_url, thumbnail=iconimage, is_episode=False))))
            context_items.append(("[COLOR yellow][B]%s[/B][/COLOR] " % 'Add to PVR', 'XBMC.RunPlugin(%s)' %
            (plugin.url_for(add_pvr, name=name, url=episodes_url, thumbnail=iconimage, is_episode=False))))
            context_items.append(("[COLOR yellow][B]%s[/B][/COLOR] " % 'Cache All', 'XBMC.RunPlugin(%s)' %
            (plugin.url_for('cache_all',url=episodes_url))))
            items.append({
                'label': "[COLOR %s][B]%s[/B][/COLOR]" % (remove_formatting(plugin.get_setting('group.colour')),name),
                'path': url,
                'thumbnail':iconimage,
                'context_menu': context_items,
            })

    next_page = re.compile('<span class="next.*?href="(.*?)"',flags=(re.DOTALL | re.MULTILINE)).search (html)
    if next_page:
        url = 'http://www.bbc.co.uk%s' % unescape(next_page.group(1))
        if 'page=' in url:
            if plugin.get_setting('page') == 'true' and "search" not in url:
                number = url.split('page=')[-1]
                if int(number) > 5:
                    xbmcgui.Dialog().notification("BBC TV","Page "+number,time=100,sound=False)
                items = items + page(url)
            else:
                url = plugin.url_for('page',url=url)
                items.append({
                    'label': "[COLOR orange]Next Page >>[/COLOR]",
                    'path': url,
                    'thumbnail':get_icon_path("item_next"),
                })

    plugin.set_content('episodes')
    #BUG date doesn't work
    #return plugin.finish(items, sort_methods=['playlist_order','label','date'])
    return items

@plugin.route('/add_pvr/<name>/<url>/<thumbnail>/<is_episode>')
def add_pvr(name,url,thumbnail,is_episode):
    pvrs = plugin.get_storage('pvrs')
    pvrs[name] = '|'.join((url,thumbnail,is_episode))

@plugin.route('/remove_pvr/<name>')
def remove_pvr(name):
    pvrs = plugin.get_storage('pvrs')
    del pvrs[name]
    xbmc.executebuiltin('Container.Refresh')

@plugin.route('/add_favourite/<name>/<url>/<thumbnail>/<is_episode>')
def add_favourite(name,url,thumbnail,is_episode):
    favourites = plugin.get_storage('favourites')
    favourites[name] = '|'.join((url,thumbnail,is_episode))

@plugin.route('/remove_favourite/<name>')
def remove_favourite(name):
    favourites = plugin.get_storage('favourites')
    del favourites[name]
    xbmc.executebuiltin('Container.Refresh')

@plugin.route('/remove_search/<name>')
def remove_search(name):
    searches = plugin.get_storage('searches')
    del searches[name]
    xbmc.executebuiltin('Container.Refresh')

@plugin.route('/new_search')
def new_search():
    d = xbmcgui.Dialog()
    what = d.input("New Search")
    if what:
        searches = plugin.get_storage('searches')
        searches[what] = ''
        return search(what)

@plugin.route('/search/<what>')
def search(what):
    if not what:
        return

    url= 'http://www.bbc.co.uk/iplayer/search?q=%s' % what.replace(' ','%20')
    return page(url)

@plugin.route('/searches')
def searches():
    searches = plugin.get_storage('searches')
    items = []

    items.append({
        'label': 'New Search',
        'path': plugin.url_for('new_search'),
        'thumbnail':get_icon_path('search'),
    })
    for search in sorted(searches):
        context_items = []
        context_items.append(("[COLOR yellow][B]%s[/B][/COLOR] " % 'Remove Search', 'XBMC.RunPlugin(%s)' %
        (plugin.url_for(remove_search, name=search))))
        items.append({
            'label': search,
            'path': plugin.url_for('search',what=search),
            'thumbnail':get_icon_path('search'),
            'context_menu': context_items,
        })
    return items

@plugin.route('/favourites')
def favourites():
    global big_list_view
    big_list_view = True
    favourites = plugin.get_storage('favourites')
    items = []
    if plugin.get_setting('autoplay') == 'true':
        autoplay = True
        action = "autoplay"
    else:
        autoplay = False
        action = "list"
    for name in sorted(favourites):
        fav = favourites[name]
        url,iconimage,is_episode = fav.split('|')
        context_items = []
        context_items.append(("[COLOR yellow][B]%s[/B][/COLOR] " % 'Remove Favourite', 'XBMC.RunPlugin(%s)' %
        (plugin.url_for(remove_favourite, name=name))))
        if is_episode == "True":
            context_items.append(("[COLOR yellow][B]%s[/B][/COLOR] " % 'Cache', 'XBMC.RunPlugin(%s)' %
            (plugin.url_for('play_episode',url=url,name=name,thumbnail=iconimage,action="cache"))))
            items.append({
                'label': unescape(name),
                'path': plugin.url_for('play_episode',url=url,name=name,thumbnail=iconimage,action=action),
                'thumbnail':iconimage,
                'is_playable' : autoplay,
                'context_menu': context_items,
            })
        else:
            context_items.append(("[COLOR yellow][B]%s[/B][/COLOR] " % 'Cache All', 'XBMC.RunPlugin(%s)' %
            (plugin.url_for('cache_all',url=url))))
            items.append({
                'label': "[COLOR %s][B]%s[/B][/COLOR]" % (remove_formatting(plugin.get_setting('group.colour')),unescape(name)),
                'path': plugin.url_for('page',url=url),
                'thumbnail':iconimage,
                'is_playable' : False,
                'context_menu': context_items,
            })
    return items

@plugin.route('/pvr_list')
def pvr_list():
    global big_list_view
    big_list_view = True
    pvrs = plugin.get_storage('pvrs')
    items = []
    if plugin.get_setting('autoplay') == 'true':
        autoplay = True
        action = "autoplay"
    else:
        autoplay = False
        action = "list"
    for name in sorted(pvrs):
        fav = pvrs[name]
        url,iconimage,is_episode = fav.split('|')
        context_items = []
        context_items.append(("[COLOR yellow][B]%s[/B][/COLOR] " % 'Remove from PVR', 'XBMC.RunPlugin(%s)' %
        (plugin.url_for(remove_pvr, name=name))))
        if is_episode == "True":
            context_items.append(("[COLOR yellow][B]%s[/B][/COLOR] " % 'Cache', 'XBMC.RunPlugin(%s)' %
            (plugin.url_for('play_episode',url=url,name=name,thumbnail=iconimage,action="cache"))))
            items.append({
                'label': unescape(name),
                'path': plugin.url_for('play_episode',url=url,name=name,thumbnail=iconimage,action=action),
                'thumbnail':iconimage,
                'is_playable' : autoplay,
                'context_menu': context_items,
            })
        else:
            context_items.append(("[COLOR yellow][B]%s[/B][/COLOR] " % 'Cache All', 'XBMC.RunPlugin(%s)' %
            (plugin.url_for('cache_all',url=url))))
            items.append({
                'label': "[COLOR %s][B]%s[/B][/COLOR]" % (remove_formatting(plugin.get_setting('group.colour')),unescape(name)),
                'path': plugin.url_for('page',url=url),
                'thumbnail':iconimage,
                'is_playable' : False,
                'context_menu': context_items,
            })
    return items

@plugin.route('/categories')
def categories():
    url = 'http://www.bbc.co.uk/iplayer'
    headers = {'User-Agent':'Mozilla/5.0 (Windows NT 6.1; rv:50.0) Gecko/20100101 Firefox/50.0'}
    html = get(url)
    match = re.compile(
        '<a href="(.*?/iplayer/categories/.+?)".*?>(.+?)</a>'
        ).findall(html)

    items = []
    if plugin.get_setting('categories') == '0':
        order = "atoz"
    else:
        order = "dateavailable"
    for url, name in match:
        if name.startswith('{'):
            continue
        if url.startswith('http'):
            url = '%s/all?sort=%s' % (url,order)
        else:
            url = 'http://www.bbc.co.uk%s/all?sort=%s' % (url,order)

        items.append({
            'label': "%s" % unescape(name),
            'path': plugin.url_for('page',url=url),
            'thumbnail':get_icon_path('lists'),
        })
    return items

@plugin.route('/highlights/<url>')
def highlights(url):
    #url = 'http://www.bbc.co.uk/iplayer'
    headers = {'User-Agent':'Mozilla/5.0 (Windows NT 6.1; rv:50.0) Gecko/20100101 Firefox/50.0'}
    html = get(url)
    match = re.compile(
        'href="(/iplayer/episode/.*?)"'
        ).findall(html)
    items = []
    if plugin.get_setting('autoplay') == 'true':
        autoplay = True
        action = "autoplay"
    else:
        autoplay = False
        action = "list"
    for episode_url in match:
        if episode_url.startswith('/iplayer'):
            episode_url = 'https://www.bbc.co.uk' + episode_url
        title = episode_url.split('/')[-1].split('#')[0]
        title = title.replace('-',' ').title()
        url = plugin.url_for('play_episode',url=episode_url,name=title,thumbnail=get_icon_path('lists'),action=action)
        items.append({
            'label': title,
            'path': url,
            'thumbnail':get_icon_path('lists'),
            'is_playable' : autoplay,
        })

    return sorted(items, key=lambda x: x['label'])

@plugin.route('/channel_highlights')
def channel_highlights():
    items = []
    channel_list = [
        ('bbcone',           'bbc_one_hd',              'BBC One'),
        ('bbctwo',           'bbc_two_hd',              'BBC Two'),
        ('tv/bbcthree',      'bbc_three_hd',          'BBC Three'),
        ('bbcfour',          'bbc_four_hd',            'BBC Four'),
        ('tv/cbbc',          'cbbc_hd',                    'CBBC'),
        ('tv/cbeebies',      'cbeebies_hd',            'CBeebies'),
        ('tv/bbcnews',       'bbc_news24',     'BBC News Channel'),
        ('tv/bbcparliament', 'bbc_parliament',   'BBC Parliament'),
        ('tv/bbcalba',       'bbc_alba',                   'Alba'),
        ('tv/s4c',           's4cpbs',                      'S4C'),
    ]
    for id, img, name in channel_list:
        iconimage = get_icon_path(img)
        items.append({
            'label': name,
            'path': plugin.url_for('highlights',url='http://www.bbc.co.uk/' + id),
            'thumbnail':iconimage,
        })
    return items

@plugin.route('/live_mpd')
def live_mpd():
    channel_list = [
            ('bbc_one_hd',                       'BBC One'),
            ('bbc_two_hd',                       'BBC Two'),
            ('bbc_four_hd',                      'BBC Four'),
            ('cbbc_hd',                          'CBBC'),
            ('cbeebies_hd',                      'CBeebies'),
            ('bbc_news24',                       'BBC News Channel'),
            ('bbc_parliament',                   'BBC Parliament'),
            ('bbc_alba',                         'Alba'),
            ('s4cpbs',                           'S4C'),
            ('bbc_one_london',                   'BBC One London'),
            ('bbc_one_scotland_hd',              'BBC One Scotland'),
            ('bbc_one_northern_ireland_hd',      'BBC One Northern Ireland'),
            ('bbc_one_wales_hd',                 'BBC One Wales'),
            ('bbc_two_scotland',                 'BBC Two Scotland'),
            ('bbc_two_northern_ireland_digital', 'BBC Two Northern Ireland'),
            ('bbc_two_wales_digital',            'BBC Two Wales'),
            ('bbc_two_england',                  'BBC Two England',),
            ('bbc_one_cambridge',                'BBC One Cambridge',),
            ('bbc_one_channel_islands',          'BBC One Channel Islands',),
            ('bbc_one_east',                     'BBC One East',),
            ('bbc_one_east_midlands',            'BBC One East Midlands',),
            ('bbc_one_east_yorkshire',           'BBC One East Yorkshire',),
            ('bbc_one_north_east',               'BBC One North East',),
            ('bbc_one_north_west',               'BBC One North West',),
            ('bbc_one_oxford',                   'BBC One Oxford',),
            ('bbc_one_south',                    'BBC One South',),
            ('bbc_one_south_east',               'BBC One South East',),
            ('bbc_one_west',                     'BBC One West',),
            ('bbc_one_west_midlands',            'BBC One West Midlands',),
            ('bbc_one_yorks',                    'BBC One Yorks',),
    ]
    items = []
    for id,name in channel_list:
        icon = 'special://home/addons/plugin.video.bbc.live.mpd/resources/media/%s.png' % id
        path = 'http://a.files.bbci.co.uk/media/live/manifesto/audio_video/simulcast/dash/uk/dash_pc/ak/%s.mpd' % id
        item = ListItem(label=name,icon=icon,path=path)
        item.set_property('inputstreamaddon', 'inputstream.adaptive')
        item.set_property('inputstream.adaptive.manifest_type', 'mpd')
        item.set_is_playable(True)
        items.append(item)
    return items

@plugin.route('/')
def index():
    context_items = []
    context_items.append(("[COLOR yellow][B]%s[/B][/COLOR] " % 'PVR Service', 'XBMC.RunPlugin(%s)' %
    (plugin.url_for('start_pvr_service'))))
    xbmc_version = float(xbmc.getInfoLabel( "System.BuildVersion" ).split()[0])

    items = [
    {
        'label': 'Live',
        'path': plugin.url_for('live'),
        'thumbnail':get_icon_path('tv'),
    }]
    #{
    #    'label': 'Red Button',
    #    'path': plugin.url_for('red_button'),
    #    'thumbnail':get_icon_path('red_button'),
    #},
    #{
    #    'label': 'Schedules',
    #    'path': plugin.url_for('schedules'),
    #    'thumbnail':get_icon_path('tv'),
    #},
    if xbmc_version > 17.0:
        items.append({
            'label': 'Highlights',
            'path': plugin.url_for('highlights',url='https://www.bbc.co.uk/iplayer'),
            'thumbnail':get_icon_path('top'),
        })
    items.append({
        'label': 'Channel Highlights',
        'path': plugin.url_for('channel_highlights'),
        'thumbnail':get_icon_path('top'),
    })
    items.append({
        'label': 'Most Popular',
        'path': plugin.url_for('highlights',url='https://www.bbc.co.uk/iplayer/group/most-popular'),
        'thumbnail':get_icon_path('top'),
    })
    items.append({
        'label': 'Search',
        'path': plugin.url_for('searches'),
        'thumbnail':get_icon_path('search'),
    })
    items.append({
        'label': 'A-Z',
        'path': plugin.url_for('alphabet'),
        'thumbnail':get_icon_path('lists'),
    })
    #{
    #    'label': 'Channel A-Z',
    #    'path': plugin.url_for('channel_a_z'),
    #    'thumbnail':get_icon_path('lists'),
    #},
    items.append({
        'label': 'Categories',
        'path': plugin.url_for('categories'),
        'thumbnail':get_icon_path('lists'),
    })
    items.append({
        'label': 'Favourites',
        'path': plugin.url_for('favourites'),
        'thumbnail':get_icon_path('favourites'),
    })
    items.append({
        'label': 'PVR',
        'path': plugin.url_for('pvr_list'),
        'thumbnail':get_icon_path('clock'),
        'context_menu': context_items,
    })
    items.append({
        'label': 'Make Live Playlist',
        'path': plugin.url_for('make_playlist'),
        'thumbnail':get_icon_path('settings'),
    })
    if plugin.get_setting('mpd') == 'true':
        item = {
            'label': 'Live MPD',
            'path': plugin.url_for('live_mpd'),
            'thumbnail':get_icon_path('tv'),
        }
        items.insert(1,item)
    return items


if __name__ == '__main__':
    plugin.run()
    if big_list_view == True:
        view_mode = int(plugin.get_setting('view_mode'))
        if view_mode:
            plugin.set_view_mode(view_mode)