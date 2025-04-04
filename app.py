import streamlit as st
import requests
import re

def get_video_id(url):
    """
    Extract the video ID from a YouTube URL.
    """
    # This regex tries to cover multiple YouTube URL formats
    pattern = r"(?:v=|\/)([0-9A-Za-z_-]{11}).*"
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    return None

def list_captions(video_id, api_key):
    """
    List available caption tracks for the given video ID.
    """
    endpoint = "https://www.googleapis.com/youtube/v3/captions"
    params = {
        "part": "snippet",
        "videoId": video_id,
        "key": api_key,
    }
    response = requests.get(endpoint, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Error fetching captions: {response.text}")
        return None

def download_caption(caption_id, api_key):
    """
    Download a caption track in SRT format using its caption ID.
    """
    endpoint = f"https://www.googleapis.com/youtube/v3/captions/{caption_id}"
    params = {
        "tfmt": "srt",  # specify SRT format
        "key": api_key,
    }
    # Note: For some captions (especially auto-generated ones), downloading might require OAuth2.
    response = requests.get(endpoint, params=params)
    if response.status_code == 200:
        return response.text
    else:
        st.error(f"Error downloading caption: {response.text}")
        return None

# --- Streamlit UI ---
st.title("YouTube Captions Downloader")
st.write("Enter a YouTube video URL to fetch available caption tracks.")

# Check for API key in secrets
yt_secrets = st.secrets.get("YT")
if not yt_secrets or "API_KEY" not in yt_secrets:
    st.error("Missing API key in secrets! Please define [YT] and API_KEY in your .streamlit/secrets.toml file.")
    st.stop()

api_key = yt_secrets["API_KEY"]

# Input for YouTube video URL
video_url = st.text_input("YouTube Video URL:")

if video_url:
    video_id = get_video_id(video_url)
    if video_id:
        st.write("Fetching captions for video ID:", video_id)
        captions_data = list_captions(video_id, api_key)
        if captions_data and "items" in captions_data and captions_data["items"]:
            # Create a dictionary to store available caption tracks
            caption_options = {}
            for item in captions_data["items"]:
                snippet = item["snippet"]
                language = snippet.get("language", "unknown")
                name = snippet.get("name", "Default")
                caption_id = item["id"]
                label = f"{name} ({language})"
                caption_options[label] = caption_id

            selected_caption = st.selectbox("Select a caption track:", list(caption_options.keys()))
            if st.button("Download Caption"):
                caption_id = caption_options[selected_caption]
                srt_content = download_caption(caption_id, api_key)
                if srt_content:
                    st.download_button("Download SRT", srt_content, file_name="captions.srt", mime="text/plain")
        else:
            st.error("No captions found for this video or captions are not accessible.")
    else:
        st.error("Invalid YouTube URL. Please check the URL and try again.")
