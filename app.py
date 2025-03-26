import streamlit as st
import pandas as pd
import speech_recognition as sr
import pyttsx3
import bcrypt
from rapidfuzz import fuzz
from sqlalchemy import create_engine

# Load warehouse data
DATA_PATH = "cleaned_voice_picking_data.xlsx"
df = pd.read_excel(DATA_PATH)

# User authentication (stored in an SQLite database)
DATABASE_URL = "sqlite:///users.db"

# Initialize text-to-speech engine
engine = pyttsx3.init()
engine.setProperty('rate', 150)
engine.setProperty('volume', 1.0)

def speak(text):
    """Convert text to speech."""
    engine.say(text)
    engine.runAndWait()

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
    user_data = pd.DataFrame({"Username": [username], "Password": [hashed_pw]})
    user_data.to_sql("users", con=engine, if_exists="append", index=False)
    return "User registered successfully."

def authenticate_user(username, password):
    """Authenticate user."""
    engine = create_engine(DATABASE_URL)
    users = pd.read_sql("SELECT * FROM users", con=engine)
    user = users[users["Username"] == username]
    
    if not user.empty and bcrypt.checkpw(password.encode('utf-8'), user.iloc[0]["Password"].encode('utf-8')):
        return True
    return False

# Streamlit UI
st.title("📦 Voice-Based Warehouse System")

# **User Authentication**
username = st.text_input("👤 Username")
password = st.text_input("🔑 Password", type="password")
if st.button("Login"):
    if authenticate_user(username, password):
        st.success("Login successful!")
    else:
        st.error("Invalid credentials.")

if st.button("Register"):
    register_user(username, password)
    st.success("User registered successfully!")

# **Text or Voice Input**
manual_command = st.text_input("📌 Type a command manually (or use voice)", key="manual_input")
if st.button("Submit Text Command"):
    process_command(manual_command)

if st.button("🎤 Start Listening"):
    command = recognize_speech()
    process_command(command)
