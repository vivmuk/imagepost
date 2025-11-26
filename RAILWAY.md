# 🚂 Railway Deployment Guide

This guide will help you deploy the Venice AI Summary Report Generator to Railway.

## Prerequisites

- Railway account (sign up at [railway.app](https://railway.app))
- GitHub repository connected (already done: https://github.com/vivmuk/imagepost)
- Venice API key

## Step 1: Create a New Railway Project

1. Go to [Railway Dashboard](https://railway.app/dashboard)
2. Click **"New Project"**
3. Select **"Deploy from GitHub repo"**
4. Choose your repository: `vivmuk/imagepost`
5. Railway will automatically detect it's a Python project

## Step 2: Configure Environment Variables

**⚠️ IMPORTANT: You MUST add your Venice API key as an environment variable!**

1. In your Railway project, go to the **Variables** tab
2. Click **"New Variable"**
3. Add the following:

| Variable Name | Value | Description |
|---------------|-------|-------------|
| `VENICE_API_KEY` | `lnWNeSg0pA_rQUooNpbfpPDBaj2vJnWol5WqKWrIEF` | Your Venice API key (required) |

### Optional Environment Variables

You can also customize these (defaults will be used if not set):

| Variable Name | Default | Description |
|---------------|---------|-------------|
| `VENICE_SUMMARIZATION_MODEL` | `qwen3-235b` | Model for summarization |
| `VENICE_IMAGE_MODEL` | `qwen-image` | Model for image generation |
| `REPORT_OUTPUT_DIR` | `reports` | Directory for generated reports |
| `IMAGE_WIDTH` | `1024` | Generated image width |
| `IMAGE_HEIGHT` | `768` | Generated image height |

## Step 3: Configure Build Settings

Railway should auto-detect Python, but verify:

1. Go to **Settings** → **Build**
2. **Build Command**: (leave empty or use `pip install -r requirements.txt`)
3. **Start Command**: `uvicorn server:app --host 0.0.0.0 --port $PORT`

## Step 4: Deploy

1. Railway will automatically deploy when you push to GitHub
2. Or click **"Deploy"** manually
3. Wait for the build to complete
4. Your app will be live at a Railway-provided URL (e.g., `https://your-app.railway.app`)

## Step 5: Test Your Deployment

1. Visit your Railway URL
2. You should see the API landing page
3. Test the API:
   ```bash
   curl -X POST https://your-app.railway.app/api/summarize/text \
     -H "Content-Type: application/json" \
     -d '{"text": "Test content", "title": "Test Report"}'
   ```

## Troubleshooting

### API Key Not Working
- Verify `VENICE_API_KEY` is set in Railway Variables
- Check the variable name matches exactly (case-sensitive)
- Restart the deployment after adding variables

### Build Fails
- Check Railway logs for error messages
- Ensure `requirements.txt` is in the root directory
- Verify Python version (Railway uses Python 3.11+ by default)

### App Crashes
- Check logs in Railway dashboard
- Verify all dependencies are in `requirements.txt`
- Ensure port is set correctly: `--port $PORT`

## Monitoring

- **Logs**: View real-time logs in Railway dashboard
- **Metrics**: Monitor CPU, memory, and network usage
- **Deployments**: Track deployment history

## Custom Domain (Optional)

1. Go to **Settings** → **Networking**
2. Click **"Generate Domain"** or add your custom domain
3. Railway will provide SSL certificates automatically

## Cost Considerations

- Railway offers a free tier with $5/month credit
- API calls to Venice will consume your Venice API credits
- Monitor usage in both Railway and Venice dashboards

## Security Notes

✅ **DO:**
- Use environment variables for API keys
- Keep your API key secret
- Use Railway's built-in secrets management

❌ **DON'T:**
- Commit API keys to Git
- Share your Railway deployment URL publicly if it contains sensitive data
- Expose API keys in client-side code

---

**Need Help?** Check Railway's [documentation](https://docs.railway.app) or the project's [README.md](README.md)

