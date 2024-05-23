"""
The server module instantiates the web server that hosts the API for the
content Provider and the implementation of the plain HTML Vanilla user interface.

SWENG861 Project, AskMinstrel
  André Wagner
  July, 2020
"""
# pylint: disable=bad-continuation, invalid-name

import argparse
import logging
from pathlib import Path
import cherrypy

from .provider import Provider
from .vanilla import VanillaUI

class Minstrel():
    """ Create endpoints for provider API. """
    # pylint: disable=no-self-use

    def __init__(self, provider: Provider):
        self.search = Search(provider)
        self.artist = Artist(provider)
        self.album = Album(provider)
        self.track = Track(provider)

    @cherrypy.expose
    def index(self):
        """ Show landing page with links. """
        return """
        <HTML><H1>AskMinstrel Server</H1>
            <a href="/vanilla">Use Vanilla UI</a><br>
            <a href="/vue">Use Vue.js UI</a><br>
            <a href="/help">Documentation</a><br>
        </HTML>
        """

    @cherrypy.expose
    def help(self):
        """ Show PyDoc generated documentation. """
        # update html with `python -m PyDoc -w askminstrel`
        raise cherrypy.InternalRedirect('/docs')

@cherrypy.expose
@cherrypy.tools.json_out()
@cherrypy.popargs('qtype', 'query')
class Search():
    """ Provide REST API for client searches.

        Only GET is implemented.
        - :param qtype: query type is one of (artist, album, track)
        - :param query: query string of keywords and field filters
        - :returns: JSON object with results
    """
    # TODO: create JSON schemas for reply objects
    def __init__(self, p: Provider):
        self._provider = p

    def GET(self, qtype, query):
        """ handle either of the following
        * GET /search/{qtype}/{query}
        * GET /search?qtype={}&query={}
        """
        logging.info("<%s>: invoked with %s", self.__class__.__name__, str((qtype,query)))

        if qtype not in ('artist', 'album', 'track'):
            raise cherrypy.HTTPError(404)

        payload = {qtype: self._provider.search(qtype, query)}
        logging.debug("returning %s ...abridged ... %s",
            str(payload)[:63], str(payload)[-31:])
        return payload

@cherrypy.expose
@cherrypy.tools.json_out()
@cherrypy.popargs('item_id')
class Artist():
    """ Provide REST API for Artist detail.

        Only GET is implemented.
        - :param item_id: unique identifier obtained from search query
        - :returns: JSON object with results
    """
    def __init__(self, p: Provider):
        self._provider = p

    def GET(self, item_id):
        """ handle either of the following
            * GET /artist/{item_id}
            * GET /artist?item_id={}
        """
        logging.info("<%s>: invoked with %s", self.__class__.__name__, item_id)

        payload = self._provider.artist(item_id)
        logging.debug("returning %s ...abridged ... %s",
            str(payload)[:63], str(payload)[-31:])
        return payload

@cherrypy.expose
@cherrypy.tools.json_out()
@cherrypy.popargs('item_id')
class Album():
    """ Provide REST API for Album detail.

        Only GET is implemented.
        - :param item_id: unique identifier obtained from search query
        - :returns: JSON object with results
    """
    def __init__(self, p: Provider):
        self._provider = p

    def GET(self, item_id):
        """ handle either of the following
            * GET /album/{item_id}
            * GET /album?item_id={}
        """
        logging.info("<%s>: invoked with %s", self.__class__.__name__, item_id)

        payload = self._provider.album(item_id)
        logging.debug("returning %s ...abridged ... %s",
            str(payload)[:63], str(payload)[-31:])
        return payload

@cherrypy.expose
@cherrypy.tools.json_out()
@cherrypy.popargs('item_id')
class Track():
    """ Provide REST API for Track detail.

        Only GET is implemented.
        - :param item_id: unique identifier obtained from search query
        - :returns: JSON object with results
    """
    def __init__(self, p: Provider):
        self._provider = p

    def GET(self, item_id):
        """ handle either of the following
            * GET /track/{item_id}
            * GET /track?item_id={}
        """
        logging.info("<%s>: invoked with %s", self.__class__.__name__, item_id)

        payload = self._provider.track(item_id)
        logging.debug("returning %s ...abridged ... %s",
            str(payload)[:63], str(payload)[-31:])
        return payload


def minstrel_server(port=50861, memoize=True):
    """ Configure and launch application server. """
    minstrel = Minstrel(Provider(memoize=memoize))
    # register all subapps in Minstrel for method dispatch (GET, PUT, POST, etc.)
    dispatch = {'request.dispatch': cherrypy.dispatch.MethodDispatcher()}
    restful = {'/'+url : dispatch for url in minstrel.__dict__}
    config = {
        'global': {
            'log.screen': False,
            'server.socket_port': port,
            'server.socket_timeout': 60,  # MAKE SOCKET NON-BLOCKING
            'engine.autoreload.on': False,
            'tools.staticdir.root': Path.cwd()
        },
        '/':{
            'tools.sessions.on': True,
            'tools.sessions.timeout': 60
        },
        '/docs': {
            'tools.staticdir.on': True,
            'tools.staticdir.dir': 'pydocs',
            'tools.staticdir.index': 'askminstrel.html'
        },
        # register Vue UI as statics since as the work is done client side
        '/vue': {
            'tools.staticdir.on': True,
            'tools.staticdir.dir': 'vue/dist',
            'tools.staticdir.index': 'index.html'
        }
    }
    config.update(restful)
    # register Vanilla UI as a separate cherrypy app with standard dispatch/routing
    # this could even be on another server if taking a microservice approach
    cherrypy.tree.mount(VanillaUI(), '/vanilla', {'/':{'tools.sessions.on': True}}
    )
    cherrypy.quickstart(minstrel, '/', config)

def cli():
    """ Parse optional command line arguments and launch minstrel_server. 
    
    Typically launched as a module via __main__.py, e.g. `python -m askminstrel`.
    """
    def _ephemeral(p):
        if int(p) in range(49152,65536):
            return int(p)
        else:
            raise argparse.ArgumentTypeError("must be in range(49152,65536)")

    parser = argparse.ArgumentParser(description="""
    AskMinstrel - a web based client for all musical questions.  Launch and browse.
    """)
    parser.add_argument('-p', '--port', type=_ephemeral, default=50861, 
        help='ephemeral TCP/IP port for web server')
    parser.add_argument('--no-store', action='store_false', dest='memoize',
        help='disable and erase memoization')
    args = parser.parse_args()
    minstrel_server(**vars(args))
