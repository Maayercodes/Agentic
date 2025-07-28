# YouTube API Setup Guide

This guide will help you set up the YouTube API for the AI Marketing Outreach application.

## Option 1: Using an API Key (Recommended for Public Data)

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the YouTube Data API v3:
   - Navigate to "APIs & Services" > "Library"
   - Search for "YouTube Data API v3"
   - Click on it and press "Enable"
4. Create credentials:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "API key"
   - Copy the generated API key
5. Add the API key to your `.env` file:
   ```
   YOUTUBE_API_KEY=your_api_key_here
   ```
6. (Optional but recommended) Restrict the API key:
   - Go back to the credentials page
   - Click on the API key you just created
   - Under "API restrictions", select "Restrict key"
   - Select "YouTube Data API v3" from the dropdown
   - Save the changes

## Option 2: Using Application Default Credentials (ADC)

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the YouTube Data API v3 as described above
4. Create a service account:
   - Go to "IAM & Admin" > "Service Accounts"
   - Click "Create Service Account"
   - Enter a name and description
   - Click "Create and Continue"
   - Assign the role "YouTube Data API v3 > YouTube Data API User"
   - Click "Done"
5. Create and download a key for the service account:
   - Click on the service account you just created
   - Go to the "Keys" tab
   - Click "Add Key" > "Create new key"
   - Select "JSON" and click "Create"
   - The key file will be downloaded to your computer
6. Set the environment variable to point to the key file:
   - Add the following to your `.env` file:
     ```
     GOOGLE_APPLICATION_CREDENTIALS=/path/to/your-service-account-key.json
     ```
   - Or set it as a system environment variable

## Troubleshooting

### Quota Limits

The YouTube Data API has quota limits. Each API request consumes a certain number of quota units. The default daily quota is 10,000 units. You can monitor your quota usage in the Google Cloud Console under "APIs & Services" > "Dashboard" > "YouTube Data API v3" > "Quotas".

### Authentication Errors

If you encounter authentication errors:

1. Verify that the API key or service account key is correct
2. Ensure the YouTube Data API v3 is enabled for your project
3. Check that the service account has the necessary permissions
4. If using ADC, make sure the GOOGLE_APPLICATION_CREDENTIALS environment variable is set correctly

### API Key Restrictions

If you've restricted your API key and are encountering errors, make sure the restrictions allow the specific API calls you're making. You might need to add additional APIs or loosen the restrictions for testing.

## Testing Your Setup

You can test your YouTube API setup by running the test script:

```bash
python test_youtube_auth.py
```

This script will attempt to authenticate with the YouTube API using both the API key and Application Default Credentials methods.