from fetch_data import request_result, request_team
import datetime as dt
import csv
import pandas as pd


regions = dict(
	LPL=dict(
		base_elo=2700,
		format='bo3',
		K=dict(
			Spring=60,
			Summer=80
		)
	),
	LEC=dict(
		base_elo=2600,
		format='bo1',
		K=dict(
			Spring=60,
			Summer=80
		)
	),
	LCK=dict(
		base_elo=2600,
		format='bo3',
		K=dict(
			Spring=60,
			Summer=80
		)
	),
	LCS=dict(
		base_elo=2500,
		format='bo1',
		K=dict(
			Spring=60,
			Summer=80
		)
	),
)


def switch_process_func(format):
	return dict(
		bo1=process_bo1,
		bo3=process_bo3or5
	).get(format)


def rename(name):
	return {
		"DragonX" : "DRX",
		"Rogue (European Team)" : "Rogue",
		"FC Schalke 04 Esports" : "Schalke 04",
		"Evil Geniuses.NA" : "Evil Geniuses",
		"eStar (Chinese Team)" : "eStar",
		"SeolHaeOne Prince" : "APK Prince"
	}.get(name, name)


def p(d):
	return 1 / (1 + 10**(-d/400))


def update_elo(elo1, elo2, winner, K):
	next_elo1, next_elo2 = elo1, elo2
	next_elo1 += K * (winner - p(elo1 - elo2))
	next_elo2 += K * (1 - winner - p(elo2 - elo1))
	return round(next_elo1, 1), round(next_elo2,1)


def get_teams(region, split):
	response, teams = request_team(region, split), []
	for elt in response:
		teams.append(rename(elt['title']['Team']))
	return teams


def process_bo1(region, split, elo, K):
	results = request_result(region, split)
	lines = []
	for match in results:
		team1, team2 = rename(match["title"]["Team1"]), rename(match["title"]["Team2"])
		w = 1 if rename(match["title"]["WinTeam"]) == team1 else 0
		elo[team1], elo[team2] = update_elo(elo[team1], elo[team2], w, K)

		day = dt.datetime.strptime(match["title"]["DateTime UTC"], "%Y-%m-%d %H:%M:%S")

		lines.append(dict(
			day=day,
			region=region,
			split=split,
			team=team1,
			elo=elo[team1]
		))
		lines.append(dict(
			day=day,
			region=region,
			split=split,
			team=team2,
			elo=elo[team2]
		))

	return elo, lines


def process_bo3or5(region, split, elo, K):
	results = request_result(region, split)

	for match in results:
		match["title"]["UniqueGame"] = match["title"]["UniqueGame"][:-2]

	new_results = {}
	for match in results:
		if match["title"]["UniqueGame"] not in new_results:
			new_results[match["title"]["UniqueGame"]] = [match]
		else:
			new_results[match["title"]["UniqueGame"]].append(match)

	lines = []

	for bo in new_results.values():
		team1, team2 = rename(bo[0]["title"]["Team1"]), rename(bo[0]["title"]["Team2"])
		day = dt.datetime.strptime(bo[0]["title"]["DateTime UTC"], "%Y-%m-%d %H:%M:%S")

		score1, score2 = 0, 0
		for game in bo:
			score1 += 1 if rename(game["title"]["WinTeam"]) == team1 else 0
			score2 += 1 if rename(game["title"]["WinTeam"]) == team2 else 0

		K_mod = K
		if max(score1, score2) == 3:
			if min(score1, score2) == 0:
				K_mod = K * 5 / 4
			elif min(score1, score2) == 0:
				K_mod = K * 3 / 4
		elif max(score1, score2) == 2:
			if min(score1, score2) == 1:
				K_mod = K * 3 / 4
		else:
			K_mod = 0
			print("'BO non complet")

		elo[team1], elo[team2] = update_elo(elo[team1], elo[team2], 1 if score1 > score2 else 0, K_mod)

		lines.append(dict(
			day=day,
			region=region,
			split=split.split(' ')[0],
			team=team1,
			elo=elo[team1]
		))
		lines.append(dict(
			day=day,
			region=region,
			split=split.split(' ')[0],
			team=team2,
			elo=elo[team2]
		))

	return elo, lines


def process_region(region):

	# SPRING
	teams = get_teams(region, "Spring")
	elo = {team: regions[region]['base_elo'] for team in teams}
	elo, lines_spring = switch_process_func(regions[region]['format'])(region, 'Spring', elo, regions[region]['K']['Spring'])

	# PLAYOFFS
	teams = get_teams(region, "Summer")
	elo, lines_spring_playoffs = process_bo3or5(region, 'Spring Playoffs', elo, regions[region]['K']['Spring'])

	# SUMMER
	teams = get_teams(region, "Summer")
	elo = {team: regions[region]['base_elo'] if team not in elo else elo[team] for team in teams}
	elo, lines_summer = switch_process_func(regions[region]['format'])(region, 'Summer', elo, regions[region]['K']['Summer'])

	print(elo)

	return lines_spring + lines_spring_playoffs + lines_summer


def all_region_to_csv():
	MAX_TIME_DELTA = dt.timedelta(days=14)

	lines = process_region('LEC') + process_region('LCS') + process_region('LPL') + process_region('LCK')
	df = pd.DataFrame(lines)
	df.day = df.day.dt.date
	for split in df.split.unique():
		for team in df[(df.split == split)].team.unique():
			days = list(df[(df.team == team) & (df.split == split)].day.unique())
			for i in range(1, len(days)):
				for j in range(1, int((days[i] - days[i-1]) / dt.timedelta(days=1))):
					new_line = dict(
						day=days[i-1] + dt.timedelta(days=j),
						region=df.loc[(df.team == team) & (df.day == days[i-1]), ['region']].values[0][0],
						split=split,
						team=team,
						elo=df.loc[(df.team == team) & (df.day == days[i-1]), ['elo']].values[0][0]
					)
					df = df.append(new_line, ignore_index=True)
			if dt.date.today() - days[-1] < MAX_TIME_DELTA:
				for j in range(1, int((dt.date.today() - days[-1]) / dt.timedelta(days=1)) + 1):
					new_line = dict(
						day=days[-1] + dt.timedelta(days=j),
						region=df.loc[(df.team == team) & (df.day == days[-1]), ['region']].values[0][0],
						split=split,
						team=team,
						elo=df.loc[(df.team == team) & (df.day == days[-1]), ['elo']].values[0][0]
					)
					df = df.append(new_line, ignore_index=True)
	df.to_csv('elos.csv', sep=';', index=False)




if __name__ == '__main__':
	all_region_to_csv()