\import streamlit as st
import requests
import re
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors

# Define the required OAuth2 scopes.
SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]

def get_authenticated_credentials():
    """
    Perform OAuth2 authentication and return credentials.
    Credentials are stored in session_state to avoid re-authenticating.
    """
    if "credentials" not in st.session_state:
        # Load OAuth2 client config from secrets.
        client_config = st.secrets.get("YT_OAUTH")
        if not client_config:
            st.error("Missing OAuth2 client config in secrets! Please define [YT_OAUTH] in your secrets file.")
            st.stop()
        
        # Initialize the OAuth flow.
        flow = google_auth_oauthlib.flow.Flow.from_client_config(
            client_config, scopes=SCOPES
        )
        # Set the redirect URI to the current Streamlit app.
        flow.redirect_uri = "http://localhost:8501"
        
        # Generate the authorization URL.
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true'
        )
        st.session_state.oauth_state = state

        st.write("### Authorization Required")
        st.write("Please click the link below to authorize the app:")
        st.write(authorization_url)
        code = st.text_input("Enter the authorization code:")

        if code:
            try:
                flow.fetch_token(code=code)
                credentials = flow.credentials
                # Save only the fields needed to reconstruct Credentials later.
                st.session_state.credentials = {
                    "token": credentials.token,
                    "refresh_token": credentials.refresh_token,
                    "token_uri": credentials.token_uri,
                    "client_id": credentials.client_id,
                    "client_secret": credentials.client_secret,
                    "scopes": credentials.scopes
                }
                st.experimental_rerun()
            except Exception as e:
                st.error(f"Error fetching token: {e}")
                st.stop()
        else:
            st.stop()  # Wait until the user provides the auth code.
    else:
        # Recreate credentials from session_state.
        from google.oauth2.credentials import Credentials
        creds_data = st.session_state.credentials
        credentials = Credentials(
            token=creds_data["token"],
            refresh_token=creds_data["refresh_token"],
            token_uri=creds_data["token_uri"],
            client_id=creds_data["client_id"],
            client_secret=creds_data["client_secret"],
            scopes=creds_data["scopes"]
        )
        return credentials

def get_video_id(url):
    """
    Extract the video ID from a YouTube URL.
    """
    pattern = r"(?:v=|\/)([0-9A-Za-z_-]{11}).*"
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    return None

def list_captions(video_id, youtube):
    """
    List available caption tracks for the given video ID using the authenticated YouTube API service.
    """
    try:
        request = youtube.captions().list(
            part="snippet",
            videoId=video_id
        )
        response = request.execute()
        return response
    except Exception as e:
        st.error(f"Error fetching captions: {e}")
        return None

def download_caption(caption_id, access_token):
    """
    Download a caption track in SRT format using its caption ID.
    This uses the OAuth2 access token for authentication.
    """
    endpoint = f"https://www.googleapis.com/youtube/v3/captions/{caption_id}"
    params = {"tfmt": "srt"}
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(endpoint, params=params, headers=headers)
    if response.status_code == 200:
        return response.text
    else:
        st.error(f"Error downloading caption: {response.text}")
        return None

# --- Streamlit UI ---
st.title("YouTube Captions Downloader (OAuth2)")
st.write("Enter a YouTube video URL to fetch available caption tracks.")

# Authenticate the user and get OAuth2 credentials.
credentials = get_authenticated_credentials()

# Build the YouTube API client using the OAuth2 credentials.
youtube = googleapiclient.discovery.build("youtube", "v3", credentials=credentials)

# Input for YouTube video URL.
video_url = st.text_input("YouTube Video URL:")

if video_url:
    video_id = get_video_id(video_url)
    if video_id:
        st.write("Fetching captions for video ID:", video_id)
        captions_data = list_captions(video_id, youtube)
        if captions_data and "items" in captions_data and captions_data["items"]:
            # Build a dictionary of available caption tracks.
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
                access_token = credentials.token
                caption_id = caption_options[selected_caption]
                srt_content = download_caption(caption_id, access_token)
                if srt_content:
                    st.download_button("Download SRT", srt_content, file_name="captions.srt", mime="text/plain")
        else:
            st.error("No captions found for this video or captions are not accessible.")
    else:
        st.error("Invalid YouTube URL. Please check the URL and try again.")
