import threading

class Timeout(Exception):
    pass

def GetUrl(driver, url):
    def TimeoutHandler():
        #print("Timed Out")
        raise TimeoutError("T")
    
    #print(url)
    #sys.stderr = io.StringIO()
    timer = threading.Timer(5, TimeoutHandler)
    timer.start()
    
    try:
        driver.get(url)
        #sys.stderr = sys.__stderr__
    except Timeout:
        raise Timeout
    except KeyboardInterrupt:
        timer.cancel()
        raise KeyboardInterrupt
    except TimeoutError:
        timer.cancel()
        GetUrl(driver, url)
    finally:
        timer.cancel()