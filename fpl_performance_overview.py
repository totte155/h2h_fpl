import requests
import matplotlib.pyplot as plt
import pandas as pd


#GET GAMEWEEK DATA
def fpl_api_query(player_id):
    players = {
        'Totte': "4512595",
        'Pappa': "1989627",
        'Frej': "1987616",
        'Phil': "4279435",
        'Tommi': "3013919",
        'Pat': "3414317",
    }

    for player, id in players.items():
        url = f"https://fantasy.premierleague.com/api/entry/{id}/history/"
        #API request
        response = requests.get(url).json()
        relevant_API_data = response["current"]



#Can I get all graphs on one page

#GAMEWEEK POINT FUNCTION
def gameweek_points(gameweek_data):
  pass


main_method():
    pass
    #player_id = input("FPL player = ")
