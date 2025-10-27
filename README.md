# Stravan-lyzer

[![Python: 3.10](https://img.shields.io/badge/Python-3.10-blue.svg)](https://www.python.org/downloads/release/python-3100/)
[![Streamlit](https://img.shields.io/badge/Built%20with-Streamlit-FF4B4B.svg)](https://streamlit.io/)
[![Docker](https://img.shields.io/badge/Docker-ready-blue.svg?logo=docker)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

A simple, modern, and self-hosted dashboard to analyze your exported Strava `activities.csv` file. This project uses Streamlit to create the interactive web app and Docker to containerize it for easy deployment.

It is designed to be run locally or placed behind a reverse proxy like Nginx Proxy Manager.

## Features

* **Top-Level KPIs:** View your all-time totals for Distance, Time, Elevation, Calories, and more.
* **Interactive Filters:** Filter your entire dashboard by Year and Activity Type.
* **Detailed Charts:**
    * **Monthly Distance:** A stacked bar chart showing total distance per month, color-coded by activity type.
    * **Cumulative Distance:** A line chart showing your distance accumulation over time.
* **Activity Heatmaps:**
    * **Hourly Activity:** See what time of day and day of week you are most active.
    * **Total Distance:** A grid of Day of Week vs. Month.
    * **Average Speed:** Find out when you are fastest.
    * **Activity Count:** See when you are most consistent.
* **Data Tables:**
    * **Breakdown by Type:** A summary table of all key metrics for each activity (Ride, Run, Hike, etc.).
    * **Recent Activities:** A list of your last 20 activities.

---

## 1. Quickstart (Local-Only)

This is the fastest way to get your dashboard running on your local machine.

### Prerequisites
* [Docker](httpss://www.docker.com/get-started) is installed and running.
* You have unzipped your Strava export and found the `activities.csv` file.

### Steps
1.  **Place Your Data:** Put your `activities.csv` file into this project's directory.

2.  **Build the Docker Image:** Open a terminal in this directory and run:
    ```bash
    docker build -t strava-dashboard .
    ```

3.  **Run the Container:**
    ```bash
    docker run -d --name strava-app -p 8501:8501 -v "$(pwd)/activities.csv:/app/activities.csv" strava-dashboard
    ```
    *(For Windows CMD, use `"%cd%` instead of `$(pwd)`)*

4.  **View Your Dashboard:**
    Open your browser and go to: **[http://localhost:8501](http://localhost:8501)**

---

## 2. Running with Nginx Proxy Manager

This is the recommended way to securely access your dashboard from a custom domain (e.g., `strava.yourdomain.com`).

There are two ways to configure this.

### Option A: Host IP Mode (Simple)

This method uses the `docker run` command from the Quickstart guide.

1.  **Run the Container:** Use the same `docker run` command from Step 3 above, which includes `-p 8501:8501`.
2.  **Find Your Host IP:** Find your computer's internal IP address (e.g., `192.168.1.50`). Do not use `localhost` or `127.0.0.1`.
3.  **Configure NPM:**
    * **Details Tab:**
        * **Domain Name:** `strava.yourdomain.com`
        * **Scheme:** `http`
        * **Forward Hostname / IP:** `192.168.1.50` (Your host's IP)
        * **Forward Port:** `8501`
        * **Websockets Support:** ✅ **Enabled** (This is required)
    * **Advanced Tab:** Paste this custom Nginx configuration:
        ```nginx
        location / {
            proxy_set_header        Host $host;
            proxy_set_header        X-Real-IP $remote_addr;
            proxy_set_header        X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header        X-Forwarded-Proto $scheme;
            proxy_set_header        Upgrade $http_upgrade;
            proxy_set_header        Connection "upgrade";
            proxy_read_timeout      86400;
        }
        ```

### Option B: Shared Docker Network (Best Practice)

This method is more robust, as it doesn't rely on your host's IP address and doesn't require exposing any ports.

1.  **Find your NPM Network:** Run `docker network ls` and find your Nginx Proxy Manager network (e.g., `npm_default`).
2.  **Stop/Remove Old Container:** `docker stop strava-app && docker rm strava-app`
3.  **Run on the Network:** Run the container again, but **remove the `-p` flag** and **add the `--network` flag**.
    ```bash
    docker run -d --name strava-app --network npm_default -v "$(pwd)/activities.csv:/app/activities.csv" strava-dashboard
    ```
    *(Replace `npm_default` with your actual network name)*

4.  **Configure NPM:**
    * **Details Tab:**
        * **Forward Hostname / IP:** `strava-app` (The container name)
        * **Forward Port:** `8501`
        * **Websockets Support:** ✅ **Enabled**
    * **Advanced Tab:** Paste the same Nginx configuration as in Option A.

---

## 3. Troubleshooting

### The app is stuck on "Loading..." or "Please wait..."

This is a WebSocket or caching issue.

1.  **NPM Config:** Double-check that **Websockets Support** is ON and your **Advanced** Nginx config is pasted correctly.
2.  **Clear Your Cache:** Your browser is loading an old, broken version. You **must** perform a hard refresh:
    * **Windows/Linux:** `Ctrl` + `F5`
    * **Mac:** `Cmd` + `Shift` + `R`
    * **Or:** Open Developer Tools (`F12`), go to the "Network" tab, check "Disable cache", and refresh.

### The dashboard crashes with a `KeyError` or "Distance is 0"

Your `activities.csv` file may have different column names than the one this script was based on. The script (in `dashboard.py`) tries to find `Distance.1` and `Elevation Gain`. You may need to edit the `load_data()` function to match your specific column names.

### About the `Dockerfile`

The `CMD` line in the `Dockerfile` includes special flags to make Streamlit work behind a reverse proxy. If you are having issues, ensure your `Dockerfile` has these flags:

```dockerfile
# ...
CMD ["streamlit", "run", "dashboard.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true", \
     "--server.enableCORS=false", \
     "--server.enableXsrfProtection=false", \
     "--server.baseUrlPath=\"\""]
