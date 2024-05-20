from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

import GetUrl
import time

from unidecode import unidecode

__PositionDict = {
    "DH":0,
    "P":1,
    "C":2,
    "1B":3,
    "2B":4,
    "3B":5,
    "SS":6,
    "LF":7,
    "CF":8,
    "RF":9
}

def __ReadPlayerFielding(driver, db, file, id, mlbId, isFirst):
    url = "https://milb.com/player/" + str(mlbId)
    GetUrl.GetUrl(driver, url)
    if isFirst:
        try:
            WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))
                )
        except GetUrl.Timeout:
            raise GetUrl.Timeout
        except: # No elements on this page
            file.write(f"Failed to click cookies button for {id}\n")
            return
        
        exitButton = driver.find_element(By.ID, "onetrust-accept-btn-handler")
        
        exitButton.click()
    try:
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "/html/body/main/section/section/section[2]/div[1]/section/div[3]/div[1]/ul/li[2]/div/div[2]/a/button"))
        )
    except:
        file.write(f"Timed out waiting for clickable button for {id}\n")
        return
    
    
    allButton = driver.find_element(By.XPATH, "/html/body/main/section/section/section[2]/div[1]/section/div[3]/div[1]/ul/li[1]/div/div[1]/a/button")
    fieldButton = driver.find_element(By.XPATH, "/html/body/main/section/section/section[2]/div[1]/section/div[3]/div[1]/ul/li[2]/div/div/a/button[@data-type='fielding']")
    driver.execute_script("arguments[0].scrollIntoView(true);", allButton)
    allButton.send_keys('\n')
    driver.execute_script("arguments[0].scrollIntoView(true);", fieldButton)
    fieldButton.send_keys('\n')
    
    time.sleep(2)
    
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "careerTable"))
        )
    except:
        file.write(f"Timed out waiting for clickable button for {id}\n")
        return
    
    careerTable = driver.find_element(By.ID, "careerTable")
    tableBody = careerTable.find_element(By.TAG_NAME, "tbody")
    
    rows = []
    while len(rows) == 0:
        rows = tableBody.find_elements(By.TAG_NAME, "tr")
    
    data = []
    
    def GetData(vals, index):
        return vals[index].get_attribute("textContent").strip()
    for row in rows:
        values = row.find_elements(By.TAG_NAME, "td")
        year = int(GetData(values, 0).split(".")[0])
        team = GetData(values, 1)
        if "teams" in team: #Is a combination of multiple levels, so ignore
                            # It is the proper sum if all minor leagues, but wrong if majors + minors
            continue
        
        position = GetData(values, 4)
        games = int(GetData(values, 5))
        innings = GetData(values, 7)
        chances = int(GetData(values, 8))
        errors = int(GetData(values, 11))
        
        full, partial = innings.split(".")
        outs = 3 * int(full) + int(partial)
            
        try:
            positionIndex = __PositionDict[position]
        except:
            file.write(f"Unable to get Position Index for {id}: {position}\n")
            return
        
        thisData = [id, year, positionIndex, games, outs, chances, errors]
        
        # Check if this year/position already exists.  If it does, add to it
        alreadyExists = False
        for d in data:
            if d[1] == year and d[2] == positionIndex:
                d[3] += games
                d[4] += outs
                d[5] += chances
                d[6] += errors
                alreadyExists = True
                break
        
        if not alreadyExists:
            data.append(thisData)
            
    cursor = db.cursor()
    cursor.executemany("INSERT INTO PlayerYearFielding('playerId','year','position','games','outs','tc','error') VALUES(?,?,?,?,?,?,?)", 
                        data
                        )    
    db.commit()
    
    return

def ReadPlayerFielding(driver, db, file, id, mlbId, isFirst):
    
    cursor = db.cursor()
    dataFound = cursor.execute(f"SELECT COUNT(*) FROM PlayerYearFielding WHERE playerId={id}").fetchone()[0] > 0
    if dataFound:
        return
        
    __ReadPlayerFielding(driver, db, file, id, mlbId, isFirst)
    