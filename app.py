import streamlit as st
from dotenv import load_dotenv
import os
from groq import Groq
from youtube_transcript_api import YouTubeTranscriptApi

load_dotenv(override=True)

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# -----------------------
# Helper: Get Video ID
# -----------------------
def get_video_id(url):
    if "v=" in url:
        return url.split("v=")[1].split("&")[0]
    elif "youtu.be/" in url:
        return url.split("youtu.be/")[1].split("?")[0]
    return None

# -----------------------
# Logic: Extract Transcript
# -----------------------
def extract_transcript_details(youtube_video_url):
    try:
        video_id = get_video_id(youtube_video_url)
        if not video_id:
            st.error("Could not parse video ID from URL.")
            return None

        ytt_api = YouTubeTranscriptApi()
        fetched = ytt_api.fetch(video_id)
        result = " ".join([snippet.text for snippet in fetched])
        return result

    except Exception as e:
        st.error(f"YouTube Error: {str(e)}")
        return None

# -----------------------
# Logic: Generate Summary
# -----------------------
def generate_summary(transcript_text, summary_length, summary_language):
    length_instructions = {
        "Short (100 words)": "Summarize in strictly under 100 words.",
        "Medium (250 words)": "Summarize in strictly under 250 words.",
        "Detailed (500 words)": "Summarize in strictly under 500 words."
    }

    prompt = f"""
You are an expert content analyst and note-taking assistant specializing in summarizing YouTube videos.

Your task is to analyze the provided video transcript and produce a structured, professional summary.
{length_instructions[summary_length]}
Respond in {summary_language} language.

Format your response as follows:

## 📌 Video Overview
A 2-3 sentence overview of what the video is about.

## 🔑 Key Points
- Extract the most important points as concise bullet points
- Each bullet should be clear and self-contained

## 💡 Key Takeaways
- What are the most valuable insights from this video?
- What should the viewer remember or act on?

## 📚 Topics Covered
List the main topics or sections discussed in the video.

## ⚡ Quick Summary
One powerful sentence that captures the essence of the entire video.

Guidelines:
- Use clear, professional language
- Be concise but comprehensive
- Avoid filler words and repetition
- Focus on actionable insights where applicable
- Maintain a neutral, informative tone

Transcript:
"""
    try:
        trimmed = transcript_text[:8000]
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt + trimmed}]
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"Groq Error: {str(e)}")
        return None

# -----------------------
# Logic: Chat with Video
# -----------------------
def chat_with_video(user_question, transcript_text, chat_history):
    system_prompt = f"""
You are an intelligent assistant that has watched and fully understood a YouTube video.
Answer the user's questions based strictly on the transcript provided below.
If the answer is not found in the transcript, say "I couldn't find that information in the video."
Be concise, clear, and professional in your responses.

Transcript:
{transcript_text[:8000]}
"""
    messages = [{"role": "system", "content": system_prompt}]

    for chat in chat_history:
        messages.append({"role": "user", "content": chat["user"]})
        messages.append({"role": "assistant", "content": chat["assistant"]})

    messages.append({"role": "user", "content": user_question})

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"Groq Error: {str(e)}")
        return None

# -----------------------
# Streamlit UI
# -----------------------
st.set_page_config(page_title="YouTube Summarizer", page_icon="🎥", layout="wide")

# -----------------------
# Sidebar Settings
# -----------------------
with st.sidebar:
    st.title("⚙️ Settings")
    st.divider()

    st.markdown("### 📏 Summary Length")
    summary_length = st.radio(
        "Choose length:",
        ["Short (100 words)", "Medium (250 words)", "Detailed (500 words)"],
        index=1
    )

    st.divider()

    st.markdown("### 🌐 Summary Language")
    summary_language = st.selectbox(
        "Choose language:",
        ["English", "Hindi", "Telugu", "Tamil", "Spanish", "French", "German", "Arabic", "Chinese", "Japanese"],
        index=0
    )

    st.divider()

    st.markdown("### ℹ️ About")
    st.info("This app extracts transcripts from YouTube videos and generates professional summaries using AI. You can also chat with the video content!")

# -----------------------
# Main UI
# -----------------------
st.title("🎥 YouTube Transcript to Notes Converter")
st.markdown("Paste any YouTube link below to get a professional structured summary instantly.")

st.divider()

youtube_link = st.text_input("🔗 Enter YouTube Video Link:", placeholder="https://www.youtube.com/watch?v=...")

if youtube_link:
    video_id = get_video_id(youtube_link)
    if video_id:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.image(f"http://img.youtube.com/vi/{video_id}/0.jpg", use_container_width=True)

st.divider()

if st.button("📝 Get Detailed Notes", use_container_width=True):
    if not youtube_link:
        st.warning("⚠️ Please enter a YouTube link first.")
    else:
        with st.spinner("Step 1: Extracting transcript from YouTube..."):
            transcript_text = extract_transcript_details(youtube_link)
            if transcript_text:
                st.session_state.transcript = transcript_text
                st.session_state.chat_history = []

        if st.session_state.get("transcript"):
            with st.spinner("Step 2: Generating professional summary with AI..."):
                summary = generate_summary(
                    st.session_state.transcript,
                    summary_length,
                    summary_language
                )
                if summary:
                    st.session_state.summary = summary

# -----------------------
# Show Summary
# -----------------------
if st.session_state.get("summary"):
    st.divider()
    st.markdown("## 📝 Detailed Notes")
    st.markdown(st.session_state.summary)

    st.divider()
    st.download_button(
        label="⬇️ Download Notes as .txt",
        data=st.session_state.summary,
        file_name="youtube_notes.txt",
        mime="text/plain"
    )

# -----------------------
# Chat with Video
# -----------------------
if st.session_state.get("transcript"):
    st.divider()
    st.markdown("## 💬 Chat with the Video")
    st.markdown("Ask any question about the video content.")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    for chat in st.session_state.chat_history:
        with st.chat_message("user"):
            st.write(chat["user"])
        with st.chat_message("assistant"):
            st.write(chat["assistant"])

    user_question = st.chat_input("Ask something about the video...")

    if user_question:
        with st.chat_message("user"):
            st.write(user_question)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                answer = chat_with_video(
                    user_question,
                    st.session_state.transcript,
                    st.session_state.chat_history
                )
                if answer:
                    st.write(answer)
                    st.session_state.chat_history.append({
                        "user": user_question,
                        "assistant": answer
                    })