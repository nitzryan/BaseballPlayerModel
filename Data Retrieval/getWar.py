from pybaseball import batting_stats
from pybaseball import pitching_stats

import sqlite3

from unidecode import unidecode
import requests
from bs4 import BeautifulSoup

from PlayerNameCleanup import PlayerNameCleanup

db = sqlite3.connect("playerData.db")

def FirstIsEquivalent(a, b):
    def Compare(a, b, nameA, nameB):
        return ((a == nameA or a == nameB) and (b == nameA or b == nameB))
    
    return (Compare(a, b, 'mike', 'michael') or
        Compare(a, b, 'jake', 'jacob') or
        Compare(a, b, 'matthew', 'matt') or
        Compare(a, b, 'daniel', 'dan') or
        Compare(a, b, 'alexei', 'alex') or
        Compare(a, b, 'charlie', 'charles') or
        Compare(a, b, 'jon', 'john') or
        Compare(a, b, 'jon', 'jonathan') or
        Compare(a, b, 'sammy', 'sam') or
        Compare(a, b, 'sam', 'samuel') or
        Compare(a, b, 'sammy', 'samuel') or
        Compare(a, b, 'tyler', 'ty') or
        Compare(a, b, 'dave', 'david') or
        Compare(a, b, 'wil', 'will') or
        Compare(a, b, 'thad', 'thaddeus') or
        Compare(a, b, 'thad', 'thaddius') or
        Compare(a, b, 'josh', 'joshua') or
        Compare(a, b, 'jon', 'jonathon') or
        Compare(a, b, 'jim', 'james') or
        Compare(a, b, 'nate', 'nathan') or
        Compare(a, b, 'cam', 'cameron') or
        Compare(a, b, 'jackson', 'clint') or
        Compare(a, b, 'joseph', 'joe') or
        Compare(a, b, 'andy', 'andrew') or
        Compare(a, b, 'nick', 'nicklaus') or
        Compare(a, b, 'cal', 'calvin') or
        Compare(a, b, 'andrew', 'drew') or
        Compare(a, b, 'russ', 'russell') or
        Compare(a, b, 'kenneth', 'kenny') or
        Compare(a, b, 'christopher', 'chris') or
        Compare(a, b, 'daniel', 'dan') or
        Compare(a, b, 'mitchell', 'mitch') or
        Compare(a, b, 'steve', 'steven') or
        Compare(a, b, 'patrick', 'pat') or
        Compare(a, b, 'edward', 'ed') or
        Compare(a, b, 'daniel', 'danny') or
        Compare(a, b, 'dan', 'danny') or
        Compare(a, b, 'kenneth', 'ken')
        )

def checkSameName(name, target):
    name = unidecode(name)
    name = name.lower()
    if "." in name and "." not in target:
        name = name.replace(".", "")
        return checkSameName(name, target)
    if "." not in name and "." in target:
        target = target.replace(".", "")
        return checkSameName(name, target)
    
    if "-" in name and "-" not in target:
        name = name.replace("-", " ")
        return checkSameName(name, target)
    if "-" not in name and "-" in target:
        target = target.replace("-", " ")
        return checkSameName(name, target)
    
    if name == target:
        return True
    
    names = name.split(" ")
    targetNames = target.split(" ")
    if len(names) == 1 or len(targetNames) == 1:
        return False
    
    for n in range(1, len(names)):
        firstEqual = targetNames[0] == names[0]
        secondEqual = targetNames[1] == names[n]
        if secondEqual:
            if firstEqual or FirstIsEquivalent(targetNames[0], names[0]):
                return True
        
    return False

db.create_function("CHECKSAMENAME", 2, checkSameName)

def UpdateNames(data):
    for d in data:
        fangraphsId = d[0]
        name = unidecode(d[1])
        name = name.lower()
        cursor = db.cursor()
        sameFId = cursor.execute(f"SELECT id FROM Player WHERE fangraphsId={fangraphsId}").fetchone()
        if sameFId == None: # Id not found in database
            sameName = cursor.execute(f'SELECT id,mlbId,fangraphsId,birthYear,birthMonth,birthDate FROM Player WHERE CHECKSAMENAME(name,"{name}") AND fangraphsId IS NULL').fetchall()
            if len(sameName) == 0:
                print(f"No matches found for {name} : FangraphsId = {fangraphsId}")
                pass
            else:
                fName = PlayerNameCleanup(name)
                try:
                    response = requests.get(f"https://fangraphs.com/players/{fName}/{fangraphsId}")
                    soup = BeautifulSoup(response.text, "html.parser")

                    el = soup.find("tr", {"class":"player-info__bio-birthdate"})
                    birthdayText = el.td.text.split(" ")[0]
                    month, day, year = birthdayText.split("/")
                    month = int(month)
                    day = int(day)
                    year = int(year)
                    for option in sameName:
                        if ((month == option[4] and day == option[5]) or (month == option[5] and day == option[4]) or (month == option[4] and (day == option[5] - 1) or (day == option[5] + 1))) and year == option[3]:
                            cursor.execute(f"UPDATE Player SET fangraphsId={fangraphsId} WHERE id={option[0]}")
                            db.commit()
                            cursor = db.cursor()
                            print(f"Added {name} through URL")
                            break
                    else:
                        print(f"Failed to find matching birthday for {name} : {fangraphsId}")
                except:
                    print(f"Exception for {name}")
                    pass
                    
        else:
            pass
            #print(f"Already in Databse: {name}")


# for year in range(2020, 2024):
#     print(f"Starting batters for {year}")
#     stats = batting_stats(year, qual=1)[['IDfg', 'Name', 'Season', 'WAR']]
#     data = stats.values.tolist()
#     UpdateNames(data)
    
#     print(f"Starting pitchers for {year}")
#     stats = pitching_stats(year, qual=1)[['IDfg', 'Name', 'Season', 'WAR']]
#     data = stats.values.tolist()
#     UpdateNames(data)
    
    
for year in range(2000, 2024):
    print(f"Starting batters for {year}")
    stats = batting_stats(year, qual=1)[['IDfg', 'Name', 'Season', 'WAR']]
    data = stats.values.tolist()
    dataToSubmit = []
    for d in data:
        cursor = db.cursor()
        alreadyEntered = cursor.execute(f"SELECT COUNT(*) FROM PlayerYearWar WHERE fangraphsId={d[0]} AND Season={d[2]} AND IsHitter=1").fetchone()[0] > 0
        if alreadyEntered:
            continue
        
        isHitter = cursor.execute(f"SELECT Position FROM Player WHERE fangraphsId={d[0]}").fetchone()[0] != "P"
        if isHitter:
            dataToSubmit.append([d[0],d[3],d[2],1])
            
    if len(dataToSubmit) > 0:
        cursor = db.cursor()
        cursor.executemany("INSERT INTO PlayerYearWar('fangraphsId','WAR','Season','IsHitter') VALUES(?,?,?,?)", dataToSubmit)
        db.commit()
    
    print(f"Starting pitchers for {year}")
    stats = pitching_stats(year, qual=1)[['IDfg', 'Name', 'Season', 'WAR']]
    data = stats.values.tolist()
    dataToSubmit = []
    for d in data:
        cursor = db.cursor()
        alreadyEntered = cursor.execute(f"SELECT COUNT(*) FROM PlayerYearWar WHERE fangraphsId={d[0]} AND Season={d[2]} AND IsHitter=0").fetchone()[0] > 0
        if alreadyEntered:
            continue
        
        position = cursor.execute(f"SELECT Position FROM Player WHERE fangraphsId={d[0]}").fetchone()[0]
        isPitcher = (position == "P") or (position == "TWP")
        if isPitcher:
            dataToSubmit.append([d[0],d[3],d[2],0])
            
    if len(dataToSubmit) > 0:
        cursor = db.cursor()
        cursor.executemany("INSERT INTO PlayerYearWar('fangraphsId','WAR','Season','IsHitter') VALUES(?,?,?,?)", dataToSubmit)
        db.commit()
    