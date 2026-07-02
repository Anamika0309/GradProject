# Deployment Checklist

This document guides you through deploying your AI Product Insights Engine for public access. We use two different platforms:
- **Render** for the Python AI Backend (since it requires a running Python server)
- **Vercel** for the HTML/JS Frontend (since it's incredibly fast and free for static files)

---

## Part 1: Deploy Backend to Render

1. Go to [Render.com](https://render.com/) and sign in with your GitHub account.
2. Click **New** -> **Web Service**.
3. Select **Build and deploy from a Git repository**.
4. Connect your `GradProject` GitHub repository.
5. Configure the service:
   - **Name:** `ai-product-insights-backend`
   - **Language:** Python
   - **Branch:** `main`
   - **Build Command:** `pip install -r phase-2/requirements.txt`
   - **Start Command:** `gunicorn --chdir phase-2 server:app --bind 0.0.0.0:$PORT`
   - **Instance Type:** Free
6. Expand the **Advanced** section to add Environment Variables:
   - Click **Add Environment Variable**
   - Key: `GROQ_API_KEY` | Value: *(Paste your Groq API key here)*
   - Key: `OPENAI_API_KEY` | Value: *(Optional: Paste your OpenAI key here)*
7. Click **Create Web Service**.
8. **Wait for it to build.** Once it says "Live", copy the URL at the top left of the screen (e.g. `https://ai-product-insights-backend-123.onrender.com`).

---

## Part 2: Connect Frontend to Backend

Now that the backend is live on the internet, your frontend needs to know where it is.

1. Open your code editor and go to `phase-3/frontend/app.js`.
2. Find line 12: `const API_HOST = 'http://localhost:5678';`
3. Change it to your new Render URL:
   ```javascript
   const API_HOST = 'https://ai-product-insights-backend-123.onrender.com';
   ```
4. Save the file.
5. Push this change to GitHub:
   ```bash
   git add phase-3/frontend/app.js
   git commit -m "Update API host for production"
   git push
   ```

---

## Part 3: Deploy Frontend to Vercel

1. Go to [Vercel.com](https://vercel.com/) and sign in with your GitHub account.
2. Click **Add New** -> **Project**.
3. Import your `GradProject` GitHub repository.
4. Click **Deploy**. (You don't need to change any settings! We already created `vercel.json` which automatically configures the routing for you).
5. **Wait for it to build.**
6. Click **Continue to Dashboard** and click on your new domain!

🎉 **Congratulations! Your system is now publicly accessible.** 
You can share the Vercel link with your senior reviewers.
