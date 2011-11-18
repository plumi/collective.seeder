"""Event subscribers"""
import logging

from zope.component import adapter
from zope.component import getUtility
from zope.component import getSiteManager
from zope.interface.interfaces import IInterface
from zope.component.interfaces import ObjectEvent
from Products.CMFCore.interfaces import IContentish
from zope.lifecycleevent.interfaces import IObjectModifiedEvent  
from Products.CMFCore.interfaces import IActionSucceededEvent 
from plone.registry.interfaces import IRegistry 
from Products.CMFCore.interfaces._content import IContentish 
import Zope2
import os
import os.path
import subprocess
import shutil
import sys
import time
import bencode
from hashlib import sha1 as sha

log = logging.getLogger('collective.transcode')

noncharacter_translate = {}
for i in xrange(0xD800, 0xE000):
    noncharacter_translate[i] = ord('-')
for i in xrange(0xFDD0, 0xFDF0):
    noncharacter_translate[i] = ord('-')
for i in (0xFFFE, 0xFFFF):
    noncharacter_translate[i] = ord('-')

@adapter(IContentish, IActionSucceededEvent)
def deleteTorrent(obj, event):
    try:
        registry = getUtility(IRegistry)
        types = registry['collective.seeder.interfaces.ISeederSettings.portal_types']
        torrent_dir = registry['collective.seeder.interfaces.ISeederSettings.torrent_dir']
        announce_urls = registry['collective.seeder.interfaces.ISeederSettings.announce_urls']
        safe_torrent_dir = registry['collective.seeder.interfaces.ISeederSettings.safe_torrent_dir']
        newTypes = [t.split(':')[0] for t in types]
        if unicode(obj.portal_type) not in newTypes:
            return
        fieldNames = [str(t.split(':')[1]) for t in types if ('%s:' % unicode(obj.portal_type)) in t]
        fts= Zope2.DB._storage.fshelper
        if not fieldNames:
            fields = [obj.getPrimaryField()]
        else:
            fields = [obj.getField(f) for f in fieldNames]
        for field in fields:
            oid = field.getUnwrapped(obj).getBlob()._p_oid
            if not oid:
                return
            #Symlink the blob object to the original filename
            blobDir = fts.getPathForOID(oid)
            blobName = os.listdir(blobDir)
            blobPath = os.path.join(blobDir,blobName[0])
            fileName = obj.UID() + '_' + field.getFilename(obj)
            linkPath = os.path.join(torrent_dir, fileName)

            #Check if the symlink exists and delete it
            if os.path.exists(linkPath):
                os.remove(linkPath)

            torrentName = fileName + '.torrent'
            torrentPath = os.path.join(torrent_dir, torrentName)
            torrentSafePath = safe_torrent_dir + '/' + fileName + '.torrent'
            #Check if the torrent files exist and delete them
            if os.path.exists(torrentPath):
                os.remove(torrentPath)
            if os.path.exists(torrentSafePath):
                os.remove(torrentSafePath)
    except Exception, e:
        pass

@adapter(IContentish, IActionSucceededEvent)
def addFile(obj, event):
    if not obj.UID():
        return
    try:
        registry = getUtility(IRegistry)
        types = registry['collective.seeder.interfaces.ISeederSettings.portal_types']
        torrent_dir = registry['collective.seeder.interfaces.ISeederSettings.torrent_dir']
        announce_urls = registry['collective.seeder.interfaces.ISeederSettings.announce_urls']
        safe_torrent_dir = registry['collective.seeder.interfaces.ISeederSettings.safe_torrent_dir']
        #Check if the torrent directory exists, otherwise create it
        if not os.path.exists(torrent_dir):
            os.makedirs(torrent_dir)
        #Check if the torrent safe directory exists, otherwise create it
        if not os.path.exists(safe_torrent_dir):
            os.makedirs(safe_torrent_dir)
        newTypes = [t.split(':')[0] for t in types]
        if unicode(obj.portal_type) not in newTypes:
            return
        fieldNames = [str(t.split(':')[1]) for t in types if ('%s:' % unicode(obj.portal_type)) in t]
        fts= Zope2.DB._storage.fshelper
        if not fieldNames:
            fields = [obj.getPrimaryField()]
        else:
            fields = [obj.getField(f) for f in fieldNames]
        for field in fields:
            oid = field.getUnwrapped(obj).getBlob()._p_oid
            if not oid:
                return
            #Symlink the blob object to the original filename
            blobDir = fts.getPathForOID(oid)
            blobName = os.listdir(blobDir)
            blobPath = os.path.join(blobDir,blobName[0])
            fileName = obj.UID() + '_' + field.getFilename(obj)
            linkPath = os.path.join(torrent_dir, fileName)
            os.symlink(blobPath, linkPath)

            torrentName = fileName + '.torrent'
            torrentPath = os.path.join(torrent_dir, torrentName)
            try:
                make_meta_file(linkPath, str(",".join(str(v) for v in announce_urls)), 262144)
                log.info("torrent created!")
            except Exception, e:
                log.error("Could not create torrent for %s\n Exception: %s" % (obj.absolute_url(), e))
            torrentSafePath = safe_torrent_dir + '/' + fileName + '.torrent'
            shutil.copyfile(torrentPath, torrentSafePath)           
    
    except Exception, e:
        log.error("Could not seed resource %s\n Exception: %s" % (obj.absolute_url(), e))
   



def make_meta_file(path, url, piece_length,
                   title=None, comment=None, safe=None, content_type=None,
                   target=None, webseeds=None, name=None, private=False,
                   created_by=None, trackers=None):
    data = {'creation date': int(gmtime())}
    if url:
        data['announce'] = url.strip()
    a, b = os.path.split(path)
    if not target:
        if b == '':
            f = a + '.torrent'
        else:
            f = os.path.join(a, b + '.torrent')
    else:
        f = target
    info = makeinfo(path, piece_length, name, content_type, private)

    #check_info(info)
    h = file(f, 'wb')

    data['info'] = info
    if title:
        data['title'] = title.encode("utf8")
    if comment:
        data['comment'] = comment.encode("utf8")
    if safe:
        data['safe'] = safe.encode("utf8")

    httpseeds = []
    url_list = []

    if webseeds:
        for webseed in webseeds:
            if webseed.endswith(".php"):
                httpseeds.append(webseed)
            else:
                url_list.append(webseed)

    if url_list:
        data['url-list'] = url_list
    if httpseeds:
        data['httpseeds'] = httpseeds
    if created_by:
        data['created by'] = created_by.encode("utf8")

    if trackers and (len(trackers[0]) > 1 or len(trackers) > 1):
        data['announce-list'] = trackers

    data["encoding"] = "UTF-8"

    h.write(bencode.bencode(data))
    h.close()


def makeinfo(path, piece_length, name = None,
             content_type = None, private=False):  # HEREDAVE. If path is directory,
                                    # how do we assign content type?
    def to_utf8(name):
        if isinstance(name, unicode):
            u = name
        else:
            try:
                u = decode_from_filesystem(name)
            except Exception, e:
                raise Exception('Could not convert file/directory name %r to '
                                  'Unicode. Either the assumed filesystem '
                                  'encoding "%s" is wrong or the filename contains '
                                  'illegal bytes.' % (name, get_filesystem_encoding()))

        if u.translate(noncharacter_translate) != u:
            raise Exception('File/directory name "%s" contains reserved '
                              'unicode values that do not correspond to '
                              'characters.' % name)
        return u.encode('utf-8')

    path = os.path.abspath(path)
    piece_count = 0
    if os.path.isdir(path):
        subs = subfiles(path)
        subs.sort()
        pieces = []
        sh = sha()
        done = 0
        fs = []
        totalsize = 0.0
        totalhashed = 0
        for p, f in subs:
            totalsize += os.path.getsize(f)
        if totalsize >= piece_length:
            import math
            num_pieces = math.ceil(float(totalsize) / float(piece_length))
        else:
            num_pieces = 1

        for p, f in subs:
            pos = 0
            size = os.path.getsize(f)
            p2 = [to_utf8(n) for n in p]
            if content_type:
                fs.append({'length': size, 'path': p2,
                           'content_type' : content_type}) # HEREDAVE. bad for batch!
            else:
                fs.append({'length': size, 'path': p2})
            h = file(f, 'rb')
            while pos < size:
                a = min(size - pos, piece_length - done)
                sh.update(h.read(a))
                done += a
                pos += a
                totalhashed += a

                if done == piece_length:
                    pieces.append(sh.digest())
                    piece_count += 1
                    done = 0
                    sh = sha()
            h.close()
            
        if name is not None:
            assert isinstance(name, unicode)
            name = to_utf8(name)
        else:
            name = to_utf8(os.path.split(path)[1])

        return {'pieces': ''.join(pieces),
            'piece length': piece_length, 'files': fs,
            'name': name,
            'private': private}
    else:
        size = os.path.getsize(path)
        if size >= piece_length:
            num_pieces = size / piece_length
        else:
            num_pieces = 1

        pieces = []
        p = 0
        h = file(path, 'rb')
        while p < size:
            x = h.read(min(piece_length, size - p))
            pieces.append(sha(x).digest())
            piece_count += 1
            p += piece_length
            if p > size:
                p = size
        h.close()
        if content_type is not None:
            return {'pieces': ''.join(pieces),
                'piece length': piece_length, 'length': size,
                'name': to_utf8(os.path.split(path)[1]),
                'content_type' : content_type,
                'private': private }
        return {'pieces': ''.join(pieces),
            'piece length': piece_length, 'length': size,
            'name': to_utf8(os.path.split(path)[1]),
            'private': private}


def subfiles(d):
    r = []
    stack = [([], d)]
    while stack:
        p, n = stack.pop()
        if os.path.isdir(n):
            for s in os.listdir(n):
                if s not in ignore and not s.startswith('.'):
                    stack.append((p + [s], os.path.join(n, s)))
        else:
            r.append((p, n))
    return r


def gmtime():
    return time.mktime(time.gmtime())

def get_filesystem_encoding():
    return sys.getfilesystemencoding()

def decode_from_filesystem(path):
    encoding = get_filesystem_encoding()
    if encoding == None:
        assert isinstance(path, unicode), "Path should be unicode not %s" % type(path)
        decoded_path = path
    else:
        assert isinstance(path, str), "Path should be str not %s" % type(path)
        decoded_path = path.decode(encoding)

    return decoded_path
