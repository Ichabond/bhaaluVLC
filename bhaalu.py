import cookielib
import urllib
import urllib2
import json
import subprocess
import calendar


import time
from threading import Thread
from argparse import ArgumentParser


class UpdateThread(Thread):
    def __init__(self, uuid):
        self.stopped = False
        self.uuid = uuid
        Thread.__init__(self)  # Call the super construcor (Thread's one)

    def run(self):
        while not self.stopped:
            self.downloadValue()
            time.sleep(120)

    def downloadValue(self):
        urllib2.urlopen("http://tv-benl.bhaalu.com/rest/session/heartbeat/%s" % self.uuid)


def runHeartbeat(uuid):
    HeartbeatThread = UpdateThread(uuid)
    HeartbeatThread.daemon = True
    HeartbeatThread.start()


def timeSelector():
    selection = raw_input("When do you want to start watching? (enter for live) [HOUR:MINUTE]: ")
    if not selection:
        return ((calendar.timegm(time.gmtime()) / 10) - 12 ) * 10000
    currentTime = time.localtime()
    selectedTime = time.strptime(
        "%s %s %s %s" % (currentTime.tm_mday, currentTime.tm_mon, currentTime.tm_year, selection), "%d %m %Y %H:%M")
    if selectedTime > currentTime:
        selectedTime = time.strptime(
            "%s %s %s %s" % (currentTime.tm_mday - 1, currentTime.tm_mon, currentTime.tm_year, selection),
            "%d %m %Y %H:%M")
    return int((time.mktime(selectedTime) / 10) * 10000)


def channelSelector(channellist):
    print "Channels found:"
    filtered = [i for i in channellist if i['type'] == "BROADCAST"]
    for (counter, channel) in enumerate(filtered):
        outp = u'%s: %s' % (counter, channel['name'])
        print outp
    selection = int(raw_input('Select the channel you want to see [0-%s]: ' % (len(filtered) - 1)))
    return filtered[selection]['id']


def BhaaluLogin(username, password):
    cookiemonster = cookielib.CookieJar()
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookiemonster))
    opener.addheaders = [('User-agent', 'bhaalu_pc_macos;version=82')]
    urllib2.install_opener(opener)
    authentication_url = "https://benl.bhaalu.com/j_spring_security_check"
    payload = {
    'j_username': username,
    'j_password': password
    }
    data = urllib.urlencode(payload)
    req = urllib2.Request(authentication_url, data)
    urllib2.urlopen(req)
    urllib2.urlopen("https://benl.bhaalu.com/tv/watch")
    return cookiemonster


def BhaaluPlay(username, password):
    RESTURL = "http://tv-benl.bhaalu.com/rest/"
    cookiemonster = BhaaluLogin(username, password)
    for cookie in cookiemonster:
        if cookie.name == "WATCH_SESSION":
            urllib2.urlopen(
                RESTURL + "session/validate/%s?challenge_rsp=a0c0e43a82d43d397a1f91b4aa594dac" % cookie.value)
            urllib2.urlopen(RESTURL + "session/heartbeat/%s" % cookie.value)
            profileJSON = urllib2.urlopen(RESTURL + "profile/getAll?session=%s" % cookie.value)
            profileParsed = json.loads(profileJSON.read())
            urllib2.urlopen(
                RESTURL + "profile/activate?session=%s&profile=%s" % (cookie.value, profileParsed["defaultProfileId"]))
            currentTime = timeSelector()
            channelsJSON = urllib2.urlopen(RESTURL + "epg/channels/%s?_=%s" % (cookie.value, currentTime))
            channelsParsed = json.loads(channelsJSON.read())
            channelID = channelSelector(channelsParsed)
            tv_url = RESTURL + "v/index?s=%s&c=%s&t=%s&fmt=.m3u8" % (cookie.value, channelID, currentTime)
            runHeartbeat(cookie.value)
            subprocess.call(["/Applications/VLC.app/Contents/MacOS/VLC", tv_url, '-v',
                             ''':http-user-agent="Mozilla/5.0 (iPhone; CPU iPhone OS 6_1_4 like Mac OS X) AppleWebKit/536.26 (KHTML, like Gecko) Version/6.0 Mobile/10B350 Safari/8536.25"'''])

if __name__ == "__main__":
    parser = ArgumentParser(description="Start the schedule json server")
    parser.add_argument("username", help="Your Bhaalu username")
    parser.add_argument("password", help="Your Bhaalu password")
    args = parser.parse_args()
    BhaaluPlay(args.username, args.password)
