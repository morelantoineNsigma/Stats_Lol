from fetch_data import request_champions
import datetime as dt
import csv
import pandas as pd


def process_region(df_elo, region):
	lines = []

	data = request_champions(region, "Summer")

	for game in data:
		game = game['title']
		day = dt.datetime.strptime(game["DateTime UTC"], "%Y-%m-%d %H:%M:%S").date()
		patch = game['Patch']
		team1 = game['Team1']
		team2 = game['Team2']
		elo1 = df_elo.loc[(df_elo.team == team1) & (df_elo.day == day), ['elo']].values[0][0]
		elo2 = df_elo.loc[(df_elo.team == team2) & (df_elo.day == day]), ['elo']].values[0][0]


		# for champion in eeaz:
		# 	lines.append(dict(
		# 		day=day,
		# 		patch=patch,
		#
		# 	))

def get_elo_table():
	df_elo = pd.read_csv('elos.csv', header=0, delimiter=';')
	elo = dict()
	return df_elo[df_elo.split == 'Summer']


def all_region_to_csv():
	df_elo = get_elo_table()
	pass

if __name__ == '__main__':
	# all_region_to_csv()
	process_region('', 'LEC')