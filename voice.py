"""
Module Vocal pour le Chatbot IA.
Gère à la fois le Speech-to-Text (Écoute) et le Text-to-Speech (Parole).
"""

import sys
import speech_recognition as sr
import pyttsx3
import re

class VoiceManager:
    def __init__(self):
        # Configuration STT
        self.recognizer = sr.Recognizer()
        
        # Configuration TTS
        self.engine = pyttsx3.init()
        # On peut ajuster la vitesse et le volume
        self.engine.setProperty('rate', 170)    # Vitesse de parole légèrement plus lente que la normale
        self.engine.setProperty('volume', 0.9)  # Volume
        
        # Sélection d'une voix française si disponible
        voices = self.engine.getProperty('voices')
        for voice in voices:
            if "fr" in voice.id.lower() or "french" in voice.name.lower() or "hortense" in voice.name.lower():
                self.engine.setProperty('voice', voice.id)
                break

    def listen(self) -> str:
        """
        Écoute le microphone et retourne le texte transcrit.
        """
        with sr.Microphone() as source:
            # Ajustement pour le bruit de fond
            self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            
            try:
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=15)
                # Utilise l'API Google gratuite (requiert internet)
                text = self.recognizer.recognize_google(audio, language="fr-FR")
                return text
            except sr.WaitTimeoutError:
                return ""
            except sr.UnknownValueError:
                # Comprend pas l'audio
                return ""
            except sr.RequestError as e:
                print(f"[dim]Erreur du service vocal : {e}[/]")
                return ""

    def _clean_text_for_speech(self, text: str) -> str:
        """Nettoie le texte pour éviter que l'IA ne prononce les emojis ou le markdown."""
        # Enlever les emojis (très basique)
        text = text.encode('ascii', 'ignore').decode('ascii')
        
        # Enlever le formatage Markdown (**, _, [], etc.)
        text = re.sub(r'[\*\_\`\#]', '', text)
        
        # Enlever les URLs
        text = re.sub(r'http\S+', '', text)
        
        return text

    def speak(self, text: str):
        """
        Lit le texte à voix haute.
        """
        clean_text = self._clean_text_for_speech(text)
        if clean_text.strip():
            self.engine.say(clean_text)
            self.engine.runAndWait()
