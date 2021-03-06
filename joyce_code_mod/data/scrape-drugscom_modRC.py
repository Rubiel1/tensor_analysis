'''
Scrape the drugs.com website for drug classes and overall tree structure
'''
import os
import sys
#add anaconda path:
if os.name == 'nt': #'nt' = windows                                                                                                                                                                                        
    sys.path.append('C:\\anaconda\\lib\\site-packages') #in windows, alot of modules were installed with Anaconda
if os.name == 'posix': #PACE cluster
    #sys.path.append('/nv/hcoc1/rchen87/anaconda/lib/python2.7/site-packages') #put anaconda at the FRONT of the path        
    sys.path[0] = '/nv/hcoc1/rchen87/anaconda/lib/python2.7/site-packages'
    sys.path.insert(0, '') # this is a python standard; null string at start of path array
from bs4 import BeautifulSoup
import json
import requests
from Queue import deque
import time
import re
import numpy as np

BASE_URL = "http://www.drugs.com"

def parseTreeStruct(ul, parents):
    """
    Parse the drug class tree structure
    Returns: dict where the keys are the leaves and the values are the parents
    """
    result = {}
    for li in ul.find_all("li", recursive=False):
        key = next(li.stripped_strings)
        ul = li.find("ul")
        if ul:
            rootParents = parents + [key]
            result[key] = parseTreeStruct(ul, rootParents)
        else:
            result[key] = parents
    return result

def parseClassList(pageURL):
    """
    Parse the drug class list to obtain url links for 
    all the leaves to get the brand name and generic type for drugs in the category
    """
    urlLinks = deque()
    soup = BeautifulSoup(requests.get(pageURL).text)
    alphabetView = soup.find("a", text=re.compile("Alphabetical View"))
    itemList = alphabetView.parent.next_sibling()[0]
    ## Get all the children links
    for item in itemList.find_all("li"):
        if item.find("ul") == None:
            aItem = item.find("a")
            catName = aItem.get_text()
            link = BASE_URL + aItem.get('href')
            urlLinks.append([link, catName])
    ## parse the trees
    treeStruct = parseTreeStruct(itemList, [])
    return urlLinks, treeStruct

def parseDrugNames(pageURL, drugCat, drugDict):
    """
    Given a leaf node page, parses the table to get the brand and generic names of drugs in the category
    Returns: dict w/ key = brand / generic name, value = {"type", "cat", "genericName" (if brand)}
    """
    soup = BeautifulSoup(requests.get(pageURL).text)
    tableClass = soup.find("table", attrs={"class": "data-list-class"})
    if tableClass == None:
        return drugDict
    for row in tableClass.find_all("tr"):
        drugElement = row.find("td")
        if drugElement == None:
            continue
        aItems = drugElement.find_all("a")
        consumerName = aItems[0].get_text().lower()
        genericName = aItems[len(aItems)-1].get_text().lower()
        ## if the generic doesn't exist add it
        if not drugDict.has_key(genericName):
            drugDict[genericName] = {"type": "generic", "cat": set()}
        drugDict[genericName]["cat"].add(str(drugCat))
        if not drugDict.has_key(consumerName):
            drugDict[consumerName] = {"type": "brand", "cat": set(), "generic": genericName}
        drugDict[consumerName]["cat"].add(str(drugCat))
    return drugDict

def main():
    urlStack, treeStruct = parseClassList(BASE_URL + "/drug-classes.html?tree=1")
    drugDict = {}
    while len(urlStack):
        scrapeItem = urlStack.popleft()
        print scrapeItem
        itemDict = parseDrugNames(scrapeItem[0], scrapeItem[1], drugDict)
        time.sleep(np.random.uniform(1,5))
    with open('drugClass-struct.json', 'wb') as outfile:
        json.dump(treeStruct, outfile, indent=2)
    ## first we need to convert it to list
    drugDictJson = {}
    for k, v in drugDict.iteritems():
        v['cat'] = list(v['cat'])
        drugDictJson[k] = v
    with open('drugClass-dict.json', 'wb') as outfile:
        json.dump(drugDictJson, outfile, indent=2)

if __name__ == "__main__":
    main()
