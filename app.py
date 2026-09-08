import os
import json
import requests
import io
from flask import Flask, render_template, request, jsonify
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

app = Flask(__name__)

SCOPES = ['https://googleapis.com']

def get_drive_service():
    """Authenticates using environment variables securely for cloud platforms."""
    creds = None
    
    # 1. First check for a persistent token string saved in env variables
    env_token = os.environ.get('GOOGLE_TOKEN_JSON')
    if env_token:
        token_info = json.loads(env_token)
        creds = Credentials.from_authorized_user_info(token_info, SCOPES)
        
    # 2. Fallback to reading a local token.json if present
    elif os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    # 3. If no active token exists, generate credentials from our minified JSON string
    if not creds or not creds.valid:
        env_creds = os.environ.get('GOOGLE_CREDENTIALS_JSON')
        if not env_creds:
            raise ValueError("Missing GOOGLE_CREDENTIALS_JSON environment variable.")
            
        creds_info = json.loads(env_creds)
        flow = InstalledAppFlow.from_client_config(creds_info, SCOPES)
        
        # Enforce out-of-band / local system loopback explicitly to prevent parameter dropouts
        flow.redirect_uri = 'http://localhost'
        
        # NOTE: If executing directly on Render, you should generate token.json locally 
        # on your machine first, then paste its contents into a GOOGLE_TOKEN_JSON env variable.
        creds = flow.run_local_server(port=0, open_browser=False)
            
    return build('drive', 'v3', credentials=creds)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/transfer', methods=['POST'])
def transfer_file():
    data = request.json
    discord_url = data.get('url')
    
    if not discord_url:
        return jsonify({'error': 'No URL provided'}), 400

    try:
        response = requests.get(discord_url, stream=True)
        if response.status_code != 200:
            return jsonify({'error': 'Failed to fetch file from Discord link'}), 400
            
        filename = discord_url.split('/')[-1].split('?')[0]
        if not filename:
            filename = "downloaded_file"

        file_stream = io.BytesIO(response.content)
        service = get_drive_service()

        file_metadata = {'name': filename}
        media = MediaIoBaseUpload(file_stream, mimetype=response.headers.get('Content-Type'), resumable=True)
        
        uploaded_file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        
        file_id = uploaded_file.get('id')

        user_permission = {'type': 'anyone', 'role': 'reader'}
        service.permissions().create(fileId=file_id, body=user_permission).execute()

        direct_download_url = f"https://google.com{file_id}"

        return jsonify({
            'success': True,
            'filename': filename,
            'download_url': direct_download_url
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
