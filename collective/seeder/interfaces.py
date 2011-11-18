"""The product's interfaces"""
from zope import schema
from zope.interface import Interface

#TODO: add help messages
class ISeederSettings(Interface):
    """Seeder settings"""
    announce_urls = schema.Tuple(title = u'Announce url(s)', 
                                  value_type = schema.TextLine(title = u'announce_urls'),
                                  default = (u'udp://tracker.openbittorrent.com:80/announce',),
                                  )

    portal_types = schema.Tuple(title = u'Portal types to seed', 
                                value_type = schema.TextLine(title = u''),
                                default = (u'File',),
                                )

    torrent_dir = schema.TextLine(title = u'Torrent directory',
                                     description= u'The absolute path to the directory where to store the torrents',
                                     default = (u'torrents'),
                                   )

    safe_torrent_dir = schema.TextLine(title = u'Torrent safe directory',
                                     description= u'The absolute path to the directory where to copy the torrents to avoid deletion by certain torrent clients',
                                     default = (u'torrents_safe'),
                                   )
