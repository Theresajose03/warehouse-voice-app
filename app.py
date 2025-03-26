import streamlit as st
import pandas as pd
import speech_recognition as sr
import bcrypt
from rapidfuzz import fuzz
from sqlalchemy import create_engine
from gtts import gTTS
import os

# Load warehouse data
DATA_PATH = "cleaned_voice_picking_data.xlsx"
try:
    df = pd.read_excel(DATA_PATH)
except FileNotFoundError:
    st.error("Data file not found. Please upload `cleaned_voice_picking_data.xlsx`.")

# User authentication (stored in an SQLite database)
DATABASE_URL = "sqlite:///users.db"

# Initialize text-to-speech engine

def speak(text):
    """Convert text to speech using Google TTS. and play it"""
    tts = gTTS(text=text, lang="en")
    audio_file = "response.mp3"
    tts.save(audio_file)
    st.audio(audio_file, format="audio/mp3")  # Streamlit will play the audio

def recognize_speech():
    """Capture voice input and return recognized text."""
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        speak("Listening... Speak now! You can ask about product details, stock location, or pick status.")
        st.write("🎤 Listening... (Speak clearly near the mic)")
        
        recognizer.adjust_for_ambient_noise(source, duration=1)
        audio = recognizer.listen(source, timeout=5)

    try:
        command = recognizer.recognize_google(audio).lower().strip()
        st.write(f"✅ Recognized: {command}")
        return command
    except sr.UnknownValueError:
        return "Could not understand. Please speak clearly."
    except sr.RequestError:
        return "Speech service unavailable."

def process_command(command):
    """Process recognized command and provide voice response."""
    command = command.lower().strip()

    if "tell me about" in command:
        product_name = command.replace("tell me about ", "").strip()
        item = df[df["Product Name"].str.lower() == product_name.lower()]
        if not item.empty:
            row = item.iloc[0]
            response = (f"Product: {row['Product Name']}.\n"
                        f"Quantity: {row['Quantity']}.\n"
                        f"Replenish Date: {row['Replenish Date']}.")
        else:
            response = f"Product {product_name} not found."

    elif "where is" in command:
        product_name = command.replace("where is ", "").strip()
        item = df[df["Product Name"].str.lower() == product_name.lower()]
        if not item.empty:
            row = item.iloc[0]
            response = f"{row['Product Name']} is stored at {row['Shelf Location']}."
        else:
            response = f"Location for {product_name} not found."

    else:
        response = "Command not recognized."

    st.write(f"🔹 Response: {response}")
    speak(response)

def register_user(username, password):
    """Register a new user."""
    engine = create_engine(DATABASE_URL)
    hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    # Create a table if it doesn't exist
    with engine.connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                Username TEXT PRIMARY KEY,
                Password TEXT
            )
        """)

    # Check if the user already exists
    users = pd.read_sql("SELECT * FROM users", con=engine)
    if username in users["Username"].values:
        return "User already exists. Try logging in."

    user_data = pd.DataFrame({"Username": [username], "Password": [hashed_pw]})
    user_data.to_sql("users", con=engine, if_exists="append", index=False)
    return "User registered successfully."

def authenticate_user(username, password):
    """Authenticate user."""
    engine = create_engine(DATABASE_URL)

    # Ensure the database exists
    with engine.connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                Username TEXT PRIMARY KEY,
                Password TEXT
            )
        """)

    users = pd.read_sql("SELECT * FROM users", con=engine)
    user = users[users["Username"] == username]
    
    if not user.empty and bcrypt.checkpw(password.encode('utf-8'), user.iloc[0]["Password"].encode('utf-8')):
        return True
    return False

# Streamlit UI
st.title("📦 Voice-Based Warehouse System")

# **User Authentication**
st.sidebar.header("User Authentication")
username = st.sidebar.text_input("👤 Username")
password = st.sidebar.text_input("🔑 Password", type="password")

if st.sidebar.button("Login"):
    if authenticate_user(username, password):
        st.session_state["authenticated"] = True
        st.sidebar.success("Login successful!")
    else:
        st.sidebar.error("Invalid credentials.")

if st.sidebar.button("Register"):
    register_message = register_user(username, password)
    st.sidebar.success(register_message)

# **Show Warehouse Functions Only If Logged In**
if "authenticated" in st.session_state and st.session_state["authenticated"]:
    st.subheader("Warehouse Assistant")

    # **Text or Voice Input**
    manual_command = st.text_input("📌 Type a command manually (or use voice)", key="manual_input")
    if st.button("Submit Text Command"):
        process_command(manual_command)

    if st.button("🎤 Start Listening"):
        command = recognize_speech()
        process_command(command)

else:
    st.warning("Please log in to access warehouse functions.")
