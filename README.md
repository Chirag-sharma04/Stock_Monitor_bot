# ICICI Bank Stock Monitor Bot

This Python script monitors the ICICI Bank stock price from Yahoo Finance, logs price changes and significant movements, detects potential buy/sell signals, and sends alerts via Slack and desktop notifications. It also tracks pivot levels and logs data to Google Sheets.

## Features

* **Real-time Price Monitoring:** Fetches and tracks ICICI Bank stock prices from Yahoo Finance.
* **Trade Signal Detection:** Identifies potential buy/sell signals and stop-loss triggers.
* **Pivot Level Alerts:** Notifies when the stock price is near pivot levels.
* **Significant Movement Tracking:** Logs large price movements hourly.
* **Google Sheets Integration:** Stores price data, pivot levels, and hourly movement counts in Google Sheets.
* **Slack Integration:** Sends real-time alerts and summaries to a Slack channel.
* **Desktop Notifications:** Provides local desktop notifications for price alerts.
* **Market Hour Awareness:** Operates only during Indian stock market hours.
* **Error Handling:** Robust error handling and logging.

## Prerequisites

* Python 3.x
* Google Cloud Platform project with Google Sheets API enabled.
* Slack API token and channel ID.
* Chrome browser and undetected-chromedriver.
* `dotenv` for managing environment variables.
* `gspread` and `oauth2client` for Google Sheets integration.
* `requests` and `beautifulsoup4` for web scraping.
* `selenium` and `undetected-chromedriver` for web automation.
* `slack_sdk` for Slack integration.
* `pytz` for timezone handling.
* `plyer` for desktop notifications.

## Installation

1.  **Clone the repository:**

    ```bash
    git clone <repository_url>
    cd <repository_directory>
    ```

2.  **Install dependencies:**

    ```bash
    pip install requests beautifulsoup4 undetected-chromedriver selenium slack_sdk python-dotenv gspread oauth2client pytz plyer
    ```

3.  **Set up Google Sheets API:**

    * Create a Google Cloud Platform project.
    * Enable the Google Sheets API.
    * Create a service account and download the JSON credentials file (rename it to `gspread-credentials.json` and place it in the same directory as the script).
    * Create a Google Sheet named "Stock Data".
    * Share the Google Sheet with the service account email address.

4.  **Set up Slack API:**

    * Create a Slack app and obtain a Slack API token.
    * Obtain the Slack channel ID where you want to receive alerts.

5.  **Configure environment variables:**

    * Create a `.env` file in the same directory as the script.
    * Add the following lines to the `.env` file, replacing the placeholders with your actual values:

        ```
        SLACK_TOKEN=your_slack_token
        SLACK_CHANNEL_ID=your_slack_channel_id
        ```

6.  **Configure Chrome profile path:**

    * Update the `profile_path` variable in the script to the path of your Chrome user data directory.
    * Update the `profile-directory` variable to your chrome profile name.

## Usage

1.  Run the script:

    ```bash
    python your_script_name.py
    ```

2.  The script will start monitoring the ICICI Bank stock price and send alerts to your Slack channel and desktop.

## Google Sheets Structure

* **Price Log:**
    * Columns: Timestamp, ICICI Price, Trade Signal, Pivot Level Alert
* **Pivot Levels:**
    * Columns: Date, Type, PP, R1, R2, R3, S1, S2, S3
* **ICICI Movements:**
    * Columns: Date, 9AM-10AM, 10AM-11AM, 11AM-12PM, 12PM-1PM, 1PM-2PM, 2PM-3PM.

## Notes

* Ensure that the Chrome WebDriver is compatible with your Chrome browser version.
* The script assumes that the Yahoo Finance and Moneycontrol websites maintain their current structure. If the websites' structure changes, the script may need to be updated.
* The script operates only during Indian stock market hours (9:15 AM to 3:30 PM IST).
* The script uses a basic trading strategy. You may need to adjust the buy/sell signals and stop-loss parameters based on your trading strategy.
* Use caution when using this bot for live trading. The stock market is risky.
