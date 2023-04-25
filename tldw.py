
import os
import wave

from google.cloud import storage
import google.cloud.texttospeech as tts

from moviepy.editor import AudioFileClip, CompositeAudioClip,TextClip, CompositeVideoClip, VideoFileClip, concatenate_videoclips
from moviepy.audio import fx


def make_video_highlight(input_file_name, highlights, output_file_name, music=False):
    
    
    highlight_padding_seconds = 5
    
    for h in highlights:
        print(h['time'], h['screen_caption'], h['voice_summary'])
        
    # download video from GS
    local_file_name = download_file_from_google_storage(input_file_name)
        
    voice_scripts = [h['voice_summary'] for h in highlights]
    video_highlight_times = [h['time'] for h in highlights]
    highlight_headings = [h['screen_caption'] for h in highlights]
    
    # generate the voices of the summaries
    voice_file_names = create_voice_clips(voice_scripts)
    
    # mix audio tracks
    audio_track = mix_audio_tracks(voice_file_names, local_file_name, video_highlight_times, music, highlight_padding_seconds)
    
    # create video track
    video_clip = cut_video_highlights(local_file_name, video_highlight_times, highlight_headings, voice_file_names, highlight_padding_seconds)
    
    # combine into final movie     
    final_clip = video_clip.set_audio(audio_track)
    
    final_clip.write_videofile(output_file_name, audio_codec='aac')
    
    return output_file_name
    


def create_voice_clips(list_voice_scripts):
    
    output_folder = 'audio/'
    output_audio_files = []
    
    for i, script in enumerate(list_voice_scripts):
        audio_file_name = f'{output_folder}audio{i}.wav'
        text_to_wav('en-US-Studio-O', script, audio_file_name, 1)
        output_audio_files.append(audio_file_name)
    
    return output_audio_files


def mix_audio_tracks(voice_file_names, local_video_file_name, video_highlight_times, music, highlight_padding_seconds=5):
    
    start_time = 0
    
    audio_clips = []
    
    for voice_file_n, video_time in zip(voice_file_names, video_highlight_times):
        
        voice_audio_length = audio_length(voice_file_n)
        voice_audio_clip = AudioFileClip(voice_file_n).set_start(start_time)
        
        video_audio_start = video_time + voice_audio_length
        video_audio_end = video_audio_start + highlight_padding_seconds
        print('local', local_video_file_name)
        video_audio_clip = fx.all.audio_fadeout(
                                    fx.all.audio_fadein(
                                            AudioFileClip(local_video_file_name).subclip(video_audio_start, video_audio_end)
                                    ,1)
                                ,1).set_start(start_time + voice_audio_length)
        
        audio_clips.append(voice_audio_clip)
        audio_clips.append(video_audio_clip)
        
        start_time += voice_audio_length + highlight_padding_seconds
        
    
        
    mixed_audio = CompositeAudioClip(audio_clips)
    
    if music:
        music_clip = AudioFileClip("chill-abstract-intention-12099.mp3").volumex(0.1).subclip(0, mixed_audio.duration)
        mixed_audio =  CompositeAudioClip([music_clip ,mixed_audio])
    
    
    return mixed_audio


def cut_video_highlights(original_file_name, video_highlight_times, highlight_headings, voice_file_names, highlight_padding_seconds=5):
    
    video_clips = []
    
    for voice_file_name, highlight_time, heading in zip(voice_file_names, video_highlight_times, highlight_headings):
        
        voice_audio_length = audio_length(voice_file_name)
        formated_time = seconds_to_minutes_seconds(highlight_time)
        
        txt_clip = TextClip( f"[{formated_time}] {heading}", font="Helvetica", fontsize = 40, color = 'black', bg_color='white')
        txt_clip = txt_clip.set_pos((50, 50)).set_duration(5) 
        
        video_clip_start = highlight_time
        video_clip_end = highlight_time + voice_audio_length + highlight_padding_seconds
        clip = CompositeVideoClip([ VideoFileClip(original_file_name).subclip(video_clip_start, video_clip_end), txt_clip])
        
        video_clips.append(clip)
        
    print(video_clips)
    
    final_video_clip = concatenate_videoclips(video_clips)
    
    return final_video_clip

def text_to_wav(voice_name: str, text: str, filename: str, speaking_rate: float = 1):
    language_code = "-".join(voice_name.split("-")[:2])
    text_input = tts.SynthesisInput(text=text)
    voice_params = tts.VoiceSelectionParams(
        language_code=language_code, name=voice_name
    )
    audio_config = tts.AudioConfig(audio_encoding=tts.AudioEncoding.LINEAR16, 
                                   speaking_rate=speaking_rate)

    client = tts.TextToSpeechClient()#.from_service_account_file(SERVICE_ACCOUNT)
    response = client.synthesize_speech(
        input=text_input, voice=voice_params, audio_config=audio_config
    )

    with open(filename, "wb") as out:
        out.write(response.audio_content)
        print(f'Generated speech saved to "{filename}"')
        
        
def download_file_from_google_storage(gs_file_name):

    
    local_file_name = os.path.basename(gs_file_name)
    bucket_name , *parts = gs_file_name.replace('gs://', '').split('/')
    object_name = '/'.join(parts)

    print(bucket_name, object_name )

    # Create a Storage client.
    client = storage.Client()

    # Get the bucket.
    bucket = client.bucket(bucket_name)

    # Get the blob.
    blob = bucket.blob(object_name)

    # Download the blob to a local file.
    with open(local_file_name, "wb") as f:
        blob.download_to_file(f)

    # Print a success message.
    print("The file was successfully downloaded.")
    
    return local_file_name

def seconds_to_minutes_seconds(seconds):

    minutes = seconds // 60
    seconds %= 60

    return f"{minutes}:{seconds:02d}"

def audio_length(audio_file_name):
    with wave.open(audio_file_name) as mywav:
        return mywav.getnframes() / mywav.getframerate()
