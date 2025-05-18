"""
Main Streamlit application for the preference elicitation system.
"""
import streamlit as st
import json
import os
import openai
import uuid
from dotenv import load_dotenv
import asyncio
import tempfile
from core.elicitation_bot import ElicitationBot
from core.preference_manager import PreferenceManager
from core.llm_services import LLMService

# Try to import the audio recorder component - if it fails, we'll use file upload instead
AUDIO_RECORDER_AVAILABLE = False
try:
    from streamlit_audiorecorder import st_audiorecorder
    AUDIO_RECORDER_AVAILABLE = True
except ImportError:
    AUDIO_RECORDER_AVAILABLE = False

# --- Configuration ---
load_dotenv() # Load environment variables from .env

# --- Initialize session state variables ---
if 'preferences_loaded' not in st.session_state:
    st.session_state.preference_manager = PreferenceManager()
    st.session_state.preferences_loaded = True
if 'elicitation_messages' not in st.session_state:
    st.session_state.elicitation_messages = []  # Store full chat history
if 'inference_messages' not in st.session_state:
    st.session_state.inference_messages = []
if 'bot' not in st.session_state:
    st.session_state.bot = ElicitationBot()
if 'llm_service' not in st.session_state:
    st.session_state.llm_service = LLMService()
if 'current_elicitation_message' not in st.session_state:
    st.session_state.current_elicitation_message = None
if 'current_inference_message' not in st.session_state:
    st.session_state.current_inference_message = None
if 'confirmed_preferences' not in st.session_state:
    st.session_state.confirmed_preferences = set()  # Track which preferences we've confirmed
if 'pending_preference' not in st.session_state:
    st.session_state.pending_preference = None  # Store a preference waiting for confirmation
if 'audio_client' not in st.session_state:
    try:
        st.session_state.audio_client = openai.OpenAI(
            api_key=os.getenv("OPENAI_API_KEY")
        )
    except:
        st.session_state.audio_client = None

# Voice settings
VOICE_MODEL = "tts-1"
VOICE_VOICES = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
DEFAULT_VOICE = "nova"
SPEECH_INPUT_MODEL = "whisper-1"

# --- Helper Functions (will be moved to core later) ---
def load_llm_api_keys():
    keys = {}
    if "OPENAI_API_KEY" in st.session_state and st.session_state.OPENAI_API_KEY:
        keys["openai"] = st.session_state.OPENAI_API_KEY
    # Add more LLMs here
    return keys

def save_preference(pref_text, source="manual_chat"):
    """Save a preference to the preference manager."""
    # No filter or validation - save all preferences directly
    new_pref = st.session_state.bot.save_preference(
        preference_text=pref_text,
        source=source
    )
    if new_pref:
        st.toast(f"New preference saved", icon="✅")
    return new_pref

def get_stored_preferences():
    return st.session_state.get('preferences', [])

def text_to_speech(text, voice=DEFAULT_VOICE):
    """Convert text to speech using OpenAI's API."""
    try:
        if not st.session_state.audio_client:
            return None
            
        response = st.session_state.audio_client.audio.speech.create(
            model=VOICE_MODEL,
            voice=voice,
            input=text
        )
        
        # Save to a temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        temp_file.close()
        
        # Write audio content to the temp file
        with open(temp_file.name, "wb") as f:
            f.write(response.content)
            
        return temp_file.name
    except Exception as e:
        st.error(f"Error generating speech: {str(e)}")
        return None

def speech_to_text(audio_file_path):
    """Convert speech to text using OpenAI's API."""
    try:
        if not st.session_state.audio_client:
            return None
            
        with open(audio_file_path, "rb") as f:
            transcript = st.session_state.audio_client.audio.transcriptions.create(
                model=SPEECH_INPUT_MODEL,
                file=f
            )
        return transcript.text
    except Exception as e:
        st.error(f"Error transcribing speech: {str(e)}")
        return None

# --- Main App Layout ---
st.set_page_config(layout="wide", page_title="Preference Companion")
st.title("Preference Companion")

# Create tabs
tab_elicit, tab_inference = st.tabs(["💬 Tell Me About You", "🤖 Ask Me Anything"])

# --- Voice settings in sidebar ---
st.sidebar.header("Voice Settings")
voice_enabled = st.sidebar.toggle("Enable Voice", value=False)
if voice_enabled:
    if not AUDIO_RECORDER_AVAILABLE:
        st.sidebar.error("Audio recorder not available. Install streamlit-audiorecorder package to use voice features.")
        voice_enabled = False
    else:
        selected_voice = st.sidebar.selectbox("Select Voice", VOICE_VOICES, index=VOICE_VOICES.index(DEFAULT_VOICE))
else:
    selected_voice = DEFAULT_VOICE

# Function to refresh preferences display
def refresh_preferences():
    """Force refresh of preferences display"""
    st.session_state.preferences_updated = not st.session_state.get('preferences_updated', False)

# --- Elicitation Tab ---
with tab_elicit:
    st.header("Let's Chat")
    st.markdown("I'd love to hear your stories and experiences. The more we talk, the better I can get to know you.")

    # Create a container for messages with fixed height and scrolling
    chat_container = st.container(height=400, border=True)
    
    # Display chat messages in the container
    with chat_container:
        for msg in st.session_state.elicitation_messages:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

    # Text chat input
    if prompt := st.chat_input("Share your thoughts or experiences...", key="chat_input"):
        # Add user message to chat history
        st.session_state.elicitation_messages.append({"role": "user", "content": prompt})
        
        # Get API key from environment
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            st.error("Please set your OpenAI API Key in the .env file.")
        else:
            # Get response from bot
            with st.spinner("Thinking..."):
                assistant_response, suggested_preference = asyncio.run(
                    st.session_state.bot.process_message("user1", prompt)
                )
            
            # Add assistant response to chat history
            st.session_state.elicitation_messages.append({"role": "assistant", "content": assistant_response})

            # Force refresh preferences
            refresh_preferences()
            
            # Rerun to update UI
            st.rerun()

    # Add a "Clear Chat" button
    if st.button("🗑️ Clear Chat", key="clear_elicit"):
        st.session_state.elicitation_messages = []
        st.rerun()

# --- Inference Tab ---
with tab_inference:
    st.header("Ask Me Anything")
    st.markdown("I'll use what I've learned about you to get to know you better.")

    # Create a container for messages with fixed height and scrolling
    chat_container = st.container(height=400, border=True)
    
    # Display chat messages in the container
    with chat_container:
        for msg in st.session_state.inference_messages:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

    # Text chat input
    if prompt := st.chat_input("Ask me anything...", key="inference_prompt"):
        # Add user message to chat history
        st.session_state.inference_messages.append({"role": "user", "content": prompt})
        
        # Get API key from environment
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            st.error("Please set your OpenAI API Key in the .env file.")
        else:
            # Process the message with the bot
            with st.spinner("Thinking..."):
                assistant_response = asyncio.run(
                    st.session_state.bot.process_inference_message(prompt)
                )
            
            # Add assistant response to chat history
            st.session_state.inference_messages.append({"role": "assistant", "content": assistant_response})
            
            # Force refresh preferences
            refresh_preferences()
            
            # Rerun to update UI
            st.rerun()

    # Add a "Clear Chat" button
    if st.button("🗑️ Clear Chat", key="clear_inference"):
        st.session_state.inference_messages = []
        st.rerun()

# --- Manual preference addition ---
with st.sidebar:
    st.subheader("Add Preference Manually")
    manual_pref = st.text_area("Enter a preference:", placeholder="Type a preference here")
    if st.button("Add Preference"):
        if manual_pref:
            save_preference(manual_pref, source="manual_input")
            refresh_preferences()
            st.rerun()
        else:
            st.error("Please enter a preference")

    # Future voice features notice
    st.sidebar.markdown("---")
    st.sidebar.info("🔊 Voice features are currently disabled due to compatibility issues. We're working on resolving this for a future update.")

# --- Sidebar: Display Current Preferences ---
st.sidebar.header("What I've Learned About You")
# Force refresh to ensure we show the most recent preferences
preferences = st.session_state.bot.get_preferences()
if preferences:
    st.sidebar.write(f"I've learned {len(preferences)} things about your preferences")
    
    # Create a scrollable container for preferences
    pref_container = st.sidebar.container(height=300, border=False)
    with pref_container:
        for pref in preferences:
            col1, col2 = st.columns([4, 1])
            with col1:
                source_icon = {
                    "manual_input": "✍️",
                    "pattern_detected": "📝",
                    "llm_detected": "🧠",
                    "response_reflected": "🪞",
                    "inference_pattern": "🔍",
                    "inference_llm": "💡",
                    "inference_reflected": "📊"
                }.get(pref.get('source', 'unknown'), "💭")
                st.write(f"{source_icon} {pref['text']}")
            with col2:
                if st.button("🗑️", key=f"del_{pref['id']}"):
                    if st.session_state.preference_manager.delete_preference(pref['id']):
                        refresh_preferences()
                        st.rerun()
else:
    st.sidebar.write("I haven't learned any preferences yet. Let's chat more!")

# Add a refresh button
if st.sidebar.button("🔄 Refresh Preferences"):
    refresh_preferences()
    st.rerun()