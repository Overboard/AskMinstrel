"""
AskMinstrel

A simple web client application to retrieve music related information.  A plain
 HTML implementation, called Vanilla is provided.  A vue.js application is considered
 but not fully developed.  A local web server provides end points and data marshalling
 for clients. 

SWENG861 Project, AskMinstrel
  André Wagner
  July, 2020

The project directly makes use of the following packages:  
[CherryPy](https://pypi.org/project/CherryPy/) A Python HTTP framework and server.  
[Tekore](https://pypi.org/project/tekore/) A Python client for the Spotify API.  
[Requests](https://pypi.org/project/requests/) A library for HTTP/1.1 requests.  
[Slugify](https://pypi.org/project/python-slugify/) Generate URI compatible strings.  

Content provided by [Spotify](https://developer.spotify.com/)

![Class Diagram](pydocs/askminstrel.png)
"""
from askminstrel.server import minstrel_server, cli
