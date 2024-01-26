from mutagen import File
from pydub import AudioSegment
import os
'''
The get_audio_metadata function is a Python utility that retrieves two key pieces of information 
from audio files: 
1. the length of the audio in seconds and 
2. its complete metadata (like album, title, artist, genre, date). 
It uses pydub for calculating the audio duration and mutagen for extracting metadata.
'''
def get_audio_metadata(file_path):
    # Check if file exists
    if not os.path.exists(file_path):
        return "File does not exist", ""

    try:
        # Get audio length
        audio = AudioSegment.from_file(file_path)
        length_seconds = len(audio) / 1000
    except Exception as e:
        return f"Error processing audio length: {e}", ""

    try:
        # Get metadata with mutagen
        audio_file = File(file_path, easy=True) # Using easy=True to simplify metadata
        metadata = audio_file.tags if audio_file else {}
    except Exception as e:
        return length_seconds, f"Error extracting metadata: {e}"

    # Format metadata
    metadata_str = ""
    if metadata:
        metadata_items = [f"{key}: {', '.join(value) if isinstance(value, list) else value}" for key, value in metadata.items()]
        metadata_str = ', '.join(metadata_items)

    return length_seconds, metadata_str.strip()

# Example usage:
# length, metadata = get_audio_metadata('path/to/your/audiofile.mp3')
# print("Length in seconds:", length)
# print("Metadata:", metadata)

#Contributed by Shreyan Basu Ray [Github - @Shreyan1]
