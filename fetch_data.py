import requests
import mwclient
import json


def request(table, fields, conditions):
	site = mwclient.Site('lol.gamepedia.com', path='/')
	str_cond = ""
	for cond in conditions:
		str_cond += "T." + cond["key"] + "='" + cond["value"] + "' AND "
	str_cond = str_cond[:-5]
	str_fields = ""
	for field in fields:
		str_fields += "T." + field + ", "
	str_fields = str_fields[:-2] + ""

	return site.api('cargoquery',
					limit='max',
					tables=table + "=T",
					fields=str_fields,
					where=str_cond
					)

#site.api('cargoquery', limit='max', tables="'" + table + "=T'", fields=str_fields, where=str_cond)

def request_result(region, split):
	table = "ScoreboardGames"
	tournament = region + ' 2020 ' + split
	conditions = [dict(key="Tournament", value=tournament)]
	fields = ['DateTime_UTC', 'Team1', 'Team2', 'WinTeam', 'N_GameInMatch', 'UniqueGame']
	return request(table, fields, conditions)["cargoquery"]


def request_team(region, split):
	tournament = region + ' 2020 ' + split
	conditions = [dict(key="Tournament", value=tournament)]
	fields = ['Tournament', 'Team']
	table = "TournamentRosters"
	return request(table, fields, conditions)["cargoquery"]


def request_champions(region, split):
	tournament = region + ' 2020 ' + split
	conditions = [dict(key="Tournament", value=tournament)]
	table = "ScoreboardGames"
	fields = ['Tournament', 'DateTime_UTC', 'Team1', 'Team2', 'WinTeam', 'Team1Bans', 'Team2Bans', 'Team1Picks',
			  'Team2Picks']

	return request(table, fields, conditions)["cargoquery"]


# def request_schedule(region, split='Summer'):
# 	# table = "MatchSchedule"
# 	table = "ScoreboardGames"
# 	# fields = ['Team1', 'Team2', 'ShownName', 'Winner']
# 	fields = ['Team1', 'Team2', 'Tournament', 'WinTeam']
# 	tournament = region + ' 2020 ' + split
# 	# conditions = [dict(key="ShownName", value=tournament)]
# 	conditions = [dict(key="Tournament", value=tournament)]
# 	return request(table, fields, conditions)["cargoquery"]

# , dict(key="Winner", value="")
if __name__ == '__main__':
	reponnse = (request_champions("LEC", "Summer"))

