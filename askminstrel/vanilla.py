"""
The vanilla module creates the data driven HTML files that constitute the vanilla
user interface and defines the CherryPy routing app to create its endpoints.

SWENG861 Project, AskMinstrel
  André Wagner
  July, 2020
"""
# pylint: disable=bad-continuation, invalid-name
import logging
from functools import wraps
import cherrypy
import requests

def vanilla_page(f):
    """ Decorator to wrap pages in header/footer template. """
    @wraps(f)
    def _wrapper(*args, **kwargs):
        return '\n'.join(('<!DOCTYPE html><HTML>',
            '<style>',
                'body {font-family: sans-serif}',
                'dt {font-weight: bold; margin-top: 0.5em;}'
                'footer {font-style: italic}',
            '</style>',
            '<header><H1>AskMinstrel Vanilla</H1>',
            '<nav>',
            ' | '.join((
                '<a href="/">Home</a>',
                '<a href="/vanilla">Search</a>',
                '<a href="/help">Documentation</a>'
            )),
            '</nav></header><hr>',
            f(*args, **kwargs),
            '<hr><footer>PSU SWENG861 Project - AMWagner</footer>',
            '</HTML>'))
    return _wrapper


def render_detail_as_html(result_type, result_dict):
    """ Create an item detail component using <DL>. """

    def _dtdd_generator(result_item):
        """ Generate <DT> and <DD> tags with appropriate content for each item. """
        for k, v in result_item.items():
            if k == 'images':
                yield f"<dt>{k.title()}</dt><dd><img src={v} style='width:320x;height:320px;'></dd>"
            elif k == 'id':
                pass
            elif isinstance(v, dict):
                # Expect a dict to represent an item url to construct
                yield f"<dt>{k.title()}</dt><dd><a href=/vanilla/detail/{v['type']}/{v['id']}>{v['name']}</a></dd>"
            elif result_type == 'audio' and isinstance(v, float):
                yield f"<dt>{k.title()}</dt><dd><meter max=1.0 value={v}></meter></dd>"
            else:
                yield f"<dt>{k.title()}</dt><dd>{v}</dd>"

    output = f'<H2>{result_type.title()} Details</H2><dl>'
    output += ''.join(_dtdd_generator(result_dict))
    output += '</dl>'
    return output

def render_search_as_html(result_type, result_list):
    """ Create a search list component using <TABLE>. """

    def _th_generator(result_item):
        """ Generate <TH> tags from the item keys. """
        yield from (f"<th>{k.title()}</th>" for k in result_item.keys() if k != 'id')

    def _td_generator(result_item):
        """ Generate <TD> tags for each datum in an item. """
        for k, v in result_item.items():
            if k == 'name':
                # Every item has name and id from which a url can be constructed
                yield f"<td><a href=/vanilla/detail/{result_type}/{result_item['id']}>{v}</a></td>"
            elif k == 'images':
                # Don't provide alt attr so that spacing remains consistent
                yield f"<td><img src={v} style='width:64px;height:64px;'></td>"
            elif k == 'id':
                pass
            elif isinstance(v, dict):
                # Expect a dict to represent an item url to construct
                yield f"<td><a href=/vanilla/detail/{v['type']}/{v['id']}>{v['name']}</a></td>"
            else:
                yield f"<td>{v}</td>"

    try:
        assert 'id' in result_list[0].keys()
        assert 'name' in result_list[0].keys()
    except IndexError:
        # empty list means no search results
        output = f'No matching {result_type} found.'
    except AssertionError:
        # malformed data likely a change in content provider
        raise cherrypy.HTTPError(500)
    else:
        output = f'<H2>{result_type.title()} Search Results</H2><table>'
        output += '<tr>'+''.join(th for th in _th_generator(result_list[0]))+'</tr>'
        for result_item in result_list:
            output += '<tr>'+''.join(td for td in _td_generator(result_item))+'</tr>'
        output += '</table>'
    return output

@vanilla_page
def render_data_as_html(api_data):
    """ Convert JSON data from the api into static html.

    The api will have returned a dict of one or more items (k, v pair).  Treat a
    dict item as a detail page component.  Treat a list as a search list component.
    """
    def _component_generator():
        for k, v in api_data.items():
            if isinstance(v, list):
                yield render_search_as_html(k, v)
            else:
                yield render_detail_as_html(k, v)

    return '<hr>'.join(_component_generator())

@vanilla_page
def render_form_as_html():
    """ Create HTML for the search form page. """
    return """
        <form action="/vanilla/search" method="get">
            <h2>Search for</h2>
            <input type="radio" id="artist" name="qtype" value="artist" checked>
            <label for="artist">Artist</label><br>
            <input type="radio" id="album" name="qtype" value="album">
            <label for="album">Album</label><br>
            <input type="radio" id="track" name="qtype" value="track">
            <label for="track">Track</label>
            <br><br>
            <label for="query">Query:</label><br>
            <input type="text" id="query" name="query" maxlength="64" autofocus required><br>
            <details>
                <summary>Field Filters</summary>
                <blockquote cite="https://developer.spotify.com/documentation/web-api/reference/search/search/">
                By default, results are returned when a match is
                found in any field of the target object type. Searches can be made
                more specific by specifying an album, artist or track field filter.
                For example: The query <code>q=album:gold%20artist:abba&type=album </code>
                returns only albums with the text “gold” in the album name and the 
                text “abba” in the artist name.
                </blockquote>
            </details>
            <br>
            <input type="submit" value="Submit">
        </form>
    """

class VanillaUI():
    """ Create endpoints for the Vanilla HTML interface. """
    # pylint: disable=no-self-use
    def __init__(self):
        self.requests = requests.Session()
        self.requests.headers.update({'Keep-Alive': 'timeout=60'})

    @cherrypy.expose
    def index(self):
        """ Show search form at application base '/vanilla' """
        return render_form_as_html()

    @cherrypy.expose
    def search(self, **kwargs):
        """ Handle search form submission by requesting from JSON service. """
        logging.info(">=>")
        logging.info("invoked with %s", str(kwargs))
        # in the context of cherrypy.request, this handler is at
        # base + script_name + path_info + query_string
        # aka: ip:port + vanilla + search + qtype=xx&query=yy
        api_url = cherrypy.request.base + cherrypy.request.path_info + '?' + cherrypy.request.query_string
        r = self.requests.get(api_url)
        r.raise_for_status()
        return render_data_as_html(r.json())

    @cherrypy.expose
    @cherrypy.popargs('qtype', 'qid')
    def detail(self, qtype, qid):
        """ Handle all detail urls constructed in HTML.  For instance,

        `/vanilla/detail/{qtype}/{qid}` where
        `qtype` is one of (artist, album, track) and
        `qid` is a unique identifier
         """
        logging.info(">=>")
        logging.info("invoked with %s", '/'.join((qtype, qid)))
        # in the context of cherrypy.request, this handler is at
        # base + script_name + path_info + query_string
        # aka: ip:port + vanilla + detail + qtype + qid
        # want ip:port + qtype + qid
        # note, need to remove pluralization or add url aliases specifically
        # albums->album, artists->artist, track->tracks
        api_url = '/'.join((cherrypy.request.base, qtype.rstrip('s'), qid))
        r = self.requests.get(api_url)
        r.raise_for_status()
        return render_data_as_html(r.json())
