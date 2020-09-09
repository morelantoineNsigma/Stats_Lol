import re
import pandas as pd
import time
import pickle
import os
import json
from fetch_data import request_result


raw_matchs = """
LEC 2020 Summer - MAD vs S04,2020-08-09,18:00
LEC 2020 Summer - RGE vs OG,2020-08-09,19:00
LEC 2020 Summer - FNC vs SK,2020-08-09,20:00
LEC 2020 Summer - G2 vs XL,2020-08-09,21:00"""


actual_standings = dict(
	MSF=7,
	SK=9,
	S04=7,
	XL=8,
	OG=6,
	VIT=7,
	G2=10,
	FNC=8,
	RGE=12,
	MAD=12,
)

def convert_name(team):
	return {
		"G2 Esports": "G2",
		"MAD Lions": "MAD",
		"Team Vitality": "VIT",
		"FC Schalke 04 Esports": "S04",
		"SK Gaming": "SK",
		"Origen": "OG",
		"Rogue (European Team)": "RGE",
		"Excel Esports": "XL",
		"Misfits Gaming": "MSF",
		"Fnatic": "FNC"
	}.get(team)

def historic():
	response = request_result('LEC', 'Summer')
	str, matchs = "", []
	for elt in response:
		matchs.append((convert_name(elt['title']['Team1']), convert_name(elt['title']['Team2'])))
		str += "0" if elt['title']['Team1'] == elt['title']['WinTeam'] else "1"
	with open('matches', 'wb') as f:
		pickle.dump(matchs, f)
	with open('results', 'wb') as f:
		pickle.dump(str, f)


def parse_matches():
	pattern = r"(?P<team1>\w[\w|\d]*) vs (?P<team2>\w[\w|\d]*)"
	games = re.findall(pattern, raw_matchs)
	return [list(game) for game in games]


def head_to_head(teams, results, matchs, actual_rank):
	team1, team2 = teams[0], teams[1]
	# H2H
	hdh = 0
	for m in range(90):
		if team1 in matchs[m] and team2 in matchs[m]:
			hdh += 1 if matchs[m][int(results[m])] == team1 else -1
	if hdh != 0:
		if hdh == 2:
			return {team1:actual_rank, team2:actual_rank+1}
		else:
			return {team1:actual_rank+1, team2:actual_rank}
	# RETOUR
	t1, t2 = 0, 0
	for m in range(45, 90):
		if team1 in matchs[m]:
			t1 += 1 if matchs[m][int(results[m])] == team1 else 0
		if team2 in matchs[m]:
			t2 += 1 if matchs[m][int(results[m])] == team2 else 0
	if t1 > t2:
		return {team1: actual_rank, team2: actual_rank + 1}
	elif t1 < t2:
		return {team1: actual_rank + 1, team2: actual_rank}


	return {team1:actual_rank, team2:actual_rank}


def best_return(teams, results, matchs, actual_rank):
	return_wins = {k:0 for k in teams}
	for m in range(45, 90):
		if matchs[m][0] in teams or matchs[m][1] in teams:
			winner = matchs[m][int(results[m])]
			if winner in return_wins:
				return_wins[winner] += 1
	# print(return_wins)
	rank_dict = {}
	temp_rank = actual_rank
	for nb_win in set(sorted(return_wins.values(), reverse=True)):
		c = 0
		for team, win in return_wins.items():
			if win == nb_win:
				rank_dict[team] = temp_rank
				c += 1
		temp_rank += c
	return rank_dict


def three_or_more_way(teams, results, matchs, actual_rank):
	hdh = {k:0 for k in teams}
	for m in range(90):
		if matchs[m][0] in teams and matchs[m][1] in teams:
			hdh[matchs[m][int(results[m])]] += 1
	# print(hdh)
	ahead, middle, behind = [], [], []
	for team in teams:
		if hdh[team] > len(teams) - 1:
			ahead.append(team)
		elif hdh[team] < len(teams) - 1:
			behind.append(team)
		else:
			middle.append(team)

	return_rank = {}
	temp_rank = actual_rank
	if len(ahead) == 1:
		return_rank.update({ahead[0]: temp_rank})
	elif len(ahead) > 1:
		return_rank.update(best_return(ahead, results, matchs, temp_rank))
	temp_rank += len(ahead)

	if len(middle) == 1:
		return_rank.update({middle[0]: temp_rank})
	elif len(middle) > 1:
		return_rank.update(best_return(middle, results, matchs, temp_rank))
	temp_rank += len(middle)
	if len(behind) == 1:
		return_rank.update({behind[0]: temp_rank})
	elif len(behind) > 1:
		return_rank.update(best_return(behind, results, matchs, temp_rank))

	return return_rank


class Scenario():
	def __init__(self, id, standings, matchs, results):
		self.id = id
		self.standings = standings.copy()
		self.matchs = matchs
		self.results = results

	def calc_standings(self, games):
		new_standings = self.standings
		for i in range(len(games)):
			new_standings[games[i][int(self.id[i])]] += 1
		return new_standings

	def pre_standings(self, games):
		final_standings = self.calc_standings(games)
		ordered_standings = sorted(final_standings.items(), key=lambda item: item[1], reverse=True)
		cla, ranks = 1, dict()
		ranks[ordered_standings[0][0]] = [ordered_standings[0][1], 1]
		for i in range(1, len(ordered_standings)):
			if ordered_standings[i-1][1] == ordered_standings[i][1]:
				ranks[ordered_standings[i][0]] = [ordered_standings[i][1], ranks[ordered_standings[i-1][0]][1]]
			else:
				ranks[ordered_standings[i][0]] = [ordered_standings[i][1], i+1]
		return ranks

	def exact_standings(self, games):
		ranks = self.pre_standings(games)
		new_ranks = ranks.copy()
		for rank in range(1, 10):
			teams = [team for team, tup in ranks.items() if tup[1] == rank]
			if len(teams) > 1:
				if len(teams) == 2:
					mod_rank = head_to_head(teams, self.results + self.id, self.matchs + games, rank)
				else:
					mod_rank = three_or_more_way(teams, self.results + self.id, self.matchs + games, rank)
				for team in teams:
					new_ranks[team][1] = mod_rank[team]
		return new_ranks

	def decoration(self, games):
		ranks = self.exact_standings(games)
		nb_qualif = 0
		for rank in range(1, 11):
			teams = [team for team, tup in ranks.items() if tup[1] == rank]
			if nb_qualif + len(teams) <= 6:
				for team in teams:
					ranks[team].append("Q")
			elif nb_qualif >= 6:
				for team in teams:
					ranks[team].append("E")
			else:
				for team in teams:
					ranks[team].append("T")
			nb_qualif += len(teams)
		return ranks



def generateAllBinaryStrings(n):
	ids = []

	def generateAllBinaryStrings_rec(n, id):
		if n > 0:
			generateAllBinaryStrings_rec(n-1, id + "0")
			generateAllBinaryStrings_rec(n-1, id + "1")
		else:
			ids.append(id)

	generateAllBinaryStrings_rec(n, "")
	with open('binaries', 'wb') as f:
		pickle.dump(ids, f)


def getBinaries():
	print("Reading Binary file")
	with open('binaries', 'rb') as f:
		binaries = pickle.load(f)
	return binaries


def exportCsv(lines):
	print("Exporting...")
	df = pd.DataFrame.from_dict(lines, orient='index')
	for col in df.keys():
		df[[col + '_Nb Win', col + '_Rank', col + '_Status']] = pd.DataFrame(df[col].tolist(), index=df.index)
		del df[col]
	df.to_csv('ScenariLEC.csv', sep=';', index=True)
	print("Export done to ", 'ScenariLEC.csv')


def test_scenario(id, standings, matchs, results):
	scenario = Scenario(id, standings, matchs, results)
	return scenario.decoration(parse_matches())


def test_all_scenari():
	with open('matches', 'rb') as f:
		matchs = pickle.load(f)
	with open('results', 'rb') as f:
		results = pickle.load(f)
	standings = actual_standings
	lines = dict()
	ids = getBinaries()
	print("Reading Done")
	for id in ids:
		lines[id] = test_scenario(id, standings, matchs, results)
	exportCsv(lines)

#
#
# def analyse_scenari():
#
# 	rank_summary = {k: {l: 0 for l in range(1, 11)} for k in actual_standings.keys()}
#
# 	filename = 'ScenariLEC_1000000.csv'
# 	while os.path.exists(filename):
# 		rank_summary = {k: 0 for k in actual_standings.keys()}
# 		df = pd.read_csv(filename, delimiter=';')
# 		for team in rank_summary.keys():
# 			stats = df[team + '_Rank'].value_counts()
# 			rank_summary[team] = stats.to_dict()
# 		with open('ScenariLEC_' + str(ind) + '.json', 'w') as fp:
# 			json.dump(rank_summary, fp, indent=4)
# 		ind += step
# 		filename = 'ScenariLEC_' + str(ind) + '.csv'
# 		print(ind)


def consolidate_json():
	regex = r"ScenariLEC_\d*.json"
	ranks = dict()
	for file in os.listdir("."):
		if re.match(regex, file):
			with open(file, 'r') as fp:
				sample = json.load(fp)
			cour = ranks.copy()
			if ranks == {}:
				cour = sample
			else:
				for team in ranks.keys():
					cour[team] = {k: sample[team].get(k, 0) + ranks[team].get(k, 0) for k in set(sample[team]) | set(ranks[team])}
			ranks = cour.copy()
	with open('ScenariLEC.json', 'w') as fp:
		json.dump(ranks, fp, indent=4)

if __name__ == '__main__':
	generateAllBinaryStrings(4)
	historic()
	# with open('matches', 'rb') as f:
	# 	matchs = pickle.load(f)
	# with open('results', 'rb') as f:
	# 	results = pickle.load(f)
	# print(test_scenario("110011110110000",actual_standings, matchs, results))
	test_all_scenari()
	# analyse_scenari()
	# c onsolidate_json()