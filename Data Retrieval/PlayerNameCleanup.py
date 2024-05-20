from unidecode import unidecode
def PlayerNameCleanup(playerName):
    playerName = playerName.lower()
    playerName = unidecode(playerName)
    playerName = playerName.replace(". ", "-")
    playerName = playerName.replace(".", "-")
    playerName = playerName.replace(" ", "-")
    playerName = playerName.replace("'", "-")
    playerName = playerName.replace("--", "-")
    while playerName.endswith("-"):
        playerName = playerName[:-1]
            
    return playerName