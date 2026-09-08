import os
from google_auth_oauthlib.flow import InstalledAppFlow

# Define the exact permission scope needed for Drive uploading
SCOPES = ['https://googleapis.com']

def generate_token():
    print("Looking for credentials.json...")
    if not os.path.exists('credentials.json'):
        print("ERROR: Move your credentials.json file into this folder first!")
        return

    # Initialize the authentication sequence independently
    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
    
    print("\nStarting local authentication server...")
    print("A browser window should open automatically.")
    print("If it doesn't, copy and paste the link from the terminal into your browser.\n")
    
    # Run the setup script. This will physically pop open your native desktop browser safely.
    creds = flow.run_local_server(port=8080)
    
    # Save the authorized session properties directly into your project directory
    with open('token.json', 'w') as token:
        token.write(creds.to_json())
        
    print("\n🎉 SUCCESS! token.json has been created in your folder.")
    print("You can close this window now.")

if __name__ == '__main__':
    generate_token()
