import time
import logging
import os
import gspread
import pytz
import datetime
import requests
from bs4 import BeautifulSoup
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv
from plyer import notification
from oauth2client.service_account import ServiceAccountCredentials


in_trade = False  # Tracks whether a trade is active
trade_price = None  # Stores the buy price

# ✅ Load environment variables
load_dotenv()
SLACK_TOKEN = os.getenv("SLACK_TOKEN")
SLACK_CHANNEL_ID = os.getenv("SLACK_CHANNEL_ID")

# ✅ Set up Slack Client
slack_client = WebClient(token=SLACK_TOKEN) if SLACK_TOKEN else None

# ✅ Logging Setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# ✅ Google Sheets Setup
SPREADSHEET_NAME = "Stock Data"
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("gspread-credentials.json", scope)
client = gspread.authorize(creds)

# ✅ Price Log Sheet (Stores Price Data)
try:
    sheet = client.open(SPREADSHEET_NAME).worksheet("Price Log")
except:
    sheet = client.open(SPREADSHEET_NAME).add_worksheet(title="Price Log", rows="1000", cols="4")
    sheet.append_row(["Timestamp", "ICICI Price", "Trade Signal", "Pivot Level Alert"])

def log_price_data(price, trade_signal="", pivot_alert=""):
    """Logs ICICI Bank stock price and relevant alerts in Google Sheets."""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # ✅ Append new data to the "Price Log" sheet
    sheet.append_row([now, price, trade_signal, pivot_alert])

    logging.info(f"📊 Logged Data: {now}, Price: ₹{price}, Signal: {trade_signal}, Alert: {pivot_alert}")

# ✅ Pivot Levels Sheet
try:
    pivot_sheet = client.open(SPREADSHEET_NAME).worksheet("Pivot Levels")
except:
    pivot_sheet = client.open(SPREADSHEET_NAME).add_worksheet(title="Pivot Levels", rows="100", cols="10")
    pivot_sheet.append_row(["Date", "Type", "PP", "R1", "R2", "R3", "S1", "S2", "S3"])

def log_pivot_levels(pp, r1, r2, r3, s1, s2, s3):
    """Logs pivot levels in Google Sheets."""
    today_date = datetime.datetime.now().strftime("%Y-%m-%d")

    # ✅ Append new row with pivot levels
    pivot_sheet.append_row([today_date, "Daily", pp, r1, r2, r3, s1, s2, s3])
    
    logging.info(f"📊 Pivot Levels Logged: {today_date}, PP: {pp}, R1: {r1}, S1: {s1}")

# ✅ ICICI Movements Sheet (Tracks large price changes per hour)
try:
    movement_sheet = client.open(SPREADSHEET_NAME).worksheet("ICICI Movements")
except:
    movement_sheet = client.open(SPREADSHEET_NAME).add_worksheet(title="ICICI Movements", rows="1000", cols="8")
    movement_sheet.append_row(["Date", "9AM-10AM", "10AM-11AM", "11AM-12PM", "12PM-1PM", "1PM-2PM", "2PM-3PM"])

# ✅ Track last known price
last_price = None
last_hour_alert = None  # Track last sent alert hour

# ✅ Check Market Hours
def is_market_open():
    ist = pytz.timezone("Asia/Kolkata")
    now = datetime.datetime.now(ist)
    market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
    market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
    return market_open <= now <= market_close and now.weekday() < 5  # Monday-Friday

# ✅ Send Slack Alerts
def send_slack_alert(message):
    """Send a Slack alert to notify about price changes and hourly movement counts."""
    try:
        if slack_client:
            slack_client.chat_postMessage(channel=SLACK_CHANNEL_ID, text=message)
        notification.notify(title="📢 ICICI Stock Alert", message=message, timeout=5)
        logging.info(f"📢 Slack Alert Sent: {message}")
    except SlackApiError as e:
        logging.error(f"❌ Slack API Error: {e.response['error']}")

# ✅ Start Chrome WebDriver with user profile
try:
    options = uc.ChromeOptions()
    
    # Use the existing Chrome user profile
    profile_path = r"C:\Users\LENOVO\AppData\Local\Google\Chrome\User Data"  # Update this path
    options.add_argument(f"--user-data-dir={profile_path}")
    options.add_argument("--profile-directory=Profile 1")    # Use your profile name
    
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    
    driver = uc.Chrome(options=options)
    driver.get("https://finance.yahoo.com/quote/ICICIBANK.NS/")
    logging.info("✅ Chrome WebDriver started successfully")

    send_slack_alert("🚀 *Stock Bot Started!* Tracking ICICI Bank price changes...")
except Exception as e:
    logging.error(f"❌ Failed to start Chrome WebDriver: {e}")
    send_slack_alert("❌ *Stock Bot Failed to Start!* Check logs for errors.")
    exit(1)

# ✅ Function to Log Large Movements in "ICICI Movements" Sheet
def log_large_movement(last_price,current_price):
    """Update the ICICI Movements sheet when a large price movement is detected."""
    
    # ✅ Ensure it only logs large movements (Increase of ₹3 or more)
    if current_price <= last_price or (current_price - last_price) < 3:
        return

    ist = pytz.timezone("Asia/Kolkata")
    now = datetime.datetime.now(ist)  # ✅ Ensure IST timezone
    today_date = now.strftime("%Y-%m-%d")
    current_hour = now.hour

    logging.info(f"🕒 Debug: Current IST Hour - {current_hour}")

    # ✅ Mapping hours to correct time slots
    time_columns = {9: 2, 10: 3, 11: 4, 12: 5, 13: 6, 14: 7}


    # ✅ Ensure we only log in valid market hours
    column_index = time_columns.get(current_hour, None)
    
    if column_index is None:
        logging.warning(f"⏳ Skipping log, time {current_hour}:00 is out of range.")
        return

    # ✅ Get all records and check if today's row exists
    records = movement_sheet.get_all_values()
    row_index = None

    for i, row in enumerate(records):
        if row[0] == today_date:
            row_index = i + 1  # ✅ Convert to 1-based index
            break

    if row_index is None:
        # ✅ Append a new row for today with all zeroes
        new_row = [today_date] + [0] * 6  # 6 hourly slots
        movement_sheet.append_row(new_row)
        row_index = len(records) + 1  # ✅ New row index

    # ✅ Read the current count
    current_value = movement_sheet.cell(row_index, column_index).value

    # ✅ Ensure it's an integer (default to 0 if empty)
    new_count = int(current_value) + 1 if current_value and current_value.isnumeric() else 1

    # ✅ Update the count in the respective column
    movement_sheet.update_cell(row_index, column_index, new_count)

    logging.info(f"📊 ICICI Movement Logged: {today_date}, {current_hour}:00 - {current_hour+1}:00 - Count: {new_count}")
  
# ✅ Send Hourly Summary Alerts
def send_hourly_summary():
    """Send an hourly alert summarizing movement count."""
    global last_hour_alert
    ist = pytz.timezone("Asia/Kolkata")
    now = datetime.datetime.now(ist)
    today_date = now.strftime("%Y-%m-%d")
    current_hour = now.hour  # ✅ Use current hour
     
    # ✅ Stop sending alerts after 2-3 PM
    if current_hour >= 15:
        logging.info(f"⏳ Skipping hourly summary, market tracking stops at 3 PM.")
        return 
    # Ensure we only send one alert per hour
    if last_hour_alert == current_hour:
        return

    # ✅ Get today's row
    records = movement_sheet.get_all_values()
    for row in records:
        if row[0] == today_date:
            column_index = (current_hour - 9) + 1  # Convert hour to column index
            
            # ✅ Check if the column exists in row
            if column_index >= len(row):  
                logging.warning(f"⏳ No data found for column index {column_index}, setting movements to 0.")
                movements = "0"
            else:
                movements = row[column_index] if row[column_index] else "0"

            alert_message = f"⏳ Hourly Update: ICICI Bank had {movements} significant price movements from {current_hour}:00 to {current_hour + 1}:00."
            send_slack_alert(alert_message)
            last_hour_alert = current_hour  # Update last alert hour
            break

def get_icici_price():
    """Fetch the latest ICICI Bank stock price from Yahoo Finance."""
    try:
        driver.refresh()  # Refresh to get the latest price
        time.sleep(5)  # Wait for page to load

        selectors = [
            "span[data-testid='qsp-price']",
            "fin-streamer[data-field='regularMarketPrice']"
        ]
        
        for selector in selectors:
            try:
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                price_element = driver.find_element(By.CSS_SELECTOR, selector)
                price = price_element.text.strip()
                return float(price.replace(",", "")) if price else None
            except:
                continue

        logging.error("❌ Could not find price element on Yahoo Finance.")
    except Exception as e:
        logging.error(f"❌ Error fetching ICICI stock price: {e}")
    return None
pivot_levels = {}  

# ✅ Fetch Pivot Levels Safely
def fetch_pivot_levels():
    """Fetch daily pivot levels from Moneycontrol and store in a dictionary."""
    try:
        url = "https://www.moneycontrol.com/india/stockpricequote/banks-private-sector/icicibank/ICI02"
        response = requests.get(url)
        soup = BeautifulSoup(response.text, "html.parser")

        pivot_data = {}  # ✅ Initialize Dictionary
        try:
            pivot_data["PP"] = float(soup.find("td", text="Pivot Point").find_next_sibling("td").text.strip())
            pivot_data["R1"] = float(soup.find("td", text="Resistance 1").find_next_sibling("td").text.strip())
            pivot_data["R2"] = float(soup.find("td", text="Resistance 2").find_next_sibling("td").text.strip())
            pivot_data["R3"] = float(soup.find("td", text="Resistance 3").find_next_sibling("td").text.strip())
            pivot_data["S1"] = float(soup.find("td", text="Support 1").find_next_sibling("td").text.strip())
            pivot_data["S2"] = float(soup.find("td", text="Support 2").find_next_sibling("td").text.strip())
            pivot_data["S3"] = float(soup.find("td", text="Support 3").find_next_sibling("td").text.strip())

        except AttributeError:
            logging.error("❌ Error parsing pivot levels. Check Moneycontrol's page structure.")
            return {}

        today_date = datetime.datetime.now().strftime("%Y-%m-%d")
        pivot_sheet.append_row([today_date, "Daily"] + list(pivot_data.values()))

        return pivot_data  # ✅ Return the pivot levels dictionary

    except Exception as e:
        logging.error(f"❌ Error fetching pivot levels: {e}")
        return {}

# ✅ Check Price Near Pivot Levels
def check_pivot_alerts(price):
    """Check if price is near pivot levels and send alerts."""
    global pivot_levels
    if not pivot_levels or "PP" not in pivot_levels:
        pivot_levels=fetch_pivot_levels()
    
    if not isinstance(pivot_levels,dict) or "PP" not in pivot_levels:
        logging.error("❌ pivot_levels does not contain 'PP'. Check fetch_pivot_levels().")
        return  

    for level, value in pivot_levels.items():
        if value and abs(price - value) <= 2:  # Alert if price is near any pivot level
            send_slack_alert(f"🎯 ICICI Bank Price near {level}: ₹{value} (Current: ₹{price})")

# ✅ Monitor Price Changes & Log Large Movements
def check_price_movements():
    """Monitor stock price changes, send alerts, and log large movements."""
    global last_price, in_trade, trade_price  # Declare globals
    current_price = get_icici_price()

    if current_price is None:
        return

    if last_price is None:
        last_price = current_price  # Set initial price

    trade_signal = ""
    pivot_alert = ""

    # ✅ Detect any price movement
    if current_price != last_price:
        direction = "⬆️ Increased" if current_price > last_price else "⬇️ Decreased"
        alert_message = f"⚡ *ICICI Bank {direction}!* New Price: ₹{current_price} (Prev: ₹{last_price})"
        send_slack_alert(alert_message)
        # ✅ Check for Buy Signal
        if not in_trade and current_price > last_price:
            send_slack_alert("💹 ICICI Bank is rising, checking for buy opportunity...")
            trade_price = current_price  # Store the buy price
            in_trade = True  # Mark as active trade
            send_slack_alert(f"✅ ICICI Bank stock bought at ₹{trade_price}")

        # ✅ Check for Sell Signal (Successful Trade)
        if in_trade and current_price >= trade_price + 2:
            send_slack_alert(f"🎯 ICICI Bank sold at ₹{current_price} (Profit: ₹{current_price - trade_price})")
            in_trade = False  # Reset trade status
            trade_price = None

         # ✅ Check for Stoploss
        if in_trade and current_price <= trade_price - 5:
            send_slack_alert(f"🚨 Stoploss hit at ₹{current_price}, exiting trade...")
            in_trade = False  # Reset trade status
            trade_price = None
        
        # ✅ Check for Pivot Alerts
        check_pivot_alerts(current_price)
        
        # ✅ Log the price and trade signal
        log_price_data(current_price, trade_signal, pivot_alert)

        # ✅ Log large price movements in ICICI Movements Sheet
        log_large_movement(last_price,current_price)

    last_price = current_price  # Update last known price
    send_hourly_summary()  # Send hourly summary
    # ✅ Market Risk Reminder
    send_slack_alert("⚠️ Gentle Reminder: The share market is risky. Be careful when investing!")

# ✅ Main Monitoring Loop
try:
    while True:
        if is_market_open():
            check_price_movements()
        else:
            ist = pytz.timezone("Asia/Kolkata")
            current_time = datetime.datetime.now(ist)

            # Check if the market closed after 3:30 PM
            if current_time.hour >= 15 and current_time.minute >= 30:
                send_slack_alert("⏳ Market Closed....Waiting for next trading day....")
                logging.info("📢 Market is closed after 3:30 PM. Alert sent.")
                
                # Sleep until the next day's market open time (9:15 AM)
                time_to_wait = (24 - current_time.hour + 9) * 3600 + (15 - current_time.minute) * 60  # Calculate the time in seconds
                time.sleep(time_to_wait)

                send_slack_alert("🚀 *Market Opened!* Resuming ICICI Bank tracking....")
                logging.info("✅ Market reopened at 9:15 AM. Resuming normal tracking...")
            # If the market is closed before 3:30 PM, wait until 3:30 PM
            else:
                send_slack_alert("⏳ Market Closed....Waiting for next trading day....")
                logging.info("📢 Market is closed. Alert sent.")
            
            while not is_market_open():
                time.sleep(3600)  # Sleep for 1 hour before checking again
                send_slack_alert("⏳ Market Closed....Waiting for next trading day....")
            
            send_slack_alert("🚀 *Market Opened!* Resuming ICICI Bank tracking....")
            logging.info("✅ Market reopened. Resuming normal tracking...")

except KeyboardInterrupt:
    send_slack_alert("🛑 *Stock Bot Stopped!* No longer tracking ICICI Bank.")
    logging.info("\nStopping bot...")
    driver.quit()
except Exception as e:
    error_message = f"❌ *Stock Bot Error!* {str(e)}"
    send_slack_alert(error_message)
    logging.error(f"Unexpected error: {str(e)}")
    import traceback
    logging.error(traceback.format_exc())
    driver.quit()
    
