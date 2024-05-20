import levels
import GetUrl

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

import time
import sqlite3
import threading
import PlayerGameLog
import PlayerNameCleanup
import traceback
import YearlyFielding

from unidecode import unidecode
def LogPlayer(driver, db, file, name, playerId, isHitter):
    name = str.replace(name, " ", "-").lower()
    name = str.replace(name, "'", "-")
    name = str.replace(name, ".", "-")
    name = str.replace(name, "--", "-")
    name = unidecode(name)
    
    cursor = db.cursor()
    thisPlayerId = cursor.execute("SELECT id FROM Player WHERE mlbId=" + str(playerId)).fetchone()
    
    if (isHitter):
        if (thisPlayerId is not None and len(thisPlayerId) == 1):
            cursor = db.cursor()
            if cursor.execute("SELECT COUNT(*) FROM PlayerYearHitter WHERE playerId=" + str(thisPlayerId[0])).fetchone()[0] > 0:
                return
        
    else:
        if (thisPlayerId is not None and len(thisPlayerId) == 1):
            cursor = db.cursor()
            if cursor.execute("SELECT COUNT(*) FROM PlayerYearPitcher WHERE playerId=" + str(thisPlayerId[0])).fetchone()[0] > 0:
                return
    
    # Check if entry for player exists
    cursor = db.cursor()
    count = cursor.execute("SELECT COUNT(*) FROM Player WHERE mlbId=" + str(playerId)).fetchone()[0]

    if count == 0:
        GetUrl.GetUrl(driver, "https://milb.com/player/" + str(playerId))
        
        try:
            playerVitals = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "player-header--vitals"))
            )
        except:
            file.write(f"Failed to find {name}\n")
            #LogPlayer(driver, db, name, playerId, isHitter)
            return
        
        name = playerVitals.find_element(By.TAG_NAME, "h1").get_attribute("textContent").strip()
        name = name.split("#")[0].strip()
        name = str.replace(name, "Jr.", "Jr")
        name = str.replace(name, "Sr.", "Sr")
        d = playerVitals.find_element(By.TAG_NAME, "ul")
        items = d.find_elements(By.TAG_NAME, "li")
        position = items[0].get_attribute("textContent").strip()
        batsThrows = items[1].get_attribute("textContent").strip()
        bats = batsThrows.split(': ')[1][0]
        throws = batsThrows.split('/')[2][0]
        height = items[2].get_attribute("textContent").strip()
        
        try:
            ft = height.split("'")[0]
            inches = height.split("'")[1].split('"')[0].strip()
        except:
            file.write(f"No Height found for {name}\n")
            return
        heightInches = int(ft) * 12 + int(inches)

        playerBioDiv = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "player-bio"))
        )
        ul = playerBioDiv.find_element(By.TAG_NAME, "ul")
        lis = ul.find_elements(By.TAG_NAME, "li")

        draftPick = -1

        for li in lis:
            text = li.get_attribute("textContent").strip()
            if "Born" in text:
                try:
                    date = int(text.split('/')[1]) 
                    month = int(text.split(' ')[1].split('/')[0])
                    year = int(text.split('/')[2].split(' ')[0])
                except: # Player does not have birth date listed, so do not include
                    file.write(f"Error reading birthdate for {name}\n")
                    return
                
            elif "Draft" in text:
                draftPick = int(text.split('Pick: ')[1])


        cursor = db.cursor()
        cursor.executemany("INSERT INTO Player('name','mlbId','birthYear','birthMonth','birthDate','draftPick','Position','Bats','Throws','Height') VALUES(?,?,?,?,?,?,?,?,?,?)", 
                        [(name, playerId, year, month, date, draftPick, position, bats, throws, heightInches)]
                        )
        db.commit()


    cursor = db.cursor()
    position = cursor.execute("SELECT position FROM Player WHERE mlbId=" + str(playerId)).fetchone()[0]
    # Update isHitter to match if they are a hitter or a pitcher, not whether they had hitting or pitching stats
    isHitter = not "P" in position
    
    # Get playerID in this database
    cursor = db.cursor()
    thisPlayerId = cursor.execute("SELECT id FROM Player WHERE mlbId=" + str(playerId)).fetchone()[0]

    # Check if entry for player exists
    if isHitter:
        cursor = db.cursor()
        count = cursor.execute("SELECT COUNT(*) FROM PlayerYearHitter WHERE playerId=" + str(thisPlayerId)).fetchone()[0]
    else:
        cursor = db.cursor()
        count = cursor.execute("SELECT COUNT(*) FROM PlayerYearPitcher WHERE playerId=" + str(thisPlayerId)).fetchone()[0]
    
    if count == 0:
        cursor = db.cursor()
        playerName = cursor.execute("SELECT name FROM Player WHERE id=" + str(thisPlayerId)).fetchone()[0]
        playerName = PlayerNameCleanup.PlayerNameCleanup(playerName)
        
        if isHitter:
            GetUrl.GetUrl(driver, "https://milb.com/player/" + playerName + "-" + str(playerId) + "?stats=career-r-hitting-all")
        if not isHitter:
            GetUrl.GetUrl(driver, "https://milb.com/player/" + playerName + "-" + str(playerId) + "?stats=career-r-pitching-all")
            
        try :
            tableDiv = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "careerTable"))
                )
        except:
            file.write(f"Failed to find career table for {name}\n")
            #LogPlayer(driver, db, name, playerId, isHitter)
            return
        
        try:
            tableBody = tableDiv.find_element(By.TAG_NAME, 'tbody')
        except:
            file.write(f"Failed to find body for {name}\n")
            return
        rows = tableBody.find_elements(By.TAG_NAME, "tr")
        
        try:
            advTableDiv = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "careerAdvancedTable"))
            )
        except:
            #LogPlayer(driver, db, name, playerId, isHitter)
            file.write(f"Failed to find career advanced table for {name}\n")
            return
        advTableBody = advTableDiv.find_element(By.TAG_NAME, "tbody")
        advRows = advTableBody.find_elements(By.TAG_NAME, "tr")
        
        data = []
        for i in range(len(rows)):
            row = rows[i]
            columns = row.find_elements(By.TAG_NAME, "td")
            if (columns[2].get_attribute("textContent").strip() == "-"):
                continue
            if isHitter:
                idxs = [0, 2, 3, 4, 5, 6, 7, 9, 10, 11, 12, 13, 14, 15, 16, 17, 22]
                advIdxs = [6, 7, 8]
            else:
                idxs = [0,2,3,4,5,7,8,9,12,14,15,16,17,18,20,21,22,23,26]
                advIdxs = []
            thisData = [thisPlayerId]
            
            try:
                for idx in idxs:
                    thisData.append(columns[idx].get_attribute("textContent").strip())
            except: # For some reason milb.com sometimes just returns the wrong page
                # Typically this is for a batter pitching, or a pitcher hitting
                # For now, just ignore
                file.write(f"Idx out of range for {name} at idx {idx}\n")
                return
            
            try:
                if thisData[2] == "DSL" or thisData[2] == "VSL":
                    thisData[3] = levels.levelDict["DSL"]
                else:
                    thisData[3] = levels.levelDict[thisData[3]]
            except:
                file.write(f"Level not in Dictionary for {name} : {thisData[3]}\n")
                return
            
            if not isHitter:
                ip = thisData[10]
                innings, partial = ip.split(".")
                thisData[10] = 3 * int(innings) + int(partial)
            
            if len(advIdxs) > 0:
                try:
                    columns = advRows[i].find_elements(By.TAG_NAME, "td")
                    for idx in advIdxs:
                        thisData.append(columns[idx].get_attribute("textContent").strip())
                except:
                    file.write(f"Error with advanced rows for {name}\n")
                    return
            
            thisData.append(columns[1].get_attribute("textContent").strip())
            
            data.append(thisData)
        
        cursor = db.cursor()
        if isHitter:
            cursor.executemany("INSERT INTO PlayerYearHitter('playerId','year','league','level','G','AB','R','H','2B','3B','HR','RBI','BB','IBB','SO','SB','CS','GOAO','HBP','SAC','SF','team') VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", 
                        data
                        )
        else:
            cursor.executemany("INSERT INTO PlayerYearPitcher('playerId','year','league','level','W','L','G','GS','CG','SV','Outs','H','R','ER','HR','HB','BB','IBB','SO','GOAO','team') VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", 
                        data
                        )
        db.commit()
            

def GetPlayers(file, driver, league, year, isHitter):
    page = "https://milb.com/stats"
    if not isHitter:
        page += "/pitching"
    
    page += "/" + league
    page += "/" + str(year)
    
    #driver.get(page)
    GetUrl.GetUrl(driver, page)
    #print(page)
    
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )
    
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "/html/body/main/div[2]/section/section/div[3]/div[2]/div/div/div[1]"))
            )
    except: # No elements on this page
        return
    navigationButtons = driver.find_element(By.XPATH, "/html/body/main/div[2]/section/section/div[3]/div[2]/div/div/div[1]")
    buttons = navigationButtons.find_elements(By.TAG_NAME, "div")
    numPages = int(buttons[-1].get_attribute("textContent").strip())
    
    hitterPitcherSymbol = "H,"
    if not isHitter:
        hitterPitcherSymbol = "P,"
    
    for currentPage in range(1, numPages + 1):
        if currentPage != 1:
            GetUrl.GetUrl(driver, page + "?page=" + str(currentPage))
            #driver.get(page + "?page=" + str(currentPage))
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
        
        links = []
        while len(links) == 0:
            links = driver.find_elements(By.XPATH, "/html/body/main/div[2]/section/section/div[3]/div[1]/div/table/tbody/tr/th/div[1]/div[2]/div/div[1]/a")
            
        for link in links:
            mlbId = int(link.get_attribute("href").split("/")[4])
            spans = link.find_elements(By.TAG_NAME, "span")
            name = spans[0].get_attribute("textContent").strip() + " " + spans[2].get_attribute("textContent").strip()
            name = str.replace(name, ".", " ")
            name = str.replace(name, "-", " ")
            name = str.replace(name, "  ", " ")
            file.write(hitterPitcherSymbol + name + ":" + str(mlbId)+"\n")
        
                
def ReadNameFile(drivers, file):
    playerData = []
    for line in file:
        data = (line.split(",")[1], int(line.split(",")[2]), line.split(",")[0] == "H")
        playerData.append(data)
    
    sortedData = sorted(playerData, key=lambda x: x[1])
    numDrivers = len(drivers)
    playerFileLength = len(sortedData)
    
    def LogPartOfList(driver, data, stIdx, endIdx, threadIdx):
        db = sqlite3.connect("playerData.db")
        db.execute("PRAGMA journal_mode = WAL")
        db.commit()
        
        numEntries = endIdx - stIdx
        n = 0
        
        file = open(f"Errors{threadIdx}.txt", "w")
        done = False
        
        def PrintNumCompleted():
            print(f"Thread {threadIdx} has completed {n}/{numEntries} Entries")
            if not done:
                threading.Timer(60, PrintNumCompleted).start()  
        
        PrintNumCompleted()
        
        def TimeoutHandler():
            print(f"Timed Out on thread {threadIdx}")
            raise GetUrl.Timeout()
        
        for i in range(stIdx, endIdx):
            timer = threading.Timer(60, TimeoutHandler)
            timer.start()
            try:
                LogPlayer(driver, db, file, data[i][0], data[i][1], data[i][2])
                timer.cancel()
            except KeyboardInterrupt:
                timer.cancel()
                print("Hello")
                raise KeyboardInterrupt
            except GetUrl.Timeout:
                file.write(f"Timed Out for {data[i][0]}")
                print(f"Timed Out on thread {threadIdx}")
                timer.cancel()
            except:
                file.write(f"Uncaught Exception for {data[i][0]}")
                print(f"Uncaught Exception {threadIdx}")
                timer.cancel()
            n += 1

        file.close()
        print(f"Thread {threadIdx} has completed")
        done = True
    
    threads = []
    
    for d in range(len(drivers)):
        startIdx = d * playerFileLength // numDrivers
        endIdx = (d + 1) * playerFileLength // numDrivers
        thread = threading.Thread(target=LogPartOfList, args=[drivers[d], sortedData, startIdx, endIdx, d])
        threads.append(thread)
        thread.start()
    
    
    for thread in threads:
        thread.join()
    # n = 0
    # for player in playerData:
    #     LogPlayer(driver, db, player[0], player[1], player[2])
    #     n += 1
    #     print("Completed " + str(n) + " / " + str(playerFileLength))

def GenerateGameLogs(drivers):
    db = sqlite3.connect("playerData.db")
    db.execute("PRAGMA journal_mode = WAL")
    db.commit()
    
    def ThreadFunction(driver, threadIdx, getNextIdFunction):
        db = sqlite3.connect("playerData.db")
        db.execute("PRAGMA journal_mode = WAL")
        db.commit()
        
        thisDone = 0
        totalDone = 0
        
        file = open(f"ErrorsGameLog{threadIdx}.txt", "w")
        done = False
        
        def PrintNumCompleted():
            nonlocal thisDone
            print(f"Thread {threadIdx} has completed {thisDone} Entries this cycle, {totalDone} in total")
            thisDone = 0
            if not done:
                threading.Timer(60, PrintNumCompleted).start()  
        
        PrintNumCompleted()
        
        def TimeoutHandler():
            print(f"Timed Out on thread {threadIdx}")
            raise GetUrl.Timeout()
        
        while True:
            timer = threading.Timer(300, TimeoutHandler)
            timer.start()
            try:
                id, mlbId, position, name = getNextIdFunction()
                if id == -1:
                    timer.cancel()
                    break
                if PlayerGameLog.ReadGameLogs(driver, db, file, id, mlbId, position, name) == True:
                    thisDone += 1
                    totalDone += 1
                timer.cancel()
            except KeyboardInterrupt:
                timer.cancel()
                print("User Interrupt")
                raise KeyboardInterrupt
            except GetUrl.Timeout:
                file.write(f"Timed Out for id {id}")
                print(f"Timed Out on thread {threadIdx}")
                timer.cancel()
            except Exception as e:
                file.write(f"Uncaught Exception for id {id} : {e}")
                print(f"Uncaught Exception {threadIdx}")
                traceback.print_exc()
                timer.cancel()

        print(f"Thread {threadIdx} has completed")
        file.close()
        done = True
    
    threads = []
    
    lock = threading.Lock()
    cursor = db.cursor()
    ids = cursor.execute("SELECT id,mlbId,Position,name FROM Player").fetchall()
    def GetNextPlayerData():
        with lock:
            if len(ids) > 0:
                return ids.pop(0)
            else:
                return -1, None, None, None
    
    def LeftTimer():
        print(f"Number of Players Left: {len(ids)}")
        if len(ids) != 0:
            threading.Timer(60, LeftTimer).start()
            
    offsetTime = 0.25 # Makes messages appear in order
    LeftTimer()
    time.sleep(offsetTime)
    
    for d in range(len(drivers)):
        thread = threading.Thread(target=ThreadFunction, args=[drivers[d], d, GetNextPlayerData])
        threads.append(thread)
        thread.start()
        time.sleep(offsetTime)
    
    
    for thread in threads:
        thread.join()
        
def GenerateFielding(drivers):
    db = sqlite3.connect("playerData.db")
    db.execute("PRAGMA journal_mode = WAL")
    db.commit()
    
    def ThreadFunction(driver, threadIdx, getNextIdFunction):
        db = sqlite3.connect("playerData.db")
        db.execute("PRAGMA journal_mode = WAL")
        db.commit()
        
        thisDone = 0
        totalDone = 0
        
        file = open(f"FieldingLog{threadIdx}.txt", "w")
        done = False
        isFirst = True
        
        def PrintNumCompleted():
            nonlocal thisDone
            print(f"Thread {threadIdx} has completed {thisDone} Entries this cycle, {totalDone} in total")
            thisDone = 0
            if not done:
                threading.Timer(60, PrintNumCompleted).start()  
        
        PrintNumCompleted()
        
        def TimeoutHandler():
            print(f"Timed Out on thread {threadIdx}")
            raise GetUrl.Timeout()
        
        while True:
            timer = threading.Timer(60, TimeoutHandler)
            timer.start()
            try:
                id, mlbId = getNextIdFunction()
                if id == -1:
                    timer.cancel()
                    break
                YearlyFielding.ReadPlayerFielding(driver, db, file, id, mlbId, isFirst)
                isFirst = False
                thisDone += 1
                totalDone += 1
                timer.cancel()
            except KeyboardInterrupt:
                timer.cancel()
                print("User Interrupt")
                raise KeyboardInterrupt
            except GetUrl.Timeout:
                file.write(f"Timed Out for id {id}\n")
                print(f"Timed Out on thread {threadIdx}")
                timer.cancel()
            except Exception as e:
                file.write(f"Uncaught Exception for id {id} : {e}\n")
                print(f"Uncaught Exception {threadIdx}")
                traceback.print_exc()
                timer.cancel()

        print(f"Thread {threadIdx} has completed")
        file.close()
        done = True
    
    threads = []
    
    lock = threading.Lock()
    cursor = db.cursor()
    ids = cursor.execute("SELECT id,mlbId FROM Player WHERE Position!='P'").fetchall()
    def GetNextPlayerData():
        with lock:
            if len(ids) > 0:
                return ids.pop(0)
            else:
                return -1, None
    
    def LeftTimer():
        print(f"Number of Players Left: {len(ids)}")
        if len(ids) != 0:
            threading.Timer(60, LeftTimer).start()
            
    offsetTime = 0.25 # Makes messages appear in order
    LeftTimer()
    time.sleep(offsetTime)
    
    for d in range(len(drivers)):
        thread = threading.Thread(target=ThreadFunction, args=[drivers[d], d, GetNextPlayerData])
        threads.append(thread)
        thread.start()
        time.sleep(offsetTime)
    
    
    for thread in threads:
        thread.join()

options = webdriver.ChromeOptions() 
options.add_argument("--log-level=3")
#options.add_argument('--headless=new')
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-renderer-backgrounding")
options.add_argument("--disable-background-timer-throttling")
options.add_argument("--disable-backgrounding-occluded-windows")
options.add_argument("--disable-client-side-phishing-detection")
options.add_argument("--disable-crash-reporter")
options.add_argument("--disable-oopr-debug-crash-dump")
options.add_argument("--no-crash-upload")
options.add_argument("--disable-gpu")
options.add_argument("--disable-extensions")
options.add_argument("--disable-low-res-tiling")
options.add_argument("--silent")

drivers = []
for i in range(1):
    drivers.append(webdriver.Chrome(options=options))

# leagues = ["international",
#            "pacific-coast",
#            "eastern",
#            "southern",
#            "texas",
#            "carolina-league",
#            "florida-state",
#            "california",
#            "south-atlantic",
#            "midwest",
#            "northwest",
#            "new-york-penn",
#            "arizona-complex",
#            "florida-complex",
#            "dominican-summer",
#            "venezuelan-summer",
#            "pioneer",
#            "appalachian"
#            ]

# years = range(2005, 2025)
# file = open("names.txt", "w", encoding="utf-8")

# for league in leagues:
#     for year in years:
#         hitters = GetPlayers(file, driver, league, year, True)
#         pitchers = GetPlayers(file, driver, league, year, False)

#LogPlayer(driver, db, "Boof Bonser", 425818, False)
# LogPlayer(driver, db, "Luis Arraez", 650333, True)
# ReadGameLogs(driver, db, 1)
# ReadGameLogs(driver, db, 4)

# file = open("names.txt", "r", encoding="utf-8")
# ReadNameFile(drivers, file)

#GenerateFielding(drivers)

db = sqlite3.connect("playerData.db")
file = open("testFile.txt", "w")
YearlyFielding.ReadPlayerFielding(drivers[0], db, file, 15455, 467090, True)
YearlyFielding.ReadPlayerFielding(drivers[0], db, file, 16492, 673661, False)
YearlyFielding.ReadPlayerFielding(drivers[0], db, file, 17442, 440162, False)
YearlyFielding.ReadPlayerFielding(drivers[0], db, file, 39130, 680646, False)

for driver in drivers:
    driver.quit()
file.close()