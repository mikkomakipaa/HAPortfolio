# Google Sheets Setup Guide

The Portfolio Tracker integration uses Google Service Account authentication to access your Google Sheets data. This is more reliable and secure than OAuth2 for automated data access.

## Step 1: Create a Google Cloud Project

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google Sheets API:
   - Go to "APIs & Services" > "Library"
   - Search for "Google Sheets API"
   - Click "Enable"

## Step 2: Create a Service Account

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "Service Account"
3. Fill in the service account details:
   - Name: `portfolio-tracker`
   - Description: `Service account for Portfolio Tracker HA integration`
4. Click "Create and Continue"
5. Skip role assignment (click "Continue")
6. Click "Done"

## Step 3: Generate Service Account Key

1. Click on the newly created service account
2. Go to the "Keys" tab
3. Click "Add Key" > "Create new key"
4. Select "JSON" format
5. Click "Create"
6. Save the downloaded JSON file securely

## Step 4: Share Google Sheets with Service Account

1. Open your portfolio Google Sheets document
2. Click "Share" in the top right
3. Add the service account email (found in the JSON file as `client_email`)
4. Give it "Viewer" permissions
5. Click "Send"

## Step 5: Configure Portfolio Tracker

1. In Home Assistant, go to Settings > Integrations
2. Add the Portfolio Tracker integration
3. Fill in the configuration:
   - **InfluxDB URL**: Your InfluxDB instance URL
   - **InfluxDB Username/Password**: Your InfluxDB credentials
   - **Database Name**: Database for portfolio data (default: `portfolio`)
   - **Google Sheets ID**: Copy from your Google Sheets URL
   - **Google Service Account JSON**: Paste the entire contents of the JSON file

## Google Sheets ID

The Google Sheets ID can be found in your Google Sheets URL:
```
https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/edit
                                      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                                      This is your Google Sheets ID
```

## Service Account JSON Format

The JSON file should look like this (with your actual values):
```json
{
  "type": "service_account",
  "project_id": "your-project-id",
  "private_key_id": "key-id",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
  "client_email": "portfolio-tracker@your-project.iam.gserviceaccount.com",
  "client_id": "123456789",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/..."
}
```

## Expected Google Sheets Format

Your Google Sheets should have columns like:

| symbol | quantity | price | value | change |
|--------|----------|-------|-------|--------|
| AAPL   | 10       | 150   | 1500  | 5.2    |
| GOOGL  | 5        | 2800  | 14000 | -12.5  |

- **symbol**: Stock ticker symbol
- **quantity**: Number of shares
- **price**: Current price per share
- **value**: Total value (quantity × price)
- **change**: Daily change amount

## Troubleshooting

### "No access to spreadsheet"
- Ensure the service account email has been shared with the Google Sheets
- Check that the Google Sheets ID is correct

### "Invalid JSON credentials"
- Verify the JSON format is correct
- Ensure all quotes and commas are properly placed
- Make sure it's a service account JSON (not OAuth2 credentials)

### "Google Sheets API not enabled"
- Go to Google Cloud Console
- Navigate to "APIs & Services" > "Library"
- Search for and enable "Google Sheets API"

## Security Notes

- **Never share your service account JSON**: It contains private keys
- **Use environment variables**: Consider storing credentials securely
- **Minimal permissions**: Only give the service account "Viewer" access to your sheets
- **Regular rotation**: Consider rotating service account keys periodically