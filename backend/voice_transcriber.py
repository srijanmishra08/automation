"""
Voice Transcriber - Transcribes voice notes from WhatsApp using OpenAI Whisper
"""

import os
import tempfile
import httpx
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()


class VoiceTranscriber:
    """
    Transcribes voice messages using OpenAI's Whisper API
    """
    
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            self.client = AsyncOpenAI(api_key=api_key)
        else:
            self.client = None
            print("Warning: OPENAI_API_KEY not set. Voice transcription disabled.")
        
        # Twilio auth for downloading media
        self.twilio_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.twilio_token = os.getenv("TWILIO_AUTH_TOKEN")
    
    async def transcribe_from_url(self, media_url: str) -> str:
        """
        Download audio from URL and transcribe it
        """
        if not self.client:
            return "[Voice transcription unavailable - OPENAI_API_KEY not set]"
        
        try:
            # Download the audio file from Twilio
            async with httpx.AsyncClient() as client:
                # Twilio requires auth to download media
                response = await client.get(
                    media_url,
                    auth=(self.twilio_sid, self.twilio_token) if self.twilio_sid else None,
                    follow_redirects=True
                )
                response.raise_for_status()
                audio_data = response.content
            
            # Save to temporary file
            with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp_file:
                tmp_file.write(audio_data)
                tmp_path = tmp_file.name
            
            try:
                # Transcribe using Whisper
                with open(tmp_path, "rb") as audio_file:
                    transcription = await self.client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                        response_format="text"
                    )
                
                return transcription.strip()
            finally:
                # Clean up temp file
                os.unlink(tmp_path)
                
        except httpx.HTTPError as e:
            print(f"Error downloading audio: {e}")
            return "[Error downloading voice note]"
        except Exception as e:
            print(f"Error transcribing audio: {e}")
            return "[Error transcribing voice note]"
    
    async def transcribe_file(self, file_path: str) -> str:
        """
        Transcribe an audio file from local path
        """
        if not self.client:
            return "[Voice transcription unavailable]"
        
        try:
            with open(file_path, "rb") as audio_file:
                transcription = await self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="text"
                )
            
            return transcription.strip()
        except Exception as e:
            print(f"Error transcribing audio: {e}")
            return "[Error transcribing audio]"
