# Gmail Setup Instructions for JobSeeker AI

## Setting up Gmail App Password

To allow JobSeeker AI to read your job alert emails, you need to create an app-specific password for Gmail:

### Step 1: Enable 2-Factor Authentication
1. Go to your Google Account settings: https://myaccount.google.com/security
2. Under "How you sign in to Google", click on "2-Step Verification"
3. Follow the prompts to enable 2FA if not already enabled

### Step 2: Create App Password
1. Go to: https://myaccount.google.com/apppasswords
2. Sign in if prompted
3. Under "Select app", choose "Mail"
4. Under "Select device", choose "Other (custom name)"
5. Enter "JobSeeker AI" as the name
6. Click "Generate"
7. Copy the 16-character password shown (without spaces)

### Step 3: Update .env File
Add your app password to the `.env` file:

```bash
EMAIL_ADDRESS=echsia16@gmail.com
EMAIL_PASSWORD=your-16-char-password-here
```

### Step 4: Enable IMAP in Gmail
1. Open Gmail settings: https://mail.google.com/mail/u/0/#settings/fwdandpop
2. Under "IMAP access", select "Enable IMAP"
3. Click "Save Changes"

### Step 5: Create Filters for Job Alerts (Optional but Recommended)
To help the system find job alerts more easily:

1. In Gmail, create a label called "JobAlerts" or "Jobs"
2. Create filters to automatically label emails from:
   - noreply@upwork.com
   - jobs-noreply@linkedin.com
   - Indeed, AngelList, or other job platforms you use

## Testing the Connection

Once you've set up your app password, test the connection:

```bash
# Export environment variables
export $(grep -v '^#' .env | xargs)

# Run the ingestion test
python scripts/test_email_ingestion.py
```

## Security Notes
- The app password is specific to this application
- It can be revoked anytime from your Google Account settings
- Never share your app password or commit it to version control
- The password is stored locally in your .env file only