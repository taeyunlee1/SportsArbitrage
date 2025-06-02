import time
import logging
import sys
import linecache
import random
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException
from gevent.pool import Pool
from gevent import monkey
monkey.patch_all()

import numpy as np
import pandas as pd
import plotly.graph_objs as go
from dash import Dash, dcc, html, Input, Output
import dash_bootstrap_components as dbc

logging.disable(logging.CRITICAL)

class SportsbookScraper:
    def __init__(self):
        self.drivers = {
            'fanduel': self.init_driver('https://sportsbook.fanduel.com/live'),
            'draftkings': self.init_driver('https://sportsbook.draftkings.com/live'),
            'betmgm': self.init_driver('https://sports.betmgm.com/en/live')
        }
        self.sport = 'Baseball'
        self.xpaths = {
            'fanduel': {
                'games': "//a[@target='_self' and contains(@title,'@')]",
                'teams': ".//div[contains(@style,'background-image')]/../div[2]/span",
                'odds': "./div/div/div"
            },
            'draftkings': {
                'games': "(//tbody[@class='sportsbook-table__body'])[1]//tr",
                'teams': ".//div[@class='event-cell__name-text']",
                'odds': ".//td[contains(@class,'sportsbook-table__column-row')]"
            },
            'betmgm': {
                'games': "//div[contains(@class,'live-event-row')]",
                'teams': ".//div[contains(@class,'participant-name')]",
                'odds': ".//div[contains(@class,'outcome-odds')]"
            }
        }

    def init_driver(self, url):
        driver = uc.Chrome()
        driver.implicitly_wait(5)
        driver.get(url)
        return driver

    def normalize_team_name(self, name):
        if 'Sox' in name:
            return ' '.join(name.split(' ')[-2:])
        return name.split(' ')[-1]

    def scrape_odds(self):
        data = {}
        pool = Pool(len(self.drivers))
        for book, driver in self.drivers.items():
            pool.apply_async(self._scrape_book, args=(book, driver, data))
        pool.join()
        return data

    def _scrape_book(self, book, driver, data):
        try:
            games = driver.find_elements(By.XPATH, self.xpaths[book]['games'])
            book_data = {}
            for game in games:
                try:
                    teams = [self.normalize_team_name(t.text.lower()) for t in game.find_elements(By.XPATH, self.xpaths[book]['teams'])]
                    key = f"{teams[0]} vs {teams[1]}"
                    odds_elements = game.find_elements(By.XPATH, self.xpaths[book]['odds'])
                    odds = [self._parse_odds(o.text) for o in odds_elements[:6]]
                    book_data[key] = {
                        'teams': teams,
                        'moneyline': odds[0:2],
                        'spread': odds[2:4],
                        'total': odds[4:6],
                        'timestamp': time.time()
                    }
                except:
                    continue
            data[book] = book_data
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.CONTROL + Keys.HOME)
        except Exception as e:
            print(f"Error scraping {book}: {str(e)}")

    def _parse_odds(self, odds_text):
        if not odds_text:
            return None
        odds_text = odds_text.replace('\n', ' ').replace('−', '-').replace(',', '').strip()
        try:
            return int(float(odds_text))
        except:
            return None

class ArbitrageDetector:
    def __init__(self):
        self.min_arb_percent = 0.01
        self.max_odds = 1000
        self.min_bet = 0.10

    def find_arbs(self, odds_data):
        arbs = []
        game_keys = set().union(*[d.keys() for d in odds_data.values()])
        for game_key in game_keys:
            game_books = {b: d.get(game_key) for b, d in odds_data.items() if game_key in d and d[game_key]}
            if len(game_books) < 2:
                continue
            for market in ['moneyline', 'spread', 'total']:
                market_arbs = self._check_market(game_books, market)
                if market_arbs:
                    arbs.extend(market_arbs)
        return pd.DataFrame(arbs)

    def _check_market(self, game_books, market):
        arbs = []
        books = list(game_books.keys())
        for i in range(len(books)):
            for j in range(i+1, len(books)):
                book1, book2 = books[i], books[j]
                data1 = game_books[book1][market]
                data2 = game_books[book2][market]
                if not data1 or not data2:
                    continue
                for outcome1 in [0, 1]:
                    for outcome2 in [0, 1]:
                        if outcome1 == outcome2:
                            continue
                        odds1 = data1[outcome1]
                        odds2 = data2[outcome2]
                        if None in [odds1, odds2]:
                            continue
                        arb = self._calculate_arb(odds1, odds2, book1, book2, game_books[book1]['teams'], market)
                        if arb:
                            arbs.append(arb)
        return arbs

    def _calculate_arb(self, odds1, odds2, book1, book2, teams, market):
        dec1 = self._american_to_decimal(odds1)
        dec2 = self._american_to_decimal(odds2)
        if None in [dec1, dec2]:
            return None
        prob1 = 1 / dec1
        prob2 = 1 / dec2
        total_prob = prob1 + prob2
        if total_prob >= 1 + self.min_arb_percent:
            bankroll = 1000
            edge = 0.01
            kelly1 = ((dec1 - 1) * (1 - prob2 - edge) - prob2) / (dec1 - 1)
            kelly2 = ((dec2 - 1) * (1 - prob1 - edge) - prob1) / (dec2 - 1)
            kelly1 = max(0, min(kelly1, 1))
            kelly2 = max(0, min(kelly2, 1))
            stake1 = kelly1 * bankroll
            stake2 = kelly2 * bankroll
            total_stake = stake1 + stake2
            profit1 = stake1 * dec1 - total_stake
            profit2 = stake2 * dec2 - total_stake
            profit = min(profit1, profit2)
            roi = (profit / total_stake) * 100 if total_stake > 0 else 0
            return {
                'game': f"{teams[0]} vs {teams[1]}",
                'market': market,
                'book1': book1,
                'book2': book2,
                'team1': teams[0],
                'team2': teams[1],
                'odds1': odds1,
                'odds2': odds2,
                'stake1': stake1,
                'stake2': stake2,
                'total_stake': total_stake,
                'profit': profit,
                'roi': roi,
                'timestamp': time.time(),
                'arb_percent': (total_prob - 1) * 100
            }
        return None

    def _american_to_decimal(self, odds):
        if odds is None:
            return None
        if odds > 0:
            return 1 + (odds / 100)
        else:
            return 1 - (100 / odds)

class Dashboard:
    def __init__(self):
        self.app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
        self.scraper = SportsbookScraper()
        self.detector = ArbitrageDetector()
        self.setup_layout()
        self.setup_callbacks()

    def setup_layout(self):
        self.app.layout = dbc.Container([
            dbc.Row(dbc.Col(html.H1("Sports Arbitrage Dashboard", className="text-center my-4"))),
            dbc.Row([
                dbc.Col([
                    html.Div(id='arb-table', className="mb-4"),
                    dcc.Interval(id='refresh-interval', interval=60*1000, n_intervals=0)
                ], width=8),
                dbc.Col([
                    dcc.Graph(id='profit-gauge'),
                    dcc.Graph(id='opportunity-bar')
                ], width=4)
            ]),
            dbc.Row([
                dbc.Col(dcc.Graph(id='odds-comparison'), width=6),
                dbc.Col(dcc.Graph(id='roi-distribution'), width=6)
            ])
        ], fluid=True)

    def setup_callbacks(self):
        @self.app.callback(
            [Output('arb-table', 'children'),
             Output('profit-gauge', 'figure'),
             Output('opportunity-bar', 'figure'),
             Output('odds-comparison', 'figure'),
             Output('roi-distribution', 'figure')],
            [Input('refresh-interval', 'n_intervals')]
        )
        def update_dashboard(n):
            odds_data = self.scraper.scrape_odds()
            arbs_df = self.detector.find_arbs(odds_data)
            table = self._create_arb_table(arbs_df)
            profit_gauge = self._create_profit_gauge(arbs_df)
            opportunity_bar = self._create_opportunity_bar(arbs_df)
            odds_comparison = self._create_odds_comparison(arbs_df)
            roi_distribution = self._create_roi_distribution(arbs_df)
            return table, profit_gauge, opportunity_bar, odds_comparison, roi_distribution

        def _create_arb_table(self, arbs_df):
            if arbs_df.empty:
                return html.Div("No arbitrage opportunities found", className="alert alert-info")

            arbs_df = arbs_df.sort_values('roi', ascending=False)

            rows = [
                html.Tr([
                    html.Td(row['game']),
                    html.Td(row['market']),
                    html.Td(f"{row['book1']} ({row['odds1']})"),
                    html.Td(f"{row['book2']} ({row['odds2']})"),
                    html.Td(f"${row['total_stake']:.2f}"),
                    html.Td(f"${row['profit']:.2f}"),
                    html.Td(f"{row['roi']:.2f}%")
                ]) for _, row in arbs_df.head(10).iterrows()
            ]

            return dbc.Table(
                [
                    html.Thead(html.Tr([
                        html.Th("Game"),
                        html.Th("Market"),
                        html.Th("Bet 1"),
                        html.Th("Bet 2"),
                        html.Th("Stake"),
                        html.Th("Profit"),
                        html.Th("ROI")
                    ])),
                    html.Tbody(rows)
                ],
                striped=True,
                bordered=True,
                hover=True
            )


    def _create_profit_gauge(self, arbs_df):
        max_roi = arbs_df['roi'].max() if not arbs_df.empty else 0
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=max_roi,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': f"Best ROI: {max_roi:.2f}%"},
            gauge={
                'axis': {'range': [None, 20]},
                'bar': {'color': "darkblue"},
                'steps': [
                    {'range': [0, 5], 'color': "red"},
                    {'range': [5, 10], 'color': "orange"},
                    {'range': [10, 20], 'color': "green"}
                ],
                'threshold': {
                    'line': {'color': "black", 'width': 4},
                    'thickness': 0.75,
                    'value': max_roi
                }
            }
        ))
        fig.update_layout(title="Maximum ROI Opportunity", margin=dict(l=30, r=30, t=50, b=10))
        return fig

    def _create_opportunity_bar(self, arbs_df):
        if arbs_df.empty:
            return go.Figure()
        book_counts = arbs_df.groupby(['book1', 'book2']).size().reset_index(name='counts')
        book_counts['combination'] = book_counts['book1'] + " + " + book_counts['book2']
        fig = go.Figure(go.Bar(x=book_counts['combination'], y=book_counts['counts'], marker_color='royalblue'))
        fig.update_layout(title="Opportunities by Sportsbook Pair", xaxis_title="Sportsbooks", yaxis_title="Number of Arbs")
        return fig

    def _create_odds_comparison(self, arbs_df):
        if arbs_df.empty:
            return go.Figure()
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=arbs_df['odds1'], y=arbs_df['odds2'], mode='markers',
            marker=dict(size=arbs_df['roi']*2, color=arbs_df['roi'], colorscale='Viridis', showscale=True, colorbar=dict(title='ROI %')),
            text=arbs_df['game'] + "<br>" + arbs_df['market'], hoverinfo='text'
        ))
        fig.update_layout(title="Odds Comparison (Size = ROI)", xaxis_title="Book 1 Odds", yaxis_title="Book 2 Odds")
        return fig

    def _create_roi_distribution(self, arbs_df):
        if arbs_df.empty:
            return go.Figure()
        fig = go.Figure(go.Histogram(x=arbs_df['roi'], nbinsx=20, marker_color='green', opacity=0.75))
        fig.update_layout(title="ROI Distribution", xaxis_title="ROI %", yaxis_title="Count")
        return fig

    def run(self):
        self.app.run_server(debug=True)

if __name__ == "__main__":
    dashboard = Dashboard()
    dashboard.run()
