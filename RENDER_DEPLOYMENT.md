# Deploying to Render

Follow these steps to deploy the Resume Ranking Portal to Render.com.

## Prerequisites
1.  You have a [Render account](https://render.com/).
2.  You have pushed this code to a GitHub repository.

## Step 1: Create a New Web Service
1.  Log in to your Render dashboard.
2.  Click **New +** and select **Web Service**.
3.  Connect your GitHub account if you haven't already.
4.  Select the repository `hiring_agent`.

## Step 2: Configure the Service
Fill in the details as follows:

-   **Name**: `hiring-agent` (or any name you prefer)
-   **Region**: Choose the one closest to you (e.g., Singapore, Frankfurt)
-   **Branch**: `master` (or `main`)
-   **Root Directory**: Leave blank (defaults to root)
-   **Runtime**: `Python 3`
-   **Build Command**: `./build.sh`
-   **Start Command**: `gunicorn recruitment.wsgi:application`

## Step 3: Configure Environment Variables
Scroll down to the **Environment Variables** section and click **Add Environment Variable**. Add the following keys and values from your local `.env` file:

| Key | Value (Example/Description) |
| :--- | :--- |
| `GEMINI_API_KEY` | Your Google Gemini API Key |
| `DB_NAME` | `Recruitment` (or your internal DB name) |
| `DB_USER` | `render` (or your internal DB user) |
| `DB_PASSWORD` | Your internal DB password |
| `DB_HOST` | Your internal DB host |
| `DB_PORT` | `5432` |
| `SMTP_HOST` | `smtp.gmail.com` |
| `SMTP_PORT` | `587` |
| `SMTP_USER` | Your email address |
| `SMTP_PASSWORD` | Your app password |
| `FROM_EMAIL` | Your email address |
| `INTERVIEWER_EMAIL` | Your email address |
| `COMPANY_NAME` | `Tek Leaders` |
| `BASE_URL` | The URL of your Render service (e.g., `https://hiring-agent.onrender.com`) |

> **Note on Database**: You will need a PostgreSQL database. You can create one on Render by clicking **New +** -> **PostgreSQL**.
> 1.  Create the database first.
> 2.  Copy the **Internal Database URL** or the individual credentials (Host, User, Password, Database) to the environment variables above.
> 3.  **Important**: Ensure your Web Service and Database are in the same region for internal networking to work.

## Step 5: Configure Secret Files (Crucial for Calendar)
Your application uses `credentials.json` and `token.json` for Google Calendar integration. These files are not in GitHub for security. You must upload them to Render.

1.  Go to the **Environment** tab of your Web Service.
2.  Scroll down to **Secret Files**.
3.  Click **Add Secret File**.
4.  **File 1**:
    -   **Filename**: `credentials.json`
    -   **Content**: Open your local `credentials.json` file, copy the entire content, and paste it here.
5.  **File 2** (Optional but recommended to avoid re-auth):
    -   **Filename**: `token.json`
    -   **Content**: Open your local `token.json` file, copy the entire content, and paste it here.

## Step 6: Deploy
1.  Click **Create Web Service** (or **Manual Deploy** -> **Deploy latest commit** if you already created it).
2.  Render will start building your application. You can watch the logs in the dashboard.
3.  Once the build finishes and the service is live, you will see a green "Live" badge.

## Troubleshooting
-   **Database Connection**: If the app fails to connect to the DB, double-check the `DB_HOST` and credentials. If using Render Postgres, use the *Internal* host address.
-   **Build Failures**: Check the logs. Ensure `build.sh` is executable (git usually handles this, but you might need `git update-index --chmod=+x build.sh` locally if it fails).
