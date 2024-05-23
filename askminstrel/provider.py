"""
The provider module acts as an interface adaptor between the third party content
provider and the AskMinstrel REST endpoints.

SWENG861 Project, AskMinstrel
  André Wagner
  July, 2020

"""
# pylint: disable=bad-continuation, invalid-name
import logging
import json
import pickle
import shutil
from pathlib import Path
from functools import singledispatch, wraps
import tekore
from slugify import slugify

CACHE = Path.cwd()/'cache'
TOKEN = CACHE/'token.pickle'
CREDENTIALS = Path.cwd()/'credentials.json'

#
# As implemented, the rich tekore models are transformed are transformed into
# simple objects that can be json serialized and represent our 'subset of interest'.
# The transformation is achieved with a set of three overloaded functions.  By
# convention, a `search object` is expected to be a list of summary information.
# These are used both for search results and also for secondary information on the
# detail pages.  Conversely, a `detail object` has more detailed information for
# a single item.  Both objects then recurse into the tekore models and create
# a `flatten object` for any nested tekore containers.
#

def _filtered_dict(model, include_keys):
    """ Create a flattened dict from `model` with only `include_keys`. """
    return {key:flatten_object_from(model.__dict__.get(key)) for key in include_keys}

#
# search_object_from
#
@singledispatch
def search_object_from(result):
    """ Convert tekore models to application specific serializable objects. """
    raise NotImplementedError(type(result))

@search_object_from.register(tekore.model.Paging)
def _(result):
    return [search_object_from(item) for item in result.items]

@search_object_from.register(tekore.model.FullArtist)
def _(result):
    include_keys = ['id', 'name', 'genres', 'images']
    return _filtered_dict(result, include_keys)

@search_object_from.register(tekore.model.SimpleAlbum)
def _(result):
    include_keys = ['id', 'name', 'artists', 'release_date', 'images']
    return _filtered_dict(result, include_keys)

@search_object_from.register(tekore.model.FullTrack)
def _(result):
    include_keys = ['id', 'name', 'artists', 'album']
    return _filtered_dict(result, include_keys)

@search_object_from.register(tekore.model.SimpleTrack)
def _(result):
    include_keys = ['id', 'name', 'disc_number', 'track_number', 'duration_ms']
    return _filtered_dict(result, include_keys)

#
# detail_object_from
#
@singledispatch
def detail_object_from(result):
    """ Convert tekore models to application specific serializable objects. """
    raise NotImplementedError

@detail_object_from.register(tekore.model.FullArtist)
def _(result):
    include_keys = ['id', 'name', 'popularity', 'genres', 'images']
    return _filtered_dict(result, include_keys)

@detail_object_from.register(tekore.model.FullAlbum)
def _(result):
    include_keys = ['id', 'name', 'popularity', 'genres', 'release_date', 'total_tracks',
        'label', 'artists', 'images']
    return _filtered_dict(result, include_keys)

@detail_object_from.register(tekore.model.FullTrack)
def _(result):
    include_keys = ['id', 'name', 'popularity', 'disc_number', 'track_number',
        'artists', 'album', 'duration_ms']
    return _filtered_dict(result, include_keys)

@detail_object_from.register(tekore.model.AudioFeatures)
def _(result):
    include_keys = ['danceability', 'energy', 'valence'] 
    # additional candidates: 'acousticness', 'instrumentalness', 'liveness'
    return _filtered_dict(result, include_keys)

#
# flatten_object_from
#
@singledispatch
def flatten_object_from(result):
    """ Convert tekore models to application specific serializable objects. """
    try:
        return result.json()
    except AttributeError:
        return result

@flatten_object_from.register(tekore.model.Paging)
def _(result):
    raise NotImplementedError(type(result))

@flatten_object_from.register(tekore.model.ModelList)
def _(result):
    """ convert tekore paging model to a single serializable objects """
    try:
        return flatten_object_from(result[0])
    except IndexError:
        return None

@flatten_object_from.register(tekore.model.Image)
def _(result):
    return result.__dict__['url']

@flatten_object_from.register(tekore.model.Item)
def _(result):
    # model.Item will have id, type but maybe not name so use .get() not []
    return {k:result.__dict__.get(k) for k in ('id', 'type', 'name')}


def permacache(f):
    """ decorator to memoize api calls using on disk storage

    returned api objects are pickled to a file name constructed from the
    wrapped function name and the keyword arguments, positional args ignored
    """
    def _construct_cache_name(prefix, options):
        return (CACHE/slugify(
            ' '.join((prefix, str(sorted(options.items()))))
            )).with_suffix('.pickle')

    @wraps(f)
    def _wrapper(*args, **kwargs):
        filename = _construct_cache_name(f.__name__, kwargs)
        logging.debug('cache name resolved as %s', filename)
        if filename.exists():
            with filename.open('rb') as fp:
                api_result = pickle.load(fp)
            logging.info('retrieved %s from cache', filename.name)
        else:
            api_result = f(*args, **kwargs)
            with filename.open('wb') as fp:
                pickle.dump(api_result, fp)
            logging.info('cached new %s from api', filename.name)
        return api_result
    return _wrapper

class TekoreAdaptor(tekore.Spotify):
    """ subclass the api module to give decorater access to its methods """
    # pylint: disable=arguments-differ

    @permacache
    def search(self, **kwargs):
        return super().search(**kwargs)

    @permacache
    def artist(self, **kwargs):
        return super().artist(**kwargs)

    @permacache
    def artist_albums(self, **kwargs):
        return super().artist_albums(**kwargs)

    @permacache
    def album(self, **kwargs):
        return super().album(**kwargs)

    @permacache
    def album_tracks(self, **kwargs):
        return super().album_tracks(**kwargs)

    @permacache
    def track(self, **kwargs):
        return super().track(**kwargs)

    @permacache
    def track_audio_features(self, **kwargs):
        return super().track_audio_features(**kwargs)

class Provider():
    """ Wrap the third party api module and provide simple objects for JSON service. 
    
    Also manages peristing the refreshable client token between application sessions.
    Obtaining a new token requires a credentials.json file with
    
    ```
    {
        "client_id": "...",
        "client_secret": "..."
    }
    ```
    """

    def __init__(self, memoize=True):
        if memoize:
            # create cache dir if it does not exist
            CACHE.mkdir(parents=True, exist_ok=True)
            factory = TekoreAdaptor
        else:
            # clear cache and do not use
            shutil.rmtree(CACHE, ignore_errors=True)
            factory = tekore.Spotify

        try:
            self.token = self._token_load()
            self._token_dump(self.token)
        except tekore.BadRequest as err:
            self.token = None

        self.spotify = factory(token=self.token,
            sender=tekore.CachingSender(max_size=256, 
                sender=tekore.PersistentSender()))  # chained senders

    @staticmethod
    def _token_load():
        """ Load persisted token from last session or request new token. """
        try:
            # load persisted token and check value, this will refresh if necessary
            with TOKEN.open('rb') as fp:
                token = pickle.load(fp)
            token_value = token.access_token[:8]
            logging.info("obtained token %s... from file", token_value)
            return token
        except FileNotFoundError as err:
            # no file but not necessarily an error
            logging.warning('no token file found, requesting new')
        except (pickle.PickleError, EOFError) as err:
            # file exists but could not un-pickle
            logging.error('%s reading token, requesting new', err)
        except AttributeError as err:
            # file unpickled but it was not a token
            logging.error('%s using token, requesting new', err)

        try:
            # request new token with external credentials
            with CREDENTIALS.open() as fp:
                credentials = json.load(fp)
            return tekore.request_client_token(**credentials)
        except FileNotFoundError as err:
            # no file for credentials, cannot proceed
            logging.critical('Credentials not found at %s', CREDENTIALS.absolute())
            raise err
        except tekore.HTTPError as err:
            # problem requesting token with credentials
            logging.critical('%s requesting token', err)
            raise err

    @staticmethod
    def _token_dump(token):
        """ Save token for next session. """
        try:
            with TOKEN.open('wb') as fp:
                pickle.dump(token, fp)
                logging.info('saved token to file')
        except FileNotFoundError:
            # directory for token does not exist, skip save
            logging.debug('no cache dir, token not saved')

    def search(self, qtype, query):
        """ Perform a search `query` for items of `qtype`. """
        api_result = self.spotify.search(query=query, types=(qtype,))
        # in our distilled api, we're only expecting one type of returned data
        # so the tekore tuple should be length one
        assert len(api_result) == 1
        return search_object_from(api_result[0])

    def artist(self, artist_id):
        """ Return detail about artist and a list of their albums. """
        api_artist = self.spotify.artist(artist_id=artist_id)
        api_albums = self.spotify.artist_albums(artist_id=artist_id)
        return {'artist': detail_object_from(api_artist),
                'albums': search_object_from(api_albums)}

    def album(self, album_id):
        """ Return detail about album and a list of its tracks. """
        api_album = self.spotify.album(album_id=album_id)
        api_tracks = self.spotify.album_tracks(album_id=album_id)
        return {'album': detail_object_from(api_album),
                'tracks': search_object_from(api_tracks)}

    def track(self, track_id):
        """ Return detail about a track."""
        api_track = self.spotify.track(track_id=track_id)
        api_features = self.spotify.track_audio_features(track_id=track_id)
        return {'track': detail_object_from(api_track),
                'audio': detail_object_from(api_features) }

if __name__ == '__main__':
    # module level test code
    logging.info("begin")
    p = Provider()
    a = p.search(query='come away with me', qtype='album')
    print(a[0])
