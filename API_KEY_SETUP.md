# API Key Setup Guide

Your API key has been configured! Here's what was set up:

## ✅ Local Development (Already Done)
Your API key is stored in `.streamlit/secrets.toml` which is:
- ✅ Ignored by git (won't be committed)
- ✅ Automatically loaded by the app
- ✅ Secure and private

## 🚀 Streamlit Cloud Deployment

To use your API key on Streamlit Cloud, follow these steps:

### Step 1: Go to Your App Settings
1. Visit: https://share.streamlit.io/
2. Click on your app: `d28austin-pga`
3. Click the **⚙️ Settings** button (three dots menu)
4. Select **"Secrets"**

### Step 2: Add Your API Key
Paste this into the secrets editor:

```toml
[odds_api]
api_key = "d6f3e4e5d8ffa7935f1b311ffb2d64e5"
```

### Step 3: Save
1. Click **"Save"**
2. Your app will automatically restart
3. The API key will be available to your app

## 🧪 Testing

### Local Testing:
```bash
cd "C:\Users\Austin.Wheeler\OneDrive - bpx\Documents\VS Code\PGA"
streamlit run app.py
```

Then:
1. Select a tournament
2. Go to "🎯 Recommendations" tab
3. You should see "🔑 API Key loaded from secrets"
4. Check "Use Live Odds" to fetch real-time data

### On Streamlit Cloud:
After adding secrets:
1. Wait for app to restart (30-60 seconds)
2. Navigate to "🎯 Recommendations"
3. Should automatically detect your API key
4. Toggle "Use Live Odds" to fetch real data

## 📊 API Usage

Your free tier includes:
- ✅ 500 requests per month
- ✅ Access to 20+ bookmakers
- ✅ Real-time odds updates
- ✅ Tournament winner markets
- ✅ Top 10 finish markets (when available)

**Tip**: Each time you load the recommendations tab = 1 API request

Check your usage at: https://the-odds-api.com/account

## 🔒 Security Notes

**✅ DO:**
- Keep your API key in secrets
- Use `.streamlit/secrets.toml` for local dev
- Use Streamlit Cloud secrets for deployment

**❌ DON'T:**
- Commit API keys to GitHub
- Share your API key publicly
- Paste it directly in code

## 🆘 Troubleshooting

### "No API key found"
- Make sure secrets.toml exists in `.streamlit/` folder
- Check the format matches exactly (including brackets and quotes)

### "Invalid API key"
- Verify the key at: https://the-odds-api.com/account
- Make sure you copied the entire key
- Check for extra spaces or quotes

### "Rate limit exceeded"
- You've used your 500 monthly requests
- Wait for next month or upgrade your plan
- Use sample data in the meantime

## 📈 Next Steps

Now that your API key is configured:

1. **Test it locally**: Run the app and check the recommendations tab
2. **Add to Streamlit Cloud**: Follow steps above to deploy with live odds
3. **Explore features**:
   - View live tournament winner odds
   - See value edges for players
   - Export recommendations with betting data

## 🔄 Updating Your Key

If you need to change your API key:

**Locally:**
Edit `.streamlit/secrets.toml`

**Streamlit Cloud:**
1. Go to app settings
2. Edit secrets
3. Save (app will restart)

---

**Your API Key**: `d6f3e4e5d8ffa7935f1b311ffb2d64e5`
**Dashboard**: https://the-odds-api.com/account
