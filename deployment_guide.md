# Deployment Guide -- Cognitive Routing & RAG AI Engine

This guide details how to deploy your interactive dashboard to various hosting platforms. The application is built using Streamlit, which runs entirely in Python and requires no custom frontend build steps.

---

## Prerequisites
Before deploying, make sure you have:
1. A **GitHub account** and your repository pushed online.
2. A **Groq API Key** (obtainable for free at [console.groq.com](https://console.groq.com)).

---

## Option 1: Streamlit Community Cloud (Recommended & Free)
Streamlit Community Cloud is the easiest way to deploy this application. It reads directly from your GitHub repository and automatically deploys changes when you push.

### Step-by-Step Instructions:
1. **Push your code to GitHub**:
   Ensure your repository includes all the files (`streamlit_app.py`, `requirements.txt`, `src/`, etc.).
2. **Log into Streamlit**:
   Go to [share.streamlit.io](https://share.streamlit.io) and log in with your GitHub account.
3. **Deploy a New App**:
   - Click the **"New app"** button.
   - Select your repository, branch (e.g., `main`), and set the main file path to `streamlit_app.py`.
4. **Configure Secrets**:
   - Before clicking deploy, click **"Advanced settings..."** or go to the App settings dashboard after deploying.
   - In the **Secrets** text box, add your Groq API Key as a secret so it is automatically set in the app environment variables:
     ```toml
     GROQ_API_KEY = "gsk_your_actual_groq_api_key_here"
     ```
5. **Launch**:
   - Click **"Deploy!"**.
   - Your application will build and be live at a public URL (e.g., `https://your-app-name.streamlit.app`) in 1-2 minutes!

---

## Option 2: Hugging Face Spaces (Free)
Hugging Face Spaces is another free option that supports Streamlit applications natively.

### Step-by-Step Instructions:
1. **Create a Hugging Face Account**: Log in or sign up at [huggingface.co](https://huggingface.co/).
2. **Create a New Space**:
   - Go to [huggingface.co/new-space](https://huggingface.co/new-space).
   - Give your space a name.
   - Select **Streamlit** as the SDK.
   - Choose public or private license.
3. **Upload Code**:
   - Clone the space repository locally or upload files directly through the Hugging Face web interface.
   - Add all project files (`streamlit_app.py`, `requirements.txt`, and the `src/` directory).
4. **Add Secrets**:
   - In your Space's dashboard, go to the **Settings** tab.
   - Under **Variables and secrets**, click **"New secret"**.
   - Set the name to `GROQ_API_KEY` and the value to your Groq API Key.
5. **View Live App**:
   - The app will automatically build and start running under the Hugging Face space URL!

---

## Option 3: Render (PaaS)
If you require custom domains, specific computing instances, or private networks, you can deploy to Render.

### Step-by-Step Instructions:
1. **Create a Render Account**: Log in at [render.com](https://render.com).
2. **Create a Web Service**:
   - Click **"New +"** and select **"Web Service"**.
   - Link your GitHub repository.
3. **Configure Settings**:
   - **Environment**: Select `Python`.
   - **Build Command**:
     ```bash
     pip install -r requirements.txt
     ```
   - **Start Command**:
     ```bash
     streamlit run streamlit_app.py --server.port $PORT --server.address 0.0.0.0
     ```
4. **Add Environment Variables**:
   - Click **"Advanced"** and add an environment variable:
     - Key: `GROQ_API_KEY`
     - Value: `your-groq-api-key-here`
5. **Deploy**: Click **"Create Web Service"**. Render will deploy it automatically.

---

## Running Locally (Testing)
To run and test the web app on your local machine before pushing to production:

```bash
# 1. Activate your virtual environment
.venv\Scripts\activate

# 2. Install dependencies (including streamlit and plotly)
pip install -r requirements.txt

# 3. Launch the dashboard
streamlit run streamlit_app.py
```
Streamlit will automatically open a browser window at `http://localhost:8501`.
