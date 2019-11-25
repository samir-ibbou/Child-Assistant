#!/home/pi/GoogleEnv/bin/python

# This module executes a search request for the specified search term.
# NOTE: To use the sample, you must provide a developer key obtained
#       in the Google APIs Console. Search for "REPLACE_ME" in this code
#       to find the correct place to provide that key..

import argparse
import logging
import re

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


# Set DEVELOPER_KEY to the API key value from the APIs & auth > Registered apps
# tab of
#   https://cloud.google.com/console
# Please ensure that you have enabled the YouTube Data API for your project.
DEVELOPER_KEY = 'AIzaSyAiZ1GX6diYqy-ozbNgX6rY79CEYJCzMWQ'
YOUTUBE_API_SERVICE_NAME = 'youtube'
YOUTUBE_API_VERSION = 'v3'

"""Search words for quiz player"""
SEARCH_WORDS_QUIZ = [' quiz', ' questions-réponses', ' jeu', ' quiz ', ' questions-réponses ', ' jeu ', 'quiz ', 'questions-réponses ', 'jeu ','quiz', 'questions-réponses', 'jeu']

"""Commands for MPV player"""
SEARCH_COMMANDS_MPV = ['pause', 'lecture', 'suivant', 'précédent']

"""Search words for Youtube Video"""
SEARCH_WORDS_VIDEO = [
[' conte ', ' compte ', ' histoire ', 'conte ', 'compte ', 'histoire ', ' raconter ', ' conter ', ' compter ', 'raconter ', 'conter ', 'compter '],
[' chanson ', ' clip ', 'chanson ', 'clip ', ' chanter ', 'chanter'],
[' documentaire ', ' parler ', ' leçon ', ' un cours ', 'documentaire ', 'parler ', 'leçon ', 'un cours ']
]

"""Search words for Youtube Playlist"""
SEARCH_WORDS_PLAYLIST = [
[' contes ', ' comptes ', ' histoires '],
[' album ', ' retrospective ', ' compilation ','album ', 'retrospective ', 'compilation '],
[' chansons ', ' clips ', ' albums ', ' retrospectives ', ' compilations '],
[' leçons ', ' des cours ']
]

def youtube_search(query, video_type):
  youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION,
    developerKey=DEVELOPER_KEY)

  # Call the search.list method to retrieve results matching the specified
  # query term.
  search_response = youtube.search().list(
    q=query,
    part='id,snippet',
    maxResults='1',
    type=video_type,
    order='relevance',
    safeSearch='strict'
  ).execute()

  videos = []
  channels = []
  playlists = []
  result = ''
  title = ''

  # Add each result to the appropriate list, and then display the lists of
  # matching videos, channels, and playlists.
  for search_result in search_response.get('items', []):
    logging.debug('Search_result:' + str(search_result))
    if search_result['id']['kind'] == 'youtube#video' and video_type == 'video':
      videos.append('%s (%s)' % (search_result['snippet']['title'],
                                 search_result['id']['videoId']))
      result = 'https://m.youtube.com/watch?v=' + search_result['id']['videoId']
    elif search_result['id']['kind'] == 'youtube#channel' and video_type == 'channel':
      channels.append('%s (%s)' % (search_result['snippet']['title'],
                                   search_result['id']['channelId']))
      result = search_result['id']['channelId']
      #logging.info('Channel:\n' + '\n'.join(channels) + '\n')
    elif search_result['id']['kind'] == 'youtube#playlist' and video_type == 'playlist':
      playlists.append('%s (%s)' % (search_result['snippet']['title'],
                                    search_result['id']['playlistId']))
      result = youtube_playlistItems(search_result['id']['playlistId'])
      
  title = search_result['snippet']['title']
  
  if video_type == 'video':
      logging.info('Audio result found:\n' + '\n'.join(videos))
  if video_type == 'playlist':   
      logging.info('Playlist result found:\n' + '\n'.join(playlists))
  
  return (result, title)

def youtube_playlistItems(playlistid):
    
  youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION,
    developerKey=DEVELOPER_KEY)
  
  # Call the search.playlistItems().list method to retrieve all videos id from playlistId
  playlistitems_list_request = youtube.playlistItems().list(
      playlistId=playlistid,
      part='snippet',
      maxResults='20'
      )
  
  videos = []
  
  while playlistitems_list_request:
    playlistitems_list_response = playlistitems_list_request.execute()

    # Print information about each video.
    for playlist_item in playlistitems_list_response['items']:
      title = playlist_item['snippet']['title']
      video_id = playlist_item['snippet']['resourceId']['videoId']
      videos.append('https://m.youtube.com/watch?v=' + video_id)
      logging.debug('Audio added to results: %s (%s)' % (title, video_id))

    playlistitems_list_request = youtube.playlistItems().list_next(
      playlistitems_list_request, playlistitems_list_response)
    
  return videos

def word_search(request):
    n = 0
    while n<len(SEARCH_COMMANDS_MPV):
        word = SEARCH_COMMANDS_MPV[n]
        match = re.match(word, request.lower().strip())
        logging.debug('Searching MPV command : ' + word)
        if match:
            logging.debug('MPV command is : ' + word)
            # Call the MPV command
            return (word, 'command')
        n += 1
    n = 0
    while n<len(SEARCH_WORDS_QUIZ):
        match = re.search(SEARCH_WORDS_QUIZ[n].lower(), request.lower())
        word = SEARCH_WORDS_QUIZ[n].strip()
        logging.debug('Searching Quiz words : ' + word)
        if match:
            logging.debug('Quiz word is : ' + word)
            # Call the Quiz game
            return (word, 'quiz')
        n += 1
    n = 0
    while n<len(SEARCH_WORDS_VIDEO):
        m = 0
        while m<len(SEARCH_WORDS_VIDEO[n]):
            match = re.search(SEARCH_WORDS_VIDEO[n][m].lower(), request.lower())
            word = SEARCH_WORDS_VIDEO[n][m].strip()
            logging.debug('Searching term word : ' + word) 
            if match:
                storyname = request[match.end():]
                search_request = SEARCH_WORDS_VIDEO[n][m].strip() + ' ' + storyname
                logging.debug(search_request)  
                word = SEARCH_WORDS_VIDEO[n][m].strip()
                #term_word = word[len(word)-1]
                logging.debug('Term word found is: ' + word)
                video_type = 'video'
                # Call the audio playing function
                logging.debug('Video type is: ' + video_type)
                return (word + ' ' + storyname, video_type)
            m += 1
        n += 1
    n = 0
    while n<len(SEARCH_WORDS_PLAYLIST):
        m = 0
        while m<len(SEARCH_WORDS_PLAYLIST[n]):
            match = re.search(SEARCH_WORDS_PLAYLIST[n][m].lower(), request.lower())
            word = SEARCH_WORDS_PLAYLIST[n][m].strip()
            logging.debug('Searching term word : ' + word) 
            if match:
                storyname = request[match.end():]
                search_request = SEARCH_WORDS_PLAYLIST[n][m].strip() + ' ' + storyname 
                word = SEARCH_WORDS_PLAYLIST[n][m].strip()
                #term_word = word[len(word)-1]
                logging.debug('Term word found is: ' + word)
                video_type = 'playlist'
                # Call the audio playing function
                logging.debug('Video type is: ' + video_type)
                return (word + ' ' + storyname, video_type)
            m += 1
        n += 1
    return