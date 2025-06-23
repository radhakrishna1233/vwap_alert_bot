from flask import Flask, request, jsonify
import yfinance as yf
import pandas as pd
from ta.volume import VolumeWeightedAveragePrice
import requests
import threading
import time

app = Flask(__name__)

BOT_TOKEN = '7751981897:AAE1XhdDBCqqggWagVKP7SQNhw0IUrJwNlM'
CHAT_ID = '698291858'

monitored_stocks = []

def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message}
    try:
        requests.post(url, data=data)
    except:
        print("Failed to send Telegram message")

def check_stock(symbol):
    try:
        df = yf.download(symbol, period="2d", interval="5m", progress=False)
        if df.empty:
            return

        df['vwap'] = VolumeWeightedAveragePrice(
            high=df['High'], low=df['Low'], close=df['Close'], volume=df['Volume']).vwap

        last = df.iloc[-1]
        body = abs(last['Close'] - last['Open'])
        upper_wick = last['High'] - max(last['Close'], last['Open'])
        lower_wick = min(last['Close'], last['Open']) - last['Low']
        avg_volume = df['Volume'].rolling(20).mean().iloc[-1]

        if last['Volume'] > 2 * avg_volume:
            send_telegram(f"🔔 {symbol}: Volume Spike! Vol = {int(last['Volume'])} > 2x Avg")

        if last['Close'] < last['vwap'] and upper_wick > 2 * body:
            send_telegram(f"⚠️ {symbol}: Bearish VWAP Rejection")

        if last['Close'] > last['vwap'] and lower_wick > 2 * body:
            send_telegram(f"⚠️ {symbol}: Bullish VWAP Rejection")

    except Exception as e:
        print(f"Error checking {symbol}: {e}")

def background_worker():
    while True:
        for symbol in monitored_stocks:
            check_stock(symbol)
        time.sleep(300)

@app.route('/')
def home():
    return "VWAP + Volume Spike Alert Bot is running."

@app.route('/add', methods=['POST'])
def add_stock():
    data = request.get_json()
    symbol = data.get('symbol')
    if symbol and symbol not in monitored_stocks:
        monitored_stocks.append(symbol)
        return jsonify({"message": f"{symbol} added."})
    return jsonify({"error": "Symbol missing or already added."})

@app.route('/remove', methods=['POST'])
def remove_stock():
    data = request.get_json()
    symbol = data.get('symbol')
    if symbol in monitored_stocks:
        monitored_stocks.remove(symbol)
        return jsonify({"message": f"{symbol} removed."})
    return jsonify({"error": "Symbol not in list."})

@app.route('/list')
def list_stocks():
    return jsonify({"stocks": monitored_stocks})

@app.route('/scan-now')
def manual_scan():
    for symbol in monitored_stocks:
        check_stock(symbol)
    return jsonify({"message": "Manual scan completed."})

if __name__ == '__main__':
    threading.Thread(target=background_worker, daemon=True).start()
    app.run(host='0.0.0.0', port=8080)