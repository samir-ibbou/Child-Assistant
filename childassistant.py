# Copyright (C) 2018 Samir IBBOU
# Project "ChildAssistant" that implements gRPC client for Google Assistant API v2 and YouTube API v3

#!/home/pi/GoogleEnv/bin/python

#import concurrent.futures
import json
import logging

import re
import os
import os.path
#import time
import sys

import mpv

import click
import grpc
import google.auth.transport.grpc
import google.auth.transport.requests
import google.oauth2.credentials
from google.assistant.embedded.v1alpha2 import (
    embedded_assistant_pb2,
    embedded_assistant_pb2_grpc
)

from tenacity import retry, stop_after_attempt, retry_if_exception

try:
    from . import (
        assistant_helpers,
        audio_helpers,
        device_helpers,
        search,
        synth_wav,
        synth_mp3,        
        quiz_game
    )
except SystemError:
    import assistant_helpers
    import audio_helpers
    import device_helpers
    import search
    import synth_wav
    import synth_mp3
    import quiz_game

import subprocess
from io import BytesIO

"""Common settings for assistant helpers."""
ASSISTANT_API_ENDPOINT = 'embeddedassistant.googleapis.com'
END_OF_UTTERANCE = embedded_assistant_pb2.AssistResponse.END_OF_UTTERANCE
DIALOG_FOLLOW_ON = embedded_assistant_pb2.DialogStateOut.DIALOG_FOLLOW_ON
CLOSE_MICROPHONE = embedded_assistant_pb2.DialogStateOut.CLOSE_MICROPHONE
DEFAULT_GRPC_DEADLINE = 60 * 3 + 5

player = None

def play_mpv_command(x):
    return {
        'pause': player.pause,
        'lecture': player.play,
        'suivant': player.playlist_next,
        'précédent': player.playlist_prev
    }[x]

def play_audio(s_words, v_type):
  logging.debug('play_audio()')
  logging.debug('search words are: ' + s_words)
  logging.debug('v_type is: ' + v_type)
  
  #Search words on Youtube
  logging.info('Search audio request: '+ s_words)
  result, title = search.youtube_search(s_words, v_type)
 
  if result:
      global player
      player = mpv.MPV(ytdl=True, vid=False)
      
      # Play only audio stream from the playlist results
      if v_type == 'playlist':
          logging.debug('Result search\n' + '\n'.join(result))
          n=0
          while n<len(result):
              player.playlist_append(result[n])
              n += 1
          player.playlist_pos = 0
          player.loop_playlist = '1'
          # Vocalise and play result found
          synth_mp3.synth_mp3_file("Résultat trouvé. La compilation " + title + " est en cours de lecture...")
          #synth_mp3.synth_mp3_file("Ma petite Maryam...tu es très belle et tu as de jolis cheveux")
          logging.info('Vocalise audio result')

          # Play only audio stream from the vids results
          logging.info('Play playlist results')
          player.playlist
          #player.playlist_next('weak')
          return

      logging.debug('Result search : ' + result)
      
      # Vocalise and play result found
      logging.info('Vocalise audio result')
      synth_mp3.synth_mp3_file("Résultat trouvé. L'Audio " + title + " est en cours de lecture...")
      #synth_mp3.synth_mp3_file("Ma petite Maryam, tu es très belle et tu as de jolis cheveux")

      # Play only audio stream from the vids results      
      logging.info('Play audio result')
      player.play(result)

class SampleAssistant(object):
    """Sample Assistant that supports conversations and device actions.

    Args:
      device_model_id: identifier of the device model.
      device_id: identifier of the registered device instance.
      conversation_stream(ConversationStream): audio stream
        for recording query and playing back assistant answer.
      channel: authorized gRPC channel for connection to the
        Google Assistant API.
      deadline_sec: gRPC deadline in seconds for Google Assistant API call.
      device_handler: callback for device actions.
    """

    def __init__(self, language_code, device_model_id, device_id,
                 conversation_stream,
                 channel, deadline_sec, device_handler):
        self.language_code = language_code
        self.device_model_id = device_model_id
        self.device_id = device_id
        self.conversation_stream = conversation_stream

        # Opaque blob provided in AssistResponse that,
        # when provided in a follow-up AssistRequest,
        # gives the Assistant a context marker within the current state
        # of the multi-Assist()-RPC "conversation".
        # This value, along with MicrophoneMode, supports a more natural
        # "conversation" with the Assistant.
        self.conversation_state = None

        # Create Google Assistant API gRPC client.
        self.assistant = embedded_assistant_pb2_grpc.EmbeddedAssistantStub(
            channel
        )
        self.deadline = deadline_sec

        self.device_handler = device_handler

    def __enter__(self):
        return self

    def __exit__(self, etype, e, traceback):
        if e:
            return False
        self.conversation_stream.close()

    def is_grpc_error_unavailable(e):
        is_grpc_error = isinstance(e, grpc.RpcError)
        if is_grpc_error and (e.code() == grpc.StatusCode.UNAVAILABLE):
            logging.error('grpc unavailable error: %s', e)
            return True
        return False

    @retry(reraise=True, stop=stop_after_attempt(3),
           retry=retry_if_exception(is_grpc_error_unavailable))
    def assist(self, quiz, continue_quiz):
        """Send a voice request to the Assistant and playback the response.

        Returns: True if conversation should continue.
        """
        continue_conversation = False
        device_actions_futures = []
        end_of_user_request = False
        
        #If a process mpv is in running, terminate it before run another one
        if player:
            player.terminate()
            
        self.conversation_stream.start_recording()
        logging.info('Recording audio request.')

        def iter_assist_requests():
            for c in self.gen_assist_requests():
                assistant_helpers.log_assist_request_without_audio(c)
                yield c
            self.conversation_stream.start_playback()

        # This generator yields AssistResponse proto messages
        # received from the gRPC Google Assistant API.
        for resp in self.assistant.Assist(iter_assist_requests(),
                                          self.deadline):
            assistant_helpers.log_assist_response_without_audio(resp)
            if resp.event_type == END_OF_UTTERANCE:
                logging.info('End of audio request detected')
                self.conversation_stream.stop_recording()
                end_of_user_request = True
            if resp.speech_results:
                # Intercepts with research on Youtube
                if end_of_user_request:
                    request = ' '.join(r.transcript
                                      for r in resp.speech_results)
                    #if we are in quiz game
                    if quiz:
                        logging.info('quiz : ' + str(quiz))
                        logging.info('continue_quiz : ' + str(continue_quiz))
                        if request.lower() == "un gland":
                            logging.debug('Gagné')
                            continue_quiz = True
                        else:
                            logging.debug('Perdu')
                            continue_quiz = True
                        logging.info('Finished playing assistant response.')
                        self.conversation_stream.stop_playback()
                        continue_conversation = True
                        return continue_conversation, quiz, continue_quiz
                    
                    #Search word from request    
                    search_response = search.word_search(request)
                    
                    if search_response:
                        #If a mpv command is called, call the mpv command
                        if search_response[1] == 'command':
                            logging.info('MPV command called : "%s"', search_response[0])
                            if search_response[0] == 'suivant':
                                player.playlist_next('weak')
                            #play_mpv_command(search_response[0])
                            logging.info('Finished playing assistant response.')
                            self.conversation_stream.stop_playback()
                            return continue_conversation, quiz, continue_quiz
                        #If a process mpv is in running, terminate it before run another one
                        #if player:
                        #    player.terminate()
                        #If a quiz game is called
                        logging.info('quiz : ' + str(quiz))
                        logging.info('continue_quiz : ' + str(continue_quiz))
                        logging.info('search_response : ' + search_response[1].lower())
                        if search_response[1] == 'quiz':
                            logging.info('Finished playing assistant response.')
                            self.conversation_stream.stop_playback()
                            quiz = True
                            if continue_quiz:
                                logging.info('Launch quiz game')                               
                                quiz_game.read_question(1)
                                quiz_game.read_reponses(1)
                                #player2 = mpv.MPV(vid=False)
                                #player2.play('/home/pi/GoogleEnv/lib/python3.5/site-packages/childassistant/quiz/animaux_celebres/debutant/audio/questions/question1.mp3')
                                #player2.wait_for_playback()
                                #player2.play('/home/pi/GoogleEnv/lib/python3.5/site-packages/childassistant/quiz/animaux_celebres/debutant/audio/reponses/reponses1.mp3')
                                #player2.wait_for_playback()
                                #player2.terminate()
                                #logging.info('Réponse : ' + response_quiz)
                                continue_quiz = False
                            else:
                                if search_response[1].lower() == "un gland":
                                    logging.debug('Gagné')
                                    playback.playback_audio_file('/home/pi/GoogleEnv/lib/python3.5/site-packages/childassistant/quiz/sons/applaude.mp3')
                                    continue_quiz = True
                                else:
                                    logging.debug('Perdu')
                                    playback.playback_audio_file('/home/pi/GoogleEnv/lib/python3.5/site-packages/childassistant/quiz/sons/huee.mp3')
                                    continue_quiz = True

                            continue_conversation = True
                            return continue_conversation, quiz, continue_quiz
                        logging.info('Finished playing assistant response.')
                        self.conversation_stream.stop_playback()
                        play_audio(search_response[0],search_response[1])
                        return continue_conversation, quiz, continue_quiz
                logging.info('Transcript of user request: "%s".',
                             ' '.join(r.transcript
                                      for r in resp.speech_results))
                logging.info('Playing assistant response.')
            if len(resp.audio_out.audio_data) > 0:
                self.conversation_stream.write(resp.audio_out.audio_data)
            if resp.dialog_state_out.conversation_state:
                conversation_state = resp.dialog_state_out.conversation_state
                logging.debug('Updating conversation state.')
                self.conversation_state = conversation_state
            if resp.dialog_state_out.volume_percentage != 0:
                volume_percentage = resp.dialog_state_out.volume_percentage
                logging.info('Setting volume to %s%%', volume_percentage)
                self.conversation_stream.volume_percentage = volume_percentage
            if resp.dialog_state_out.microphone_mode == DIALOG_FOLLOW_ON:
                continue_conversation = True
                logging.info('Expecting follow-on query from user.')
            elif resp.dialog_state_out.microphone_mode == CLOSE_MICROPHONE:
                continue_conversation = False
            if resp.device_action.device_request_json:
                device_request = json.loads(
                    resp.device_action.device_request_json
                )
                fs = self.device_handler(device_request)
                if fs:
                    device_actions_futures.extend(fs)

        if len(device_actions_futures):
            logging.info('Waiting for device executions to complete.')
            concurrent.futures.wait(device_actions_futures)

        logging.info('Finished playing assistant response.')
        self.conversation_stream.stop_playback()
        return continue_conversation
        
    def gen_assist_requests(self):
        """Yields: AssistRequest messages to send to the API."""

        dialog_state_in = embedded_assistant_pb2.DialogStateIn(
                language_code=self.language_code,
                conversation_state=b''
            )
        if self.conversation_state:
            logging.debug('Sending conversation state.')
            dialog_state_in.conversation_state = self.conversation_state
        config = embedded_assistant_pb2.AssistConfig(
            audio_in_config=embedded_assistant_pb2.AudioInConfig(
                encoding='LINEAR16',
                sample_rate_hertz=self.conversation_stream.sample_rate,
            ),
            audio_out_config=embedded_assistant_pb2.AudioOutConfig(
                encoding='LINEAR16',
                sample_rate_hertz=self.conversation_stream.sample_rate,
                volume_percentage=self.conversation_stream.volume_percentage,
            ),
            dialog_state_in=dialog_state_in,
            device_config=embedded_assistant_pb2.DeviceConfig(
                device_id=self.device_id,
                device_model_id=self.device_model_id,
            )
        )
        # The first AssistRequest must contain the AssistConfig
        # and no audio data.
        yield embedded_assistant_pb2.AssistRequest(config=config)
        for data in self.conversation_stream:
            # Subsequent requests need audio data, but not config.
            yield embedded_assistant_pb2.AssistRequest(audio_in=data)


@click.command()
@click.option('--api-endpoint', default=ASSISTANT_API_ENDPOINT,
              metavar='<api endpoint>', show_default=True,
              help='Address of Google Assistant API service.')
@click.option('--credentials',
              metavar='<credentials>', show_default=True,
              default=os.path.join(click.get_app_dir('google-oauthlib-tool'),
                                   'credentials.json'),
              help='Path to read OAuth2 credentials.')
@click.option('--project-id',
              metavar='<project id>',
              help=('Google Developer Project ID used for registration '
                    'if --device-id is not specified'))
@click.option('--device-model-id',
              metavar='<device model id>',
              help=(('Unique device model identifier, '
                     'if not specifed, it is read from --device-config')))
@click.option('--device-id',
              metavar='<device id>',
              help=(('Unique registered device instance identifier, '
                     'if not specified, it is read from --device-config, '
                     'if no device_config found: a new device is registered '
                     'using a unique id and a new device config is saved')))
@click.option('--device-config', show_default=True,
              metavar='<device config>',
              default=os.path.join(
                  click.get_app_dir('googlesamples-assistant'),
                  'device_config.json'),
              help='Path to save and restore the device configuration')
@click.option('--lang', show_default=True,
              metavar='<language code>',
              default='fr-FR',
              help='Language code of the Assistant')
@click.option('--verbose', '-v', is_flag=False, default=False,
              help='Verbose logging.')
@click.option('--input-audio-file', '-i',
              metavar='<input file>',
              help='Path to input audio file. '
              'If missing, uses audio capture')
@click.option('--output-audio-file', '-o',
              metavar='<output file>',
              help='Path to output audio file. '
              'If missing, uses audio playback')
@click.option('--audio-sample-rate',
              default=audio_helpers.DEFAULT_AUDIO_SAMPLE_RATE,
              metavar='<audio sample rate>', show_default=True,
              help='Audio sample rate in hertz.')
@click.option('--audio-sample-width',
              default=audio_helpers.DEFAULT_AUDIO_SAMPLE_WIDTH,
              metavar='<audio sample width>', show_default=True,
              help='Audio sample width in bytes.')
@click.option('--audio-iter-size',
              default=audio_helpers.DEFAULT_AUDIO_ITER_SIZE,
              metavar='<audio iter size>', show_default=True,
              help='Size of each read during audio stream iteration in bytes.')
@click.option('--audio-block-size',
              default=audio_helpers.DEFAULT_AUDIO_DEVICE_BLOCK_SIZE,
              metavar='<audio block size>', show_default=True,
              help=('Block size in bytes for each audio device '
                    'read and write operation.'))
@click.option('--audio-flush-size',
              default=audio_helpers.DEFAULT_AUDIO_DEVICE_FLUSH_SIZE,
              metavar='<audio flush size>', show_default=True,
              help=('Size of silence data in bytes written '
                    'during flush operation'))
@click.option('--grpc-deadline', default=DEFAULT_GRPC_DEADLINE,
              metavar='<grpc deadline>', show_default=True,
              help='gRPC deadline in seconds')
@click.option('--once', default=False, is_flag=True,
              help='Force termination after a single conversation.')
def main(api_endpoint, credentials, project_id,
         device_model_id, device_id, device_config, lang, verbose,
         input_audio_file, output_audio_file,
         audio_sample_rate, audio_sample_width,
         audio_iter_size, audio_block_size, audio_flush_size,
         grpc_deadline, once, *args, **kwargs):
    """Samples for the Google Assistant API.

    Examples:
      Run the sample with microphone input and speaker output:

        $ python -m googlesamples.assistant
        

      Run the sample with file input and speaker output:

        $ python -m googlesamples.assistant -i <input file>

      Run the sample with file input and output:

        $ python -m googlesamples.assistant -i <input file> -o <output file>
    """
    # Setup logging.
    logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO)

    # Load OAuth 2.0 credentials.
    try:
        with open(credentials, 'r') as f:
            credentials = google.oauth2.credentials.Credentials(token=None,
                                                                **json.load(f))
            http_request = google.auth.transport.requests.Request()
            credentials.refresh(http_request)
    except Exception as e:
        logging.error('Error loading credentials: %s', e)
        logging.error('Run google-oauthlib-tool to initialize '
                      'new OAuth 2.0 credentials.')
        sys.exit(-1)

    # Create an authorized gRPC channel.
    grpc_channel = google.auth.transport.grpc.secure_authorized_channel(
        credentials, http_request, api_endpoint)
    logging.info('Connecting to %s', api_endpoint)

    # Configure audio source and sink.
    audio_device = None
    if input_audio_file:
        audio_source = audio_helpers.WaveSource(
            open(input_audio_file, 'rb'),
            sample_rate=audio_sample_rate,
            sample_width=audio_sample_width
        )
    else:
        audio_source = audio_device = (
            audio_device or audio_helpers.SoundDeviceStream(
                sample_rate=audio_sample_rate,
                sample_width=audio_sample_width,
                block_size=audio_block_size,
                flush_size=audio_flush_size
            )
        )
    if output_audio_file:
        audio_sink = audio_helpers.WaveSink(
            open(output_audio_file, 'wb'),
            sample_rate=audio_sample_rate,
            sample_width=audio_sample_width
        )
    else:
        audio_sink = audio_device = (
            audio_device or audio_helpers.SoundDeviceStream(
                sample_rate=audio_sample_rate,
                sample_width=audio_sample_width,
                block_size=audio_block_size,
                flush_size=audio_flush_size
            )
        )
    # Create conversation stream with the given audio source and sink.
    conversation_stream = audio_helpers.ConversationStream(
        source=audio_source,
        sink=audio_sink,
        iter_size=audio_iter_size,
        sample_width=audio_sample_width,
    )

    device_handler = device_helpers.DeviceRequestHandler(device_id)

    @device_handler.command('action.devices.commands.OnOff')
    def onoff(on):
        if on:
            logging.info('Turning device on')
        else:
            logging.info('Turning device off')

    if not device_id or not device_model_id:
        try:
            with open(device_config) as f:
                device = json.load(f)
                device_id = device['id']
                device_model_id = device['model_id']
        except Exception as e:
            logging.warning('Device config not found: %s' % e)
            logging.info('Registering device')
            if not device_model_id:
                logging.error('Option --device-model-id required '
                              'when registering a device instance.')
                sys.exit(-1)
            if not project_id:
                logging.error('Option --project-id required '
                              'when registering a device instance.')
                sys.exit(-1)
            device_base_url = (
                'https://%s/v1alpha2/projects/%s/devices' % (api_endpoint,
                                                             project_id)
            )
            device_id = str(uuid.uuid1())
            payload = {
                'id': device_id,
                'model_id': device_model_id
            }
            session = google.auth.transport.requests.AuthorizedSession(
                credentials
            )
            r = session.post(device_base_url, data=json.dumps(payload))
            if r.status_code != 200:
                logging.error('Failed to register device: %s', r.text)
                sys.exit(-1)
            logging.info('Device registered: %s', device_id)
            os.makedirs(os.path.dirname(device_config), exist_ok=True)
            with open(device_config, 'w') as f:
                json.dump(payload, f)

    with SampleAssistant(lang, device_model_id, device_id,
                         conversation_stream,
                         grpc_channel, grpc_deadline,
                         device_handler) as assistant:
        # If file arguments are supplied:
        # exit after the first turn of the conversation.
        if input_audio_file or output_audio_file:
            assistant.assist()
            return

        # If no file arguments supplied:
        # keep recording voice requests using the microphone
        # and playing back assistant response using the speaker.
        # When the once flag is set, don't wait for a trigger. Otherwise, wait.
        wait_for_user_trigger = not once
        while True:
            if wait_for_user_trigger:
                click.pause(info='Press Enter to send a new request...')
                continue_conversation, quiz, continue_quiz = assistant.assist(False, True)
            else:
                continue_conversation2, quiz2, continue_quiz2 = assistant.assist(quiz, continue_quiz)
            # wait for user trigger if there is no follow-up turn in
            # the conversation.
            wait_for_user_trigger = not continue_conversation

            # If we only want one conversation, break.
            if once and (not continue_conversation):
                break

if __name__ == '__main__':

  # set log level (DEBUG, INFO, ERROR)
  #logging.basicConfig(level=logging.DEBUG)

  # create message queue for communicating between threads
  #msg_q = Queue()

  # start Child Assistant
  main()
  





  



  
