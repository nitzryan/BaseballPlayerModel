from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

import GetUrl
import MonthYearToDict
import PlayerNameCleanup

from unidecode import unidecode

def __ReadPlayerGameLogs(driver, db, file, name, id, mlbId, year, leagueDict, levelDict, isHitter):
    name = PlayerNameCleanup.PlayerNameCleanup(name)
    
    if isHitter:
        url = "https://milb.com/player/" + name + "-" + str(mlbId) + "?stats=gamelogs-r-hitting-mlb&year=" + str(year)
    else:
        url = "https://milb.com/player/" + name + "-" + str(mlbId) + "?stats=gamelogs-r-pitching-mlb&year=" + str(year)
        
    #print(url)
    GetUrl.GetUrl(driver, url)
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "/html/body/main/section/section/section[2]/div[1]/section/div[3]/div[2]/div/div[1]/div/div/div[1]/div/table/tbody/tr"))
            )
    except GetUrl.Timeout:
        raise GetUrl.Timeout
    except: # No elements on this page
        file.write(f"Failed to find body for {name} : {year}\n")
        return
    
    logs = []
    while len(logs) == 0:
        logs = driver.find_elements(By.XPATH, "/html/body/main/section/section/section[2]/div[1]/section/div[3]/div[2]/div/div[1]/div/div/div[1]/div/table/tbody/tr")
    
    data = []
    for log in logs:
        if "total" in log.get_attribute("class") or "header-repeat" in log.get_attribute("class"):
            continue
        
        columns = log.find_elements(By.TAG_NAME, "td")
        date = columns[0].get_attribute("textContent").strip()
        month = MonthYearToDict.monthToYearDict[date.split(" ")[0]]
        day = date.split(" ")[1]
        team = columns[1].get_attribute("textContent").strip()
        
        if isHitter:
            idxs = [3,4,5,7,8,9,10,11,12,13,14,15,19,20,21]
        else:
            idxs = [3, 4, 7, 8, 10, 12, 13, 14, 15, 16, 17, 18, 19, 20, 24]
            
        thisData = [id, day, month, year, leagueDict[team], levelDict[team]]
        for idx in idxs:
            thisData.append(columns[idx].get_attribute("textContent").strip())
            
        if not isHitter:
            ip = thisData[11]
            innings, partial = ip.split(".")
            thisData[11] = 3 * int(innings) + int(partial)
            
            try:
                inPlayOuts = int(thisData[11]) - int(thisData[19])
                goaoRatio = float(thisData[20])
                goPerc = goaoRatio / (goaoRatio + 1)
                go = round(goPerc * inPlayOuts, 0)
                ao = inPlayOuts - go
                thisData[20] = str(go)
                thisData.append(str(ao))
            except GetUrl.Timeout:
                raise GetUrl.Timeout
            except: # No in-play outs recorded, so goaoRatio is not a number
                thisData[20] = "0"
                thisData.append("0")
            
        data.append(thisData)
        
    cursor = db.cursor()
    if isHitter:
        cursor.executemany("INSERT INTO PlayerGameHitter('playerId','day','month','year','league','level','AB','R','H','2B','3B','HR','RBI','BB','IBB','SO','SB','CS','HBP','SAC','SF') VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", 
                            data
                            )    
    else:
        cursor.executemany("INSERT INTO PlayerGamePitcher('playerId','day','month','year','league','level','W','L','GS','CG','SV','Outs','H','R','ER','HR','HB','BB','IBB','SO','GO','AO') VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", 
                            data
                            )    
    db.commit()
    
    return

def ReadGameLogs(driver, db, file, id, mlbId, position, name):
    
    isHitter = not "P" in position
    cursor = db.cursor()
    if isHitter:
        years = cursor.execute("SELECT DISTINCT(year) FROM PlayerYearHitter WHERE playerId=" + str(id)).fetchall()
    else:
        years = cursor.execute("SELECT DISTINCT(year) FROM PlayerYearPitcher WHERE playerId=" + str(id)).fetchall()
        
    anyUpdated = False
    for year in years:
        year = year[0]
        if (year < 2005):
            continue
        leagueDict = {}
        levelDict = {}
        cursor = db.cursor()
        if isHitter:
            results = cursor.execute("SELECT team,level,league FROM PlayerYearHitter WHERE playerId = " + str(id) + " AND year = " + str(year)).fetchall()
        else:
            results = cursor.execute("SELECT team,level,league FROM PlayerYearPitcher WHERE playerId = " + str(id) + " AND year = " + str(year)).fetchall()
        for result in results:
            leagueDict[result[0]] = result[2]
            levelDict[result[0]] = result[1]
        
        cursor = db.cursor()
        if isHitter:
            found = cursor.execute("SELECT COUNT(*) FROM PlayerGameHitter WHERE playerId=" + str(id) + " AND year=" + str(year)).fetchone()[0] > 0
            if not found:
                __ReadPlayerGameLogs(driver, db, file, name, id, mlbId, year, leagueDict, levelDict, True)
                anyUpdated = True
        else:
            found = cursor.execute("SELECT COUNT(*) FROM PlayerGamePitcher WHERE playerId=" + str(id) + " AND year=" + str(year)).fetchone()[0] > 0
            if not found:
                __ReadPlayerGameLogs(driver, db, file, name, id, mlbId, year, leagueDict, levelDict, False)
                anyUpdated = True
                
    return anyUpdated