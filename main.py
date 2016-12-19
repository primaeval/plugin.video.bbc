# Acknowledgements: Lots of code from Mikey1234. Thanks.

from xbmcswift2 import Plugin
from xbmcswift2 import actions
import xbmc,xbmcaddon,xbmcvfs,xbmcgui,xbmcplugin
import re
import requests,urllib
import os,sys

plugin = Plugin()
big_list_view = False

def log(v):
    xbmc.log(repr(v))

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
        items.append({
            'label' : name,
            'thumbnail' : icon,
            'path' : url,
            'is_playable' : True
        })

    device = 'hls_mobile_wifi'
    for id, name  in sd :
        url='http://a.files.bbci.co.uk/media/live/manifesto/audio_video/simulcast/hls/uk/%s/%s/%s.m3u8' % (device, provider, id)
        icon = 'special://home/addons/plugin.video.bbc/resources/img/%s.png' % id
        items.append({
            'label' : name,
            'thumbnail' : icon,
            'path' : url,
            'is_playable' : True
        })

    return items

@plugin.route('/play_episode/<url>/<name>/<thumbnail>/<action>')
def play_episode(url,name,thumbnail,action):
    headers = {'User-Agent':'Mozilla/5.0 (Windows NT 6.1; rv:50.0) Gecko/20100101 Firefox/50.0'}
    r = requests.get(url,headers=headers)

    if r.status_code != requests.codes.ok:
        return
    html = r.content
    vpid=re.compile('"vpid":"(.+?)"').findall(html)[0]

    if not vpid:
        return

    URL=[]
    if int(plugin.get_setting('catchup'))==1:
        NEW_URL= "http://open.live.bbc.co.uk/mediaselector/5/select/version/2.0/mediaset/stb-all-h264/vpid/%s" % vpid

        r = requests.get(NEW_URL,headers=headers)
        if r.status_code != requests.codes.ok:
            return
        html = r.content

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


            if int(plugin.get_setting('supplier'))==0:
                url="%s://%s:%s/%s?%s playpath=%s?%s" % (protocol,server,port,app,auth,playpath,auth)
                if supplier == 'akamai':
                    res=playpath.split('secure/')[1]
                    resolution=res.split('kbps')[0]
                    URL.append([(eval(resolution)),url])

    else:
        NEW_URL= "http://open.live.bbc.co.uk/mediaselector/5/select/version/2.0/mediaset/iptv-all/vpid/%s" % vpid

        r = requests.get(NEW_URL,headers=headers)
        if r.status_code != requests.codes.ok:
            return
        html = r.content

        hls = re.compile('bitrate="(.+?)".+?connection href="(.+?)".+?transferFormat="(.+?)"/>').findall(html)
        for resolution, url, supplier in hls:
            server=url.split('//')[1]
            server=server.split('/')[0]

            if int(plugin.get_setting('supplier'))==0:
                URL.append([(eval(resolution)),url])

            if int(plugin.get_setting('supplier'))==1:
                URL.append([(eval(resolution)),url])

    if action == "autoplay":
        URL=max(URL)[1]
        item =  {
            'label': name,
            'path': URL,
            'thumbnail': thumbnail
        }
        return plugin.play_video(item)
    elif action == "list":
        items = []
        for u in sorted(URL, reverse=True):
            items.append({
                'label': "%s [%d]" % (name, u[0]),
                'path': u[1],
                'thumbnail': thumbnail,
                'is_playable': True
            })
        return items
    elif action == "download":
        pass


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
    headers = {'User-Agent':'Mozilla/5.0 (Windows NT 6.1; rv:50.0) Gecko/20100101 Firefox/50.0'}
    r = requests.get(url,headers=headers)
    if r.status_code != requests.codes.ok:
        return
    html = r.content

    items = []
    match=re.compile('<a href="/iplayer/brand/(.+?)".+?<span class="title">(.+?)</span>',re.DOTALL).findall (html)
    for url , name in match:
        url = "http://www.bbc.co.uk/iplayer/episodes/%s" % url
        items.append({
            'label': unescape(name),
            'path': plugin.url_for('page',url=url),
            'thumbnail':get_icon_path('lists'),
        })
    return items

@plugin.route('/page/<url>')
def page(url):
    headers = {'User-Agent':'Mozilla/5.0 (Windows NT 6.1; rv:50.0) Gecko/20100101 Firefox/50.0'}
    r = requests.get(url,headers=headers)
    if r.status_code != requests.codes.ok:
        return
    html = r.content

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

        name=re.compile('title="(.+?)"').findall (p)[0]
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
            url = plugin.url_for('play_episode',url=episode_url,name=name,thumbnail=iconimage,action=action)
            context_items.append(("[COLOR yellow][B]%s[/B][/COLOR] " % 'Add Favourite', 'XBMC.RunPlugin(%s)' %
            (plugin.url_for(add_favourite, name=name, url=episode_url, thumbnail=iconimage, is_episode=True))))
            context_items.append(("[COLOR yellow][B]%s[/B][/COLOR] " % 'Download', 'XBMC.RunPlugin(%s)' %
            (plugin.url_for('play_episode',url=episode_url,name=name,thumbnail=iconimage,action="download"))))
            items.append({
                'label': name,
                'path': url,
                'thumbnail':iconimage,
                'is_playable' : autoplay,
                'context_menu': context_items,
            })
        context_items = []
        if episodes_url:
            name = unescape(group)
            url = plugin.url_for('page',url=episodes_url)
            context_items.append(("[COLOR yellow][B]%s[/B][/COLOR] " % 'Add Favourite', 'XBMC.RunPlugin(%s)' %
            (plugin.url_for(add_favourite, name=name, url=episodes_url, thumbnail=iconimage, is_episode=False))))
            items.append({
                'label': "[B]%s[/B]" % name,
                'path': url,
                'thumbnail':iconimage,
                'context_menu': context_items,
            })
    next_page = re.compile('href="([^"]*?&amp;page=[0-9]*)"> Next').search (html)
    if next_page:
        url = 'http://www.bbc.co.uk%s' % unescape(next_page.group(1))
        url = plugin.url_for('page',url=url)
        items.append({
            'label': "[COLOR orange]Next Page >>[/COLOR]",
            'path': url,
            'thumbnail':get_icon_path("item_next"),
        })
    return items

@plugin.route('/add_favourite/<name>/<url>/<thumbnail>/<is_episode>')
def add_favourite(name,url,thumbnail,is_episode):
    favourites = plugin.get_storage('favourites')
    favourites[name] = '|'.join((url,thumbnail,is_episode))

@plugin.route('/remove_favourite/<name>')
def remove_favourite(name):
    favourites = plugin.get_storage('favourites')
    del favourites[name]
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
    for s in sorted(searches):
        items.append({
            'label': s,
            'path': plugin.url_for('search',what=s),
            'thumbnail':get_icon_path('search'),
        })
    return items

@plugin.route('/favourites')
def favourites():
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
            items.append({
                'label': unescape(name),
                'path': plugin.url_for('play_episode',url=url,name=name,thumbnail=iconimage,action=action),
                'thumbnail':iconimage,
                'is_playable' : autoplay,
                'context_menu': context_items,
            })
        else:
            items.append({
                'label': "[B]%s[/B]" % unescape(name),
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
    r = requests.get(url,headers=headers)
    if r.status_code != requests.codes.ok:
        return
    html = r.content
    match = re.compile(
        '<a href="/iplayer/categories/(.+?)" class="stat">(.+?)</a>'
        ).findall(html)
    items = []
    for url, name in match:
        url = 'http://www.bbc.co.uk/iplayer/categories/%s/all?sort=atoz' % url
        items.append({
            'label': "[B]%s[/B]" % unescape(name),
            'path': plugin.url_for('page',url=url),
            'thumbnail':get_icon_path('lists'),
        })
    return items


@plugin.route('/')
def index():
    items = [
    {
        'label': 'Live',
        'path': plugin.url_for('live'),
        'thumbnail':get_icon_path('tv'),
    },
    {
        'label': 'Most Popular',
        'path': plugin.url_for('page',url='http://www.bbc.co.uk/iplayer/group/most-popular'),
        'thumbnail':get_icon_path('top'),
    },
    {
        'label': 'Search',
        'path': plugin.url_for('searches'),
        'thumbnail':get_icon_path('search'),
    },
    {
        'label': 'A-Z',
        'path': plugin.url_for('alphabet'),
        'thumbnail':get_icon_path('lists'),
    },
    {
        'label': 'Categories',
        'path': plugin.url_for('categories'),
        'thumbnail':get_icon_path('top'),
    },
    {
        'label': 'Favourites',
        'path': plugin.url_for('favourites'),
        'thumbnail':get_icon_path('top'),
    },


    ]
    return items


if __name__ == '__main__':
    plugin.run()
    if big_list_view == True:
        view_mode = int(plugin.get_setting('view_mode'))
        if view_mode:
            plugin.set_view_mode(view_mode)