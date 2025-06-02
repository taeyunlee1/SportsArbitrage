🧠 Sports Arbitrage Finder Dashboard
A real-time dashboard for detecting and visualizing arbitrage opportunities across major sportsbooks. Built with Dash, Plotly, Selenium, and undetected_chromedriver, this tool scrapes live betting odds and identifies risk-free profit scenarios using arbitrage strategies.

🚀 Features
🔍 Live Odds Scraping from FanDuel, DraftKings, and BetMGM

📈 Arbitrage Detection using implied probability calculations and edge filtering

📊 Interactive Dashboard with ROI gauges, odds comparisons, and stake calculations

✅ Kelly Criterion staking strategy for risk-adjusted betting

⏱️ Auto-refresh every 60 seconds to show updated opportunities

📦 Requirements
Python 3.8+

Google Chrome

ChromeDriver (managed by undetected_chromedriver)

🛠️ Installation
bash
Copy
Edit
git clone https://github.com/<your_username>/arbitrage-dashboard.git
cd arbitrage-dashboard
conda create -n arb_env python=3.11
conda activate arb_env
pip install -r requirements.txt
If you don’t have requirements.txt, install dependencies manually:

bash
Copy
Edit
pip install dash plotly pandas numpy selenium undetected-chromedriver gevent dash-bootstrap-components
🧪 Usage
bash
Copy
Edit
python arbitrage.py
A Dash web server will launch at http://127.0.0.1:8050/.

📸 Dashboard Preview
Table of arbitrage opportunities

Profit Gauge showing best ROI found

Bar Chart of sportsbook pairs with most arbs

Scatter Plot comparing odds with ROI size scaling

Histogram of ROI distribution

🔐 Notes
Make sure Chrome is installed on your system.

This project uses undetected_chromedriver to bypass bot detection on sportsbooks.

VPNs or proxies may be required depending on sportsbook access in your region.

🧠 How It Works
Scraper: Launches headless Chrome drivers for each sportsbook and collects data using XPath.

Detector: Converts American odds to decimal, computes implied probabilities, and checks for arbitrage opportunities.

Dashboard: Displays all data in an interactive UI built with Dash and Plotly.
