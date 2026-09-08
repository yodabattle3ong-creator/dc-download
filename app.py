import os
import requests
import io
import json
from flask import Flask, render_template, request, jsonify
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

app = Flask(__name__)

# Scopes required to upload files and update sharing permissions
SCOPES = ['https://www.googleapis.com/auth/drive.file']

def get_drive_service():
    """Authenticates using environment variables or local token.json."""
    creds = None
    
    # 1. Look for existing session token
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    # 2. If no token, authenticate via environment variables or local credentials file
    if not creds or not creds.valid:
        google_creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
        
        if google_creds_json:
            # For cloud hosting deployment (Render/Railway)
            creds_data = json.loads(google_creds_json)
            flow = InstalledAppFlow.from_client_config(creds_data, SCOPES)
        elif os.path.exists('credentials.json'):
            # For local testing configuration
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
        else:
            raise Exception("Missing authentication credentials. Provide GOOGLE_CREDENTIALS_JSON env var or a credentials.json file.")
            
        flow.redirect_uri = os.environ.get("REDIRECT_URI", "urn:ietf:wg:oauth:2.0:oob")
        creds = flow.run_local_server(port=0) if not google_creds_json else flow.run_console()
        
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
            
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
        # 1. Download file from Discord link into memory streaming chunk blocks
        response = requests.get(discord_url, stream=True)
        if response.status_code != 200:
            return jsonify({'error': f'Failed to fetch file from Discord link (Status: {response.status_code})'}), 400
            
        # Extract filename cleanly from the Discord CDN path URL
        filename = discord_url.split('/')[-1].split('?')[0]
        if not filename:
            filename = "downloaded_file"

        file_stream = io.BytesIO(response.content)

        # 2. Connect to the authenticated Google Drive instance
        service = get_drive_service()

        # 3. Stream upload payload data metadata structural configurations
        file_metadata = {'name': filename}
        media = MediaIoBaseUpload(file_stream, mimetype=response.headers.get('Content-Type'), resumable=True)
        
        uploaded_file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        
        file_id = uploaded_file.get('id')

        # 4. Modify Access Management Control settings to "Anyone with the link can view"
        user_permission = {
            'type': 'anyone',
            'role': 'reader',
        }
        service.permissions().create(
            fileId=file_id,
            body=user_permission
        ).execute()

        # 5. Build accessible direct export extraction endpoint link mapping
        direct_download_url = f"https://drive.google.com/uc?export=download&id={file_id}"

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
