import GetUrl
import sqlite3

db = db = sqlite3.connect("playerData.db")
file = open("ErrorMsgs//MonthLogErrors.txt", "w")

def CreateHitterMonthLogs(id):
    cursor = db.cursor()
    playerData = cursor.execute(f"SELECT DISTINCT year,league,level FROM PlayerYearHitter WHERE playerId={id}").fetchall()
    for data in playerData:
        year = data[0]
        league = data[1]
        level = data[2]
        
        cursor = db.cursor()
        months = cursor.execute(f"SELECT DISTINCT month FROM PlayerGameHitter WHERE playerId={id} AND year={year} AND league='{league}' AND level={level}").fetchall()
        for month in months:
            month = month[0]
            # Check if data Exists
            dataExists = cursor.execute(f"SELECT COUNT(*) FROM PlayerMonthHitter WHERE playerId={id} AND year={year} AND league='{league}' AND level={level} AND month={month}").fetchone()[0] > 0
            if dataExists:
                continue
            # Data does not exist
            gameData = cursor.execute(f"SELECT AB,R,H,[2B],[3B],HR,RBI,BB,IBB,SO,SB,CS,HBP,SAC,SF FROM PlayerGameHitter WHERE playerId={id} AND year={year} AND league='{league}' AND level={level} AND month={month}").fetchall()
            if len(gameData) == 0:
                file.write(f"No Game data found for id={id} year={year} month={month} league={league} level={level}\n")
                continue
            
            # Sum up all games for the month
            monthData = [0 for _ in range(len(gameData[0]))]
            for game in gameData:
                for n in range(len(game)):
                    monthData[n] += game[n]
                
            sqliteData = [id, month, year, league, level]
            for d in monthData:
                sqliteData.append(d)
            cursor.execute(f"INSERT INTO PlayerMonthHitter('playerId','month','year','league','level','AB','R','H','2B','3B','HR','RBI','BB','IBB','SO','SB','CS','HBP','SAC','SF') VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", sqliteData)
            db.commit()
        

def CreatePitcherMonthLogs(id):
    cursor = db.cursor()
    playerData = cursor.execute(f"SELECT DISTINCT year,league,level FROM PlayerYearPitcher WHERE playerId={id}").fetchall()
    for data in playerData:
        year = data[0]
        league = data[1]
        level = data[2]
        
        cursor = db.cursor()
        months = cursor.execute(f"SELECT DISTINCT month FROM PlayerGamePitcher WHERE playerId={id} AND year={year} AND league='{league}' AND level={level}").fetchall()
        for month in months:
            month = month[0]
            # Check if data Exists
            dataExists = cursor.execute(f"SELECT COUNT(*) FROM PlayerMonthPitcher WHERE playerId={id} AND year={year} AND league='{league}' AND level={level} AND month={month}").fetchone()[0] > 0
            if dataExists:
                continue
            # Data does not exist
            gameData = cursor.execute(f"SELECT W,L,GS,CG,SV,Outs,H,R,ER,HR,HB,BB,IBB,SO,GO,AO FROM PlayerGamePitcher WHERE playerId={id} AND year={year} AND league='{league}' AND level={level} AND month={month}").fetchall()
            if len(gameData) == 0:
                file.write(f"No Game data found for id={id} year={year} month={month} league={league} level={level}\n")
                continue
            
            # Sum up all games for the month
            monthData = [0 for _ in range(len(gameData[0]) + 1)] # +1 to keep track of games
            for game in gameData:
                for n in range(len(game)):
                    monthData[n] += game[n]
                monthData[-1] += 1
                
            sqliteData = [id, month, year, league, level]
            for d in monthData:
                sqliteData.append(d)
            cursor.execute(f"INSERT INTO PlayerMonthPitcher('playerId','month','year','league','level','W','L','GS','CG','SV','Outs','H','R','ER','HR','HB','BB','IBB','SO','GO','AO','G') VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", sqliteData)
            db.commit()

cursor = db.cursor()
playerData = cursor.execute("SELECT id,Position FROM Player").fetchall()

n = 0
for data in playerData:
    id = data[0]
    position = data[1]
    isHitter = True
    if position == "P" or position == "SP" or position == "RP" or position == "CP":
        isHitter = False
        
    if isHitter:
        CreateHitterMonthLogs(id)
    else:
        CreatePitcherMonthLogs(id)
        
    n += 1
    if (n % 100 == 0) or (n == len(playerData)):
        print(f"Completed {n} of {len(playerData)} Entries")
        
file.close()