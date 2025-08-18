import os
import sys
import json
import csv
import shutil
import requests
from datetime import datetime
from dateutil.relativedelta import relativedelta
import time
import math
import win32com.client
import numpy as np
import pandas as pd

print("all packages imported successfully")

#define today's date for quick calling
todayDate = datetime.now().strftime("%Y-%m-%d")

#function for writing new rows to output csv files
def writerowtocsv(outputcsvpath,row,mode):
    with open(outputcsvpath, mode, newline="", encoding="utf-8") as opencsv:
        csvwriter = csv.writer(opencsv)
        csvwriter.writerow(row)

#function to import the most recent dataverse report EXCEL file
def loadlatestdataversereport(tdrdataversereports, pattern):
    files = os.listdir(tdrdataversereports)
    files.sort(reverse=True)

    latest_file = None
    for file in files:
        if pattern in file:
            latest_file = file
            break

    if not latest_file:
        print(f"No file with '{pattern}' was found in '{tdrdataversereports}'.")
        return None
    else:
        file_path = os.path.join(tdrdataversereports, latest_file)
        df = pd.read_excel(file_path, sheet_name='datasets', engine='openpyxl')
        print(f"The most recent file '{latest_file}' has been loaded successfully.")
        return df

#function to search for the most recent output subfolder and then a specified CSV file within it    
def loadlatestoutputfile(directory, pattern):
    subfolders = [f for f in os.listdir(directory) if os.path.isdir(os.path.join(directory, f))]

    date_subfolders = []
    for folder in subfolders:
        try:
            datetime.strptime(folder, "%Y-%m-%d")
            date_subfolders.append(folder)
        except ValueError:
            continue

    date_subfolders.sort(reverse=True)
    for recent_folder in date_subfolders:
        folder_path = os.path.join(directory, recent_folder)
        files = os.listdir(folder_path)
        files.sort(reverse=True)

        for file in files:
            if pattern in file:
                file_path = os.path.join(folder_path, file)
                df = pd.read_csv(file_path)
                print(f"The most recent file '{file}' from folder '{recent_folder}' has been loaded successfully.")
                return df, folder_path

    print(f"No file with '{pattern}' was found in any subfolder of '{directory}'.")
    return None

# Open and read config parameters from .env file
configfile = ".env"
with open(configfile) as envfile:
    config = json.loads(envfile.read())

#define whether to run in test mode
test = config['test']
if test == "True":
    subset = 10
    print(f"only testing with the first {subset} records")

#define whether to run cross-validation to ID how many published datasets you have admin privileges to
crossvalidate = config['crossvalidate']

#load API key
headers_dataverse = {
    'X-Dataverse-key': config['dataverse_api_key']
}

#if tdr-dataverse-reports directory does not yet exist, create it
if not os.path.isdir("tdr-dataverse-reports"):
    os.mkdir("tdr-dataverse-reports")

#if outputs directory does not yet exist, create it
if not os.path.isdir("outputs"):
    os.mkdir("outputs")

#if outputs directory does not yet exist, create it
if not os.path.isdir("./outputs/" + todayDate):
    os.mkdir("outputs/" + todayDate)
    print("outputs/" + todayDate + " has been created successfully")





#create summary file
with open("outputs/" + todayDate + "/all_results_summary.txt", "w") as resultssummaryfile:
    resultssummaryfile.write("Results summary " + todayDate + "\n\n")
    resultssummaryfile.write("   REVIEW CRITERIA \n")
    resultssummaryfile.write("        UNPUBLISHED DATA years since created = "+ str(config['unpublisheddatasetreviewthresholdinyears']) +"  \n")
    resultssummaryfile.write("        UNPUBLISHED DATA dataset size threshold = "+ str(config['unpublisheddatasetreviewthresholdingb']) +"  \n")
    resultssummaryfile.write("        PUBLISHED DATA years since published = "+ str(config['publisheddatasetreviewthresholdinyears']) +"\n")
    resultssummaryfile.write("        PUBLISHED DATA dataset size threshold = "+ str(config['publisheddatasetreviewthresholdingb']) +"  \n")
    resultssummaryfile.write("        PUBLISHED DATA mitigating factor minimum downloads = "+ str(config['mitigatingfactormindownloadcount']) +"\n")
    resultssummaryfile.write("        PUBLISHED DATA mitigating factor: minimum citations = "+ str(config['mitigatingfactormincitationcount']) +"  \n\n")


#set initial counts to 0
totaldatasetsindataverse = 0
totaldatasetsindataverseovertenyearsold = 0
totaldatasetsindataverseoveroverfivegb = 0
totaldatasetsindataverseovertenyearsoldandoverfivegb = 0


#define file paths for all output CSV files
publishedneedsreviewcsvpath = "outputs/" + todayDate + "/stage3-needsreview-published-list-" + todayDate + "-" + str(config['institutionaldataverse']) + ".csv"
unpublishedneedsreviewcsvpath = "outputs/" + todayDate + "/stage3-needsreview-unpublished-list-" + todayDate + "-" + str(config['institutionaldataverse']) + ".csv"
publishedmitigatingfactorcsvpath = "outputs/" + todayDate + "/stage2-mitigatingfactor-published-list-" + todayDate + "-" + str(config['institutionaldataverse']) + ".csv"
publishednoreviewneededcsvpath = "outputs/" + todayDate + "/stage1-passed-published-list-" + todayDate + "-" + str(config['institutionaldataverse']) + ".csv"
unpublishednoreviewneededcsvpath = "outputs/" + todayDate + "/stage1-passed-unpublished-list-" + todayDate + "-" + str(config['institutionaldataverse']) + ".csv"
couldnotbeevaluatedcsvpath = "outputs/" + todayDate + "/could-not-be-evaluated-" + todayDate + "-" + str(config['institutionaldataverse']) + ".csv"
deaccessionedcsvpath = "outputs/" + todayDate + "/deaccessioned-" + todayDate + "-" + str(config['institutionaldataverse']) + ".csv"


#set output csv header row column names and write header rows to output csvs
publishedheaderrow = ["doi","title","author", "author contact email", "latest version state", "date created","date last updated", "date published", "years since creation", "years since last update", "years since publication", "version", "size(GB)", "unique downloads", "citation count", "funding", "exemption notes"]
unpublishedheaderrow = ["doi","title","author", "author contact email", "latest version state", "date created", "date last updated", "years since creation", "years since last update", "size(GB)", "funding", "exemption notes"]
deaccessionedheaderrow = ["doi","title","author", "author contact email", "latest version state", "date created", "date last updated", "years since creation", "years since last update", "size(GB)", "funding", "exemption notes", "status", "deaccession reason"]


#create output CSV files if config file indicates they should be created
if config["processunpublisheddatasets"] == "True":
    writerowtocsv(unpublishedneedsreviewcsvpath,unpublishedheaderrow,"w")
    writerowtocsv(unpublishednoreviewneededcsvpath,unpublishedheaderrow,"w")

if config["processpublisheddatasets"] == "True":
    writerowtocsv(publishedneedsreviewcsvpath,publishedheaderrow,"w")
    writerowtocsv(publishednoreviewneededcsvpath,publishedheaderrow,"w")
    writerowtocsv(publishedmitigatingfactorcsvpath,publishedheaderrow,"w")

if config["processdeaccessioneddatasets"] == "True":
    writerowtocsv(deaccessionedcsvpath,deaccessionedheaderrow,"w")  

writerowtocsv(couldnotbeevaluatedcsvpath,publishedheaderrow,"w")


#set start time and define log file path
ot = time.time()
timeprintlist = [time.time()]
logfilepath = "logs/" + datetime.now().strftime("%Y-%m-%d--%Hh-%Mm-%Ss") + ".txt"

#define write log function
def writelog(message):

    global logfilepath
    if not logfilepath:
        logfilepath=str("logs/" + datetime.now().strftime("%Y_%m_%d__%H_%M_%S") + "__log.txt")
    try:
        os.mkdir(logfilepath.split("/")[0])
    except Exception as e:
        pass
    processedtimes = []
    ct = time.time()
    totaltime = ct-ot
    stagetime = ct-timeprintlist[-1]
    timeprintlist.append(ct)
    timestoprocess = [stagetime, totaltime]
    for flt in timestoprocess:
        m, s = str(int(math.floor(flt/60))), int(round(flt%60))
        if s < 10:
            sstr = "0" + str(s)
        else:
            sstr = str(s)
        processedtimes.append(m+":"+sstr)
    timeprint = " " + datetime.now().strftime("%H:%M:%S") + "   " + processedtimes[1]  + "   +" + processedtimes[0] + "   "
    print(timeprint + str(message))
    try:
        if isinstance(logfilepath, str):
            with open(logfilepath, "a") as log:
                log.write(timeprint + str(message) + "\n")
    except Exception as e:
        print("ERROR: could not successfully write to log file (" + str(e) + ")")

writelog("Starting TDR Data Retention review process at " + datetime.now().strftime("%Y-%m-%d__%H:%M:%S"))

writelog("All packages imported and all major script parameters defined successfully\n")





#RETRIEVE INFORMATION ABOUT DEACCESSIONED DATASETS
if config["processdeaccessioneddatasets"] == "True":
    writelog("\n\nSTARTING TO PROCESS DEACCESSIONED DATASETS\n\n")
    ROLE_IDS = str(1) #admin role
    DVOBJECT_TYPES="Dataset"
    PUBLISHED_STATES="Deaccessioned"

    deaccessioneddatasetcounter = 0
    currentpageofresults = 0
    pagecount = config['paginationlimit']
    pageincrement = config['pageincrement']
    pagesize = config['pagesize']

    try:
        #substituting search endpoint
        deaccessionedqueryurl = f"https://dataverse.tdl.org/api/search?q=*&subtree={config['institutionaldataverse']}&start={currentpageofresults}&per_page={pagesize}&page={pageincrement}&fq=publicationStatus:Deaccessioned&type=dataset"

        writelog(deaccessionedqueryurl)

        deaccessioneddatasetlist = requests.get(deaccessionedqueryurl, headers={"X-Dataverse-key":config['dataverse_api_key']})
        deaccessioneddata = json.loads(deaccessioneddatasetlist.text)['data']
        print(f"\nRetrieving {len(deaccessioneddata['items'])} {PUBLISHED_STATES} datasets...\n")
        if currentpageofresults == 1:
            writelog("NUMBER OF DEACCESSIONED RESULTS: " + str(deaccessioneddata['total_count']))

        for deaccessioneddatasetsprocessedcount, deaccessioneddatasetinfo in enumerate(json.loads(deaccessioneddatasetlist.text)['data']['items']):

            writelog("#" + str(deaccessioneddatasetsprocessedcount) + " DEACCESSIONED DATASET")
            deaccessioneddatasetcounter += 1

            for k,v in deaccessioneddatasetinfo.items():
                writelog("   " + k + ": "+ str(v))

            doi = deaccessioneddatasetinfo['global_id']
            # entityid = deaccessioneddatasetinfo['entity_id'] #only available via MyData endpoint
            title = deaccessioneddatasetinfo['name']
            author = str(deaccessioneddatasetinfo['authors'])
            authorcontactemail = ""
            datecreated = str(deaccessioneddatasetinfo['createdAt'])
            datelastupdated = str(deaccessioneddatasetinfo['updatedAt'])
            yearssincecreation = ""
            yearssincelastupdated = ""
            datasetsizevaluegb = ""
            fundinginfo = ""
            datalicense = ""
            latestversionstate = ""
            exemptionnotes = ""
            status = deaccessioneddatasetinfo['versionState']
            deaccessionreason = deaccessioneddatasetinfo['deaccession_reason']

            writelog("\n\n")

            datasetdetailsrow = [doi, title, author, authorcontactemail, latestversionstate, datecreated, datelastupdated, yearssincecreation, yearssincelastupdated, datasetsizevaluegb, fundinginfo, exemptionnotes, status, deaccessionreason]


            writerowtocsv(deaccessionedcsvpath, datasetdetailsrow, "a")
        
        # currentpageofresults += pagesize
        # pageincrement += 1

    except Exception as e:
        print(f"Error processing: {str(e)}")

    with open("outputs/" + todayDate + "/all_results_summary.txt", "a") as resultssummaryfile:
        resultssummaryfile.write("   DEACCESSIONED DATASETS\n")
        resultssummaryfile.write("        number evaluated: " + str(deaccessioneddatasetcounter) + "\n\n")

    # while currentpageofresults < pagecount:

    #     try:
    #         currentpageofresults += 1

    #         # deaccessionedqueryurl = "https://dataverse.tdl.org/api/mydata/retrieve?role_ids=" + ROLE_IDS + "&dvobject_types=" +DVOBJECT_TYPES + "&published_states=" +PUBLISHED_STATES + "&selected_page=" + str(currentpageofresults)

    #         #substituting search endpoint
    #         deaccessionedqueryurl = f"https://dataverse.tdl.org/api/search?q=*&subtree={config['institutionaldataverse']}&start={currentpageofresults}&page={pageincrement}&fq=publicationStatus:Deaccessioned&type=dataset"

    #         writelog(deaccessionedqueryurl)

    #         deaccessioneddatasetlist = requests.get(deaccessionedqueryurl, headers={"X-Dataverse-key":config['dataverse_api_key']})

    #         deaccessioneddata = json.loads(deaccessioneddatasetlist.text)['data']
    #         print(deaccessioneddata['start'])

    #         pagecount = deaccessioneddata['pagination']['pageCount']

    #         if currentpageofresults == 1:
    #             writelog("NUMBER OF DEACCESSIONED RESULTS: " + str(deaccessioneddata['total_count']))


    #         for deaccessioneddatasetsprocessedcount, deaccessioneddatasetinfo in enumerate(json.loads(deaccessioneddatasetlist.text)['data']['items']):

    #             writelog("#" + str(deaccessioneddatasetsprocessedcount) + " DEACCESSIONED DATASET")
    #             deaccessioneddatasetcounter += 1

    #             for k,v in deaccessioneddatasetinfo.items():
    #                 writelog("   " + k + ": "+ str(v))

    #             doi = deaccessioneddatasetinfo['global_id']
    #             entityid = deaccessioneddatasetinfo['entity_id']
    #             title = deaccessioneddatasetinfo['name']
    #             author = str(deaccessioneddatasetinfo['authors'])
    #             authorcontactemail = ""
    #             datecreated = str(deaccessioneddatasetinfo['createdAt'])
    #             datelastupdated = str(deaccessioneddatasetinfo['updatedAt'])
    #             yearssincecreation = ""
    #             yearssincelastupdated = ""
    #             datasetsizevaluegb = ""
    #             fundinginfo = ""
    #             datalicense = ""
    #             latestversionstate = ""
    #             exemptionnotes = ""
    #             status = deaccessioneddatasetinfo['versionState']
    #             deaccessionreason = deaccessioneddatasetinfo['deaccession_reason']

    #             writelog("\n\n")

    #             datasetdetailsrow = [doi, title, author, authorcontactemail, latestversionstate, datecreated, datelastupdated, yearssincecreation, yearssincelastupdated, datasetsizevaluegb, fundinginfo, exemptionnotes, status, deaccessionreason]


    #             writerowtocsv(deaccessionedcsvpath, datasetdetailsrow, "a")


    #     except Exception as e:
    #         writelog(str(e))
    #         break

    # with open("outputs/" + todayDate + "/all_results_summary.txt", "a") as resultssummaryfile:
    #     resultssummaryfile.write("   DEACCESSIONED DATASETS\n")
    #     resultssummaryfile.write("        number evaluated: " + str(deaccessioneddatasetcounter) + "\n\n")

    writelog("\nFINISHED PROCESSING DEACCESSIONED DATASETS\n\n")









#TRY NEW METHOD TO RETRIEVE INFO ABOUT ALL PUBLISHED DATASETS


if config["processpublisheddatasets"] == "True":
    writelog("STARTING NEW METHOD TO PROCESS PUBLISHED DATASETS \n\n") 
    publisheddatasetcounter = 0
    passcount = 0
    needsreviewcount = 0
    currentpageofresults = 0
    pagecount = config['paginationlimit']

    ROLE_IDS = str(1) #admin role
    DVOBJECT_TYPES="dataset"
    PUBLISHED_STATES="Published"

    pageincrement = config['pageincrement']
    pagesize = config['pagesize']
    publisheddata = []
    
    while True:
        try:
            publisheddataqueryurl = f"https://dataverse.tdl.org/api/search?q=*&subtree={config['institutionaldataverse']}&start={currentpageofresults}&per_page={pagesize}&page={pageincrement}&fq=publicationStatus:{PUBLISHED_STATES}&type={DVOBJECT_TYPES}"

            writelog(publisheddataqueryurl)

            publisheddatasetlist = requests.get(publisheddataqueryurl, headers={"X-Dataverse-key":config['dataverse_api_key']})
            response = publisheddatasetlist.json()

            if not response.get('data') or not response['data'].get('items'):
                print("No data found or no more items.")
                break

            items = response['data']['items']
            total_count = response['data']['total_count']
            total_pages = math.ceil(total_count / pagesize)
            current_page = (currentpageofresults // pagesize) + 1

            writelog(f"Retrieved {len(items)} items from page {current_page} of {total_pages}")

            publisheddata.extend(items)

            currentpageofresults += pagesize
            if currentpageofresults >= total_count:
                writelog(f"NUMBER OF PUBLISHED RESULTS ACCESSIBLE UNDER USER ROLE STATUS: {total_count}")
                break
        except Exception as e:
            writelog(str(e))   
    
    if test == "True": 
        publisheddata = publisheddata[:subset]

    for publisheddatasetsprocessedcount, publisheddatasetinfo in enumerate(publisheddata):

        # doi,title,author,author contact email,latest version state,date deposited,date published,date distributed,years since deposit,years since publication,years since distribution,size(GB),unique downloads,citation count,funding,exemption notes

            # writelog("CREATED: " + str(unpublisheddatasetinfo['createdAt']))
            # writelog("UPDATED: " + str(unpublisheddatasetinfo['updatedAt']))
            publisheddatasetcounter += 1
            writelog("#" + str(publisheddatasetcounter) + " PUBLISHED DATASET")
            for k,v in publisheddatasetinfo.items():
                writelog(k + ": "+ str(v))


            doi = publisheddatasetinfo['global_id']
            # entityid = unpublisheddatasetinfo['entity_id'] #only for MyData endpoint
            title = publisheddatasetinfo['name']
            author = str(publisheddatasetinfo['authors'])
            authorcontactemail = ""
            datecreated = str(publisheddatasetinfo['createdAt'])
            datelastupdated = str(publisheddatasetinfo['updatedAt'])
            datepublished = ""
            yearssincecreation = ""
            yearssincelastupdated = ""
            yearssincepublished = ""
            major = publisheddatasetinfo['majorVersion']
            minor = publisheddatasetinfo['minorVersion']
            version = float(f"{major}.{minor}")
            datasetsizevaluegb = ""
            uniquedownloads = ""
            totalcitations = ""
            fundinginfo = ""
            datalicense = ""
            latestversionstate = ""
            exemptionnotes = ""

            creationyear = int(datecreated.lower().split("t")[0].split("-")[0])
            creationmonth = int(datecreated.lower().split("t")[0].split("-")[1])
            creationday = int(datecreated.lower().split("t")[0].split("-")[2])

            writelog("creationyear = " + str(creationyear))
            writelog("creationmonth = " + str(creationmonth))
            writelog("creationday = " + str(creationday))

            yearssincecreation = float(relativedelta(datetime.now(), datetime(creationyear,creationmonth,creationday,0,0,0,0)).years + (relativedelta(datetime.now(), datetime(creationyear,creationmonth,creationday,0,0,0,0)).months/12) + (relativedelta(datetime.now(), datetime(creationyear,creationmonth,creationday,0,0,0,0)).days/365))

            writelog("yearssincecreation = " + str(yearssincecreation))


            lastupdatedyear = int(datelastupdated.lower().split("t")[0].split("-")[0])
            lastupdatedmonth = int(datelastupdated.lower().split("t")[0].split("-")[1])
            lastupdatedday = int(datelastupdated.lower().split("t")[0].split("-")[2])

            writelog("lastupdatedyear = " + str(lastupdatedyear))
            writelog("lastupdatedmonth = " + str(lastupdatedmonth))
            writelog("lastupdatedday = " + str(lastupdatedday))

            yearssincelastupdated = float(relativedelta(datetime.now(), datetime(lastupdatedyear,lastupdatedmonth,lastupdatedday,0,0,0,0)).years + (relativedelta(datetime.now(), datetime(lastupdatedyear,lastupdatedmonth,lastupdatedday,0,0,0,0)).months/12) + (relativedelta(datetime.now(), datetime(lastupdatedyear,lastupdatedmonth,lastupdatedday,0,0,0,0)).days/365))

            writelog("yearssincelastupdated = " + str(yearssincelastupdated))

            datasetinfo = requests.get("https://dataverse.tdl.org/api/datasets/:persistentId/versions?persistentId=" + doi, headers={"X-Dataverse-key":config['dataverse_api_key']})
            data = json.loads(datasetinfo.text)['data']
            for entry in data:
                    for k, v in entry.items():
                        if type(v) is dict:
                            writelog("  " + k)
                            for k2,v2 in v.items():
                                if type(v2) is dict:
                                    writelog("     " + k2)
                                    for k3,v3 in v2.items():
                                        writelog("        " + k3 + ": " + str(v3))
                                else:
                                    writelog("     " + k2 + ": " + str(v2))
                        else:
                            writelog("  " + k + ": " + str(v))

            current_version = json.loads(datasetinfo.text)['data'][0] #for latest version
            all_files = current_version.get('files', [])
            total_filesize_bytes = sum(
                file.get('dataFile', {}).get('filesize', 0) for file in all_files
            )
            datasetsizevaluegb = round(total_filesize_bytes / (1024 ** 3), 2)
            writelog(f"Version: {version}, {major}, {minor}")
            writelog(f"Total File Size (GB): {datasetsizevaluegb}")

            citation = current_version.get('metadataBlocks', {}).get('citation', {})
            fields = citation.get('fields', [])

            funderinfo = []
            for field in fields:
                if field.get('typeName') == 'grantNumber':
                    for grant in field.get('value', []):
                        grant_number_agency = grant.get('grantNumberAgency', {}).get('value', '')
                        funderinfo.append(grant_number_agency)
            fundinginfo = "; ".join(funderinfo)
            writelog(f"Funder: {fundinginfo}")

            contactinfo = []
            for field in fields:
                if field.get('typeName') == 'datasetContact':
                    for contact in field.get('value', []):
                        contact_email = contact.get('datasetContactEmail', {}).get('value', '')
                        contactinfo.append(contact_email)
            authorcontactemail = "; ".join(contactinfo)
            writelog(f"Contact email: {authorcontactemail}")

            datepublished = current_version.get('publicationDate')
            
            publishedyear = int(datepublished.lower().split("t")[0].split("-")[0])
            publishedmonth = int(datepublished.lower().split("t")[0].split("-")[1])
            publishedday = int(datepublished.lower().split("t")[0].split("-")[2])

            writelog("publishedyear = " + str(publishedyear))
            writelog("publishedmonth = " + str(publishedmonth))
            writelog("publishedday = " + str(publishedday))

            yearssincepublished = float(relativedelta(datetime.now(), datetime(publishedyear,publishedmonth,publishedday,0,0,0,0)).years + (relativedelta(datetime.now(), datetime(publishedyear,publishedmonth,publishedday,0,0,0,0)).months/12) + (relativedelta(datetime.now(), datetime(publishedyear,publishedmonth,publishedday,0,0,0,0)).days/365))

            writelog("yearssincepublished = " + str(yearssincepublished))

            latestversionstate = current_version.get('latestVersionPublishingState')

            #metrics
            citationsrequest = requests.get("https://dataverse.tdl.org/api/datasets/:persistentId/makeDataCount/citations?persistentId=" + doi)
            citations = json.loads(citationsrequest.content.decode("latin-1"))
            if isinstance(citations.get("data"), dict) and "citations" in citations["data"]:
                totalcitations = str(citations["data"]["citations"])
            else:
                totalcitations = "0"
            downloadsrequest = requests.get("https://dataverse.tdl.org/api/datasets/:persistentId/makeDataCount/downloadsUnique?persistentId=" + doi)
            downloads = json.loads(downloadsrequest.content.decode("latin-1"))
            if isinstance(downloads.get("data"), dict) and "downloadsUnique" in downloads["data"]:
                uniquedownloads = str(downloads["data"]["downloadsUnique"])
            else:
                uniquedownloads = "0"

            datasetdetailsrow = [doi, title, author, authorcontactemail, latestversionstate, datecreated, datelastupdated, datepublished, yearssincecreation, yearssincelastupdated, yearssincepublished, version, datasetsizevaluegb, uniquedownloads, totalcitations, fundinginfo, exemptionnotes]

            #published dataset does not need review
            if yearssincecreation < float(config['publisheddatasetreviewthresholdinyears']) and datasetsizevaluegb < float(config['publisheddatasetreviewthresholdingb']):
                writerowtocsv(publishednoreviewneededcsvpath, datasetdetailsrow, "a")
                passcount += 1


            #published dataset does need to be reviewed
            else:
                writerowtocsv(publishedneedsreviewcsvpath, datasetdetailsrow, "a")
                needsreviewcount += 1

            writelog("\n\n")


    with open("outputs/" + todayDate + "/all_results_summary.txt", "a") as resultssummaryfile:
        resultssummaryfile.write("   PUBLISHED DATASETS\n")
        resultssummaryfile.write("        number evaluated: " + str(publisheddatasetcounter) + "\n")
        resultssummaryfile.write("        stage 1 pass count: " + str(passcount) + "\n")
        resultssummaryfile.write("        stage 1 needs review count: " + str(needsreviewcount) + "\n\n")


    writelog("\n\nFINISHED PROCESSING PUBLISHED DATASETS\n\n")
    
    # while currentpageofresults < pagecount:

    #     try:
    #         currentpageofresults += 1

    #         publisheddataqueryurl = f"https://dataverse.tdl.org/api/search?q=*&subtree={config['institutionaldataverse']}&start={currentpageofresults}&per_page={pagesize}&page={pageincrement}&fq=publicationStatus:{PUBLISHED_STATES}&type={DVOBJECT_TYPES}"

    #         writelog(publisheddataqueryurl)

    #         publisheddatasetlist = requests.get(publisheddataqueryurl, headers={"X-Dataverse-key":config['dataverse_api_key']})
    #         # response = publisheddatasetlist.json()

    #         publisheddata = json.loads(publisheddatasetlist.text)['data']

    #         totalresults = publisheddata['total_count']
    #         print(totalresults)

            # for dataset in publisheddata['items']:
            #     for k,v in dataset.items():
            #         print(k + ": " + str(v))
            # print("\n\n")


        #         total = 
        # print "=== Page", page, "==="
        # print "start:", start, " total:", total
        # for i in data['data']['items']:
        #     print "- ", i['name'], "(" + i['type'] + ")"

        #     writelog(publisheddata)

            # pagecount = publisheddata['pagination']['pageCount']

            # if currentpageofresults == 1:
            #     writelog("page 1")

            # for publisheddatasetsprocessedcount, publisheddatasetinfo in enumerate(publisheddata['items']):

            # # doi,title,author,author contact email,latest version state,date deposited,date published,date distributed,years since deposit,years since publication,years since distribution,size(GB),unique downloads,citation count,funding,exemption notes

            #     # writelog("CREATED: " + str(unpublisheddatasetinfo['createdAt']))
            #     # writelog("UPDATED: " + str(unpublisheddatasetinfo['updatedAt']))
            #     publisheddatasetcounter += 1
            #     writelog("#" + str(publisheddatasetcounter) + " PUBLISHED DATASET")
            #     for k,v in publisheddatasetinfo.items():
            #         writelog(k + ": "+ str(v))

        # except Exception as e:
        #     print(str(e))







#RETRIEVE INFORMATION ABOUT UNPUBLISHED DATASETS
if config["processunpublisheddatasets"] == "True":

    # writelog("STARTING TO PROCESS UNPUBLISHED DATASETS \n\n")

    # ROLE_IDS = str(1) #admin role
    # DVOBJECT_TYPES="dataset"
    # PUBLISHED_STATES="Draft"

    
    # unpublisheddatasetcounter = 0
    # passcount = 0
    # needsreviewcount = 0
    # currentpageofresults = 0
    # pagecount = config['paginationlimit']
    # pageincrement = config['pageincrement']
    # pagesize = config['pagesize']

    # while currentpageofresults < pagecount:

    #     try:
    #         currentpageofresults += 1

    #         unpublisheddataqueryurl = f"https://dataverse.tdl.org/api/search?q=*&subtree={config['institutionaldataverse']}&start={currentpageofresults}&per_page={pagesize}&page={pageincrement}&fq=publicationStatus:{PUBLISHED_STATES}&type={DVOBJECT_TYPES}"

    #         writelog(unpublisheddataqueryurl)

    #         unpublisheddatasetlist = requests.get(unpublisheddataqueryurl, headers={"X-Dataverse-key":config['dataverse_api_key']})

    #         unpublisheddata = json.loads(unpublisheddatasetlist.text)['data']

    #         print(f"\nRetrieving {len(unpublisheddata['items'])} {PUBLISHED_STATES} datasets...\n")

    writelog("STARTING TO PROCESS UNPUBLISHED DATASETS \n\n")

    ROLE_IDS = str(1)  # admin role
    DVOBJECT_TYPES = "dataset"
    PUBLISHED_STATES = "Draft"

    unpublisheddatasetcounter = 0
    passcount = 0
    needsreviewcount = 0
    currentpageofresults = 0
    pagesize = config['pagesize']
    pageincrement = config['pageincrement']
    unpublisheddata = [] #creating empty list to store all results

    while True:
        try:
            unpublisheddataqueryurl = f"https://dataverse.tdl.org/api/search?q=*&subtree={config['institutionaldataverse']}&start={currentpageofresults}&per_page={pagesize}&page={pageincrement}&fq=publicationStatus:{PUBLISHED_STATES}&type={DVOBJECT_TYPES}"

            writelog(unpublisheddataqueryurl)

            unpublisheddatasetlist = requests.get(unpublisheddataqueryurl, headers={"X-Dataverse-key":config['dataverse_api_key']})
            response = unpublisheddatasetlist.json()

            if not response.get('data') or not response['data'].get('items'):
                print("No data found or no more items.")
                break

            items = response['data']['items']
            total_count = response['data']['total_count']
            total_pages = math.ceil(total_count / pagesize)
            current_page = (currentpageofresults // pagesize) + 1

            writelog(f"Retrieved {len(items)} items from page {current_page} of {total_pages}")

            unpublisheddata.extend(items)

            currentpageofresults += pagesize
            if currentpageofresults >= total_count:
                writelog(f"NUMBER OF UNPUBLISHED RESULTS ACCESSIBLE UNDER USER ROLE STATUS: {total_count}")
                break
        except Exception as e:
            writelog(str(e))   
                
            # writelog("https://dataverse.tdl.org/api/mydata/retrieve?role_ids=" + ROLE_IDS + "&dvobject_types=" +DVOBJECT_TYPES + "&published_states=" +PUBLISHED_STATES + "&selected_page=" + str(currentpageofresults))
            
            # unpublisheddatasetlist = requests.get("https://dataverse.tdl.org/api/mydata/retrieve?role_ids=" + ROLE_IDS + "&dvobject_types=" + DVOBJECT_TYPES + "&published_states=" + PUBLISHED_STATES + "&selected_page=" + str(currentpageofresults), headers={"X-Dataverse-key":config['dataverse_api_key']})

            # unpublisheddata = json.loads(unpublisheddatasetlist.text)['data']

            # writelog(unpublisheddata)

            # pagecount = unpublisheddata['pagination']['pageCount']

            # if currentpageofresults == 1:
            #     writelog("NUMBER OF UNPUBLISHED RESULTS ACCESSIBLE UNDER USER ROLE STATUS "+ ROLE_IDS +": " + str(unpublisheddata['pagination']['numResults']))

    if test == "True":
        unpublisheddata = unpublisheddata[:subset]

    for unpublisheddatasetsprocessedcount, unpublisheddatasetinfo in enumerate(unpublisheddata):

    # doi,title,author,author contact email,latest version state,date deposited,date published,date distributed,years since deposit,years since publication,years since distribution,size(GB),unique downloads,citation count,funding,exemption notes

        # writelog("CREATED: " + str(unpublisheddatasetinfo['createdAt']))
        # writelog("UPDATED: " + str(unpublisheddatasetinfo['updatedAt']))
        unpublisheddatasetcounter += 1
        writelog("#" + str(unpublisheddatasetcounter) + " UNPUBLISHED DATASET")
        for k,v in unpublisheddatasetinfo.items():
            writelog(k + ": "+ str(v))


        doi = unpublisheddatasetinfo['global_id']
        # entityid = unpublisheddatasetinfo['entity_id'] #only for MyData endpoint
        title = unpublisheddatasetinfo['name']
        author = str(unpublisheddatasetinfo['authors'])
        authorcontactemail = ""
        datecreated = str(unpublisheddatasetinfo['createdAt'])
        datelastupdated = str(unpublisheddatasetinfo['updatedAt'])
        yearssincecreation = ""
        yearssincelastupdated = ""
        datasetsizevaluegb = ""
        fundinginfo = ""
        datalicense = ""
        latestversionstate = ""
        exemptionnotes = ""


            #     try:
            #         citationcount = str(len(citations['data']))

            #     except:
            #         citationcount = 0


            #     # datetimeofmostrecentupdate = datetime.strptime(repo['updated_at'], '%Y-%m-%dT%H:%M:%SZ')

            #     # monthssincemostrecentupdate = float(relativedelta(datetime.now(), datetime(yearofmostrecentupdate,monthofmostrecentupdate,dayofmostrecentupdate,0,0,0,0)).months)

        creationyear = int(datecreated.lower().split("t")[0].split("-")[0])
        creationmonth = int(datecreated.lower().split("t")[0].split("-")[1])
        creationday = int(datecreated.lower().split("t")[0].split("-")[2])

        writelog("creationyear = " + str(creationyear))
        writelog("creationmonth = " + str(creationmonth))
        writelog("creationday = " + str(creationday))

        yearssincecreation = float(relativedelta(datetime.now(), datetime(creationyear,creationmonth,creationday,0,0,0,0)).years + (relativedelta(datetime.now(), datetime(creationyear,creationmonth,creationday,0,0,0,0)).months/12) + (relativedelta(datetime.now(), datetime(creationyear,creationmonth,creationday,0,0,0,0)).days/365))

        writelog("yearssincecreation = " + str(yearssincecreation))


        lastupdatedyear = int(datecreated.lower().split("t")[0].split("-")[0])
        lastupdatedmonth = int(datecreated.lower().split("t")[0].split("-")[1])
        lastupdatedday = int(datecreated.lower().split("t")[0].split("-")[2])

        writelog("lastupdatedyear = " + str(lastupdatedyear))
        writelog("lastupdatedmonth = " + str(lastupdatedmonth))
        writelog("lastupdatedday = " + str(lastupdatedday))

        yearssincelastupdated = float(relativedelta(datetime.now(), datetime(lastupdatedyear,lastupdatedmonth,lastupdatedday,0,0,0,0)).years + (relativedelta(datetime.now(), datetime(lastupdatedyear,lastupdatedmonth,lastupdatedday,0,0,0,0)).months/12) + (relativedelta(datetime.now(), datetime(creationyear,creationmonth,creationday,0,0,0,0)).days/365))

        writelog("yearssincelastupdated = " + str(yearssincelastupdated))


        # datasetsizerequest = requests.get("https://dataverse.tdl.org/api/datasets/" + str(entityid) + "/storagesize", headers={"X-Dataverse-key":config['dataverse_api_key']})
        # datasizemessage = str(json.loads(datasetsizerequest.text)['data'])
        # datasetsizevaluegb = float(int(datasizemessage.split("dataset:")[1].split(" bytes")[0].strip().replace(",","")) / 1000000000)
        # writelog("size = " + str(round(datasetsizevaluegb,3) + " GB"))

        datasetinfo = requests.get("https://dataverse.tdl.org/api/datasets/:persistentId/versions/:draft?persistentId=" + doi, headers={"X-Dataverse-key":config['dataverse_api_key']})
        writelog(json.loads(datasetinfo.text)['data'])
        for k,v in json.loads(datasetinfo.text)['data'].items():
            if type(v) is dict:
                writelog("  " + k)
                for k2,v2 in v.items():
                    if type(v2) is dict:
                        writelog("     " + k2)
                        for k3,v3 in v2.items():
                            writelog("        " + k3 + ": " + str(v3))
                    else:
                        writelog("     " + k2 + ": " + str(v2))
            else:
                writelog("  " + k + ": " + str(v))

        response_data = json.loads(datasetinfo.text)['data']
        files = response_data.get('files', [])
        total_filesize_bytes = sum(
                file.get('dataFile', {}).get('filesize', 0) for file in files
            )
        datasetsizevaluegb = round(total_filesize_bytes / (1024 ** 3), 2)
        writelog(f"     Total File Size (GB): {datasetsizevaluegb}")

        citation = response_data.get('metadataBlocks', {}).get('citation', {})
        fields = citation.get('fields', [])
        funderinfo = []
        for field in fields:
            if field['typeName'] == 'grantNumber':
                for grant in field.get('value', []):
                    grant_number_agency = grant.get('grantNumberAgency', {}).get('value', '')
                    funderinfo.append(grant_number_agency)

        fundinginfo = "; ".join(funderinfo)
        contactinfo = []
        for field in fields:
            if field['typeName'] == 'datasetContact':
                for contact in field.get('value', []):
                    contact_email = contact.get('datasetContactEmail', {}).get('value', '')
                    contactinfo.append(contact_email)
        authorcontactemail = "; ".join(contactinfo)

        latestversionstate=response_data.get('latestVersionPublishingState')

        datasetdetailsrow = [doi, title, author, authorcontactemail, latestversionstate, datecreated, datelastupdated, yearssincecreation, yearssincelastupdated, datasetsizevaluegb, fundinginfo, exemptionnotes]

        #unpublished dataset does not need review
        if yearssincecreation < float(config['unpublisheddatasetreviewthresholdinyears']) and datasetsizevaluegb < float(config['unpublisheddatasetreviewthresholdingb']):
            writerowtocsv(unpublishednoreviewneededcsvpath, datasetdetailsrow, "a")
            passcount += 1


        #unpublished dataset does need to be reviewed
        else:
            writerowtocsv(unpublishedneedsreviewcsvpath, datasetdetailsrow, "a")
            needsreviewcount += 1

        writelog("\n\n")


    with open("outputs/" + todayDate + "/all_results_summary.txt", "a") as resultssummaryfile:
        resultssummaryfile.write("   UNPUBLISHED DATASETS\n")
        resultssummaryfile.write("        number evaluated: " + str(unpublisheddatasetcounter) + "\n")
        resultssummaryfile.write("        stage 1 pass count: " + str(passcount) + "\n")
        resultssummaryfile.write("        stage 1 needs review count: " + str(needsreviewcount) + "\n\n")


    writelog("\n\nFINISHED PROCESSING UNPUBLISHED DATASETS\n\n")


















#ORIGINAL PROCESS TO RETRIEVE INFORMATION ABOUT PUBLISHED DATASETS THAT DOES NOT SUCCESSFULLY FIND ALL DATASETS
# if config["processpublisheddatasets"] == "True":

#     call = config['dataverse_api_host'] + "/api/info/metrics/uniquedownloads?parentAlias=" + config['institutionaldataverse']
#     writelog("data request url = " + call)

#     datasetdoianddownloadcountlist = requests.get(call)
#     print(datasetdoianddownloadcountlist)

#     processedpublisheddatasets = 0
#     mitigatingfactordatasetcount = 0
#     passcount = 0
#     needsreviewcount = 0
#     insufficientprivilegestoprocesscount = 0
    # writelog(datasetdoianddownloadcountlist.text)



    # for datasetsprocessedcount, rawdoianddownloadcount in enumerate(datasetdoianddownloadcountlist.text.split("\n")):

    #     if datasetsprocessedcount > 0:

    #         try:

    #             publishedneedsreview = False
    #             unpublishedneedsreview = False
    #             publishednoreviewneeded = False
    #             unpublishednoreviewneeded = False
    #             mitigatingfactorpresent = False

    #             doi = ""
    #             entityid = ""
    #             title = ""
    #             author = ""
    #             authorcontactemail = ""
    #             datedeposited = ""
    #             datepublished = ""
    #             datedistributed = ""
    #             yearssincedeposit = ""
    #             yearssincepublication = ""
    #             yearssincedistribution = ""
    #             uniquedownloads = ""
    #             fundinginfo = ""
    #             datalicense = ""
    #             latestversionstate = ""
    #             exemptionnotes = ""

    #             # datasetretentionscore = 0
    #             cleaneddoianddownloadcount = rawdoianddownloadcount.replace("\"","")
    #             doi = cleaneddoianddownloadcount.split(",")[0]
    #             uniquedownloads = cleaneddoianddownloadcount.split(",")[1]

    #             writelog("\n\n\n")
    #             writelog("#" + str(datasetsprocessedcount) + " Starting to process " + doi)

    #             processedpublisheddatasets += 1

    #             citationsrequest = requests.get("https://dataverse.tdl.org/api/datasets/:persistentId/makeDataCount/citations?persistentId=" + doi)
    #             citations = json.loads(citationsrequest.content.decode("latin-1"))

    #             datasetgeneralinforequest = requests.get("https://dataverse.tdl.org/api/datasets/:persistentId/?persistentId=" + doi)
    #             datasetgeneralinforequest= json.loads(datasetgeneralinforequest.content.decode("latin-1"))

    #             try:
    #                 latestversionstate = str(datasetgeneralinforequest['data']['latestVersion']['versionState'])
    #             except Exception as e:
    #                 writelog(str(e))

    #             writelog("versionState:  " + str(datasetgeneralinforequest['data']['latestVersion']['versionState']))
    #             datasetid = str(datasetgeneralinforequest['data']['id'])


    #             metadatarequest = requests.get("https://dataverse.tdl.org/api/datasets/"+datasetid+"/versions/1.0/metadata", headers={"X-Dataverse-key":config['dataverse_api_key']})
    #             metadata = json.loads(metadatarequest.content.decode("latin-1"))

    #             for k,v in metadata['data'].items():
    #                 try:
    #                     if len(str(v)) > 50:
    #                         writelog("   " + k + ":  " + str(v)[:50].replace("\n") + "....")
    #                     else:
    #                         writelog("   " + k + ":  " + str(v))
    #                 except:
    #                     pass

    #             # datasetsizerequest = requests.get("https://dataverse.tdl.org/api/datasets/"+datasetid+"/storagesize", headers={"X-Dataverse-key":config['dataverse_api_key']})
    #             # datasetsize = json.loads(datasetsizerequest.content.decode("latin-1"))

    #             ispartofdata = metadata['data']['schema:isPartOf']
    #             dataversehierarchy = []
    #             spacing = "   "

                
    #             while ispartofdata['@id'] != 'https://dataverse.tdl.org/dataverse/root':
    #                 try:
    #                     dataversehierarchy.append(ispartofdata['schema:name'])
    #                     writelog(spacing + "is part of " + ispartofdata['schema:name'])
    #                     spacing += spacing
    #                     ispartofdata = ispartofdata['schema:isPartOf']
    #                 except Exception as e:
    #                     print(str(e))

    #             try:
    #                 dataversehierarchy.append('TDR Root')
    #                 dataversehierarchy.reverse()
    #                 dataversehierarchy.append("dataset")

    #                 title = metadata['data']['title']
    #                 author = metadata['data']['citation:datasetContact']['citation:datasetContactName']
    #                 authorcontactemail = metadata['data']['citation:datasetContact']['citation:datasetContactEmail']
    #             except Exception as e:
    #                 print(str(e))

    #             # creationyear = int(datecreated.lower().split("t")[0].split("-")[0])
    #             # creationmonth = int(datecreated.lower().split("t")[0].split("-")[1])
    #             # creationday = int(datecreated.lower().split("t")[0].split("-")[2])
    #             #
    #             # writelog("creationyear = " + str(creationyear))
    #             # writelog("creationmonth = " + str(creationmonth))
    #             # writelog("creationday = " + str(creationday))
    #             #
    #             # yearssincecreation = float(relativedelta(datetime.now(), datetime(creationyear,creationmonth,creationday,0,0,0,0)).years + (relativedelta(datetime.now(), datetime(creationyear,creationmonth,creationday,0,0,0,0)).months/12) + (relativedelta(datetime.now(), datetime(creationyear,creationmonth,creationday,0,0,0,0)).days/365))
    #             #
    #             # writelog("yearssincecreation = " + str(yearssincecreation))
    #             #
    #             #
    #             # lastupdatedyear = int(datecreated.lower().split("t")[0].split("-")[0])
    #             # lastupdatedmonth = int(datecreated.lower().split("t")[0].split("-")[1])
    #             # lastupdatedday = int(datecreated.lower().split("t")[0].split("-")[2])
    #             #
    #             # writelog("lastupdatedyear = " + str(lastupdatedyear))
    #             # writelog("lastupdatedmonth = " + str(lastupdatedmonth))
    #             # writelog("lastupdatedday = " + str(lastupdatedday))
    #             #
    #             # yearssincelastupdated = float(relativedelta(datetime.now(), datetime(lastupdatedyear,lastupdatedmonth,lastupdatedday,0,0,0,0)).years + (relativedelta(datetime.now(), datetime(lastupdatedyear,lastupdatedmonth,lastupdatedday,0,0,0,0)).months/12) + (relativedelta(datetime.now(), datetime(creationyear,creationmonth,creationday,0,0,0,0)).days/365))
    #             #
    #             # writelog("yearssincelastupdated = " + str(yearssincelastupdated))




    #             if config['institutionname'] + " Dataverse Collection" not in str(metadata['data']['schema:isPartOf']) and config['institutionaldataverse'] != "*":
    #                 writelog(spacing + " skipping dataset because it is in not in the " + config['institutionaldataverse'] + " dataverse")


    #             if str("https://dataverse.tdl.org/dataverse/" + config['institutionaldataverse']) in str(metadata) or config['institutionaldataverse'] == "*":
    #                 writelog(spacing + " dataset is within a dataverse that is designated for processing, continuing to evaluate dataset...")


    #                 writelog("   preparing to request dataset size.....")

    #                 try:
    #                     datasetsizerequest = requests.get("https://dataverse.tdl.org/api/datasets/" + str(datasetid) + "/storagesize", headers={"X-Dataverse-key":config['dataverse_api_key']})
    #                     datasizemessage = str(json.loads(datasetsizerequest.text)['data'])
    #                     datasetsizevaluegb = float(int(datasizemessage.split("dataset:")[1].split(" bytes")[0].strip().replace(",","")) / 1073741824)

    #                     writelog("   size = " + str(datasetsizevaluegb) + "GB")

    #                     if config['showdatasetdetails'] == "True":
    #                         writelog("   Dataset DOI: " + str(doi) + "")
    #                         writelog("   Dataset ID: " + str(datasetid) + "")
    #                         writelog("   Unique Downloads: " + uniquedownloads + "")
    #                         writelog("   Citation Count: " + str(len(citations['data'])) + "")
    #                         writelog("   Citation List: " + str(citations['data']) + "")
    #                         writelog("   Corresponding Author Name: " + metadata['data']['citation:datasetContact']['citation:datasetContactName'] + "")
    #                         writelog("   Corresponding Author Email: " + metadata['data']['citation:datasetContact']['citation:datasetContactEmail'] + "")
    #                         writelog("   Dataset Size (GB): " + str(round(datasetsizevaluegb,4)) + "")
    #                         # writelog("   Grant Number(s): " + str(metadata['data']))
    #                         writelog("   Data Access Restrictions: " + str(metadata['data']['dvcore:fileTermsOfAccess']['dvcore:fileRequestAccess']) + "")

    #                         try:
    #                             writelog("   Deposit Date: " + str(metadata['data']['dateOfDeposit']) + "")
    #                             datedeposited = str(str(metadata['data']['dateOfDeposit']))
    #                             deposityear = int(metadata['data']['dateOfDeposit'].split("-")[0])
    #                             depositmonth = int(metadata['data']['dateOfDeposit'].split("-")[1])
    #                             depositday = int(metadata['data']['dateOfDeposit'].split("-")[2])
    #                             yearssincepublication = float(relativedelta(datetime.now(), datetime(deposityear,depositmonth,depositday,0,0,0,0)).years + (relativedelta(datetime.now(), datetime(deposityear,depositmonth,depositday,0,0,0,0)).months/12))
    #                             yearssincepublication = round(yearssincepublication,3)
    #                             # writelog("   deposityear = " + str(deposityear))
    #                             # writelog("   depositmonth = " + str(depositmonth))
    #                             # writelog("   depositday = " + str(depositday))
    #                             # writelog("   yearssincepublication = " + str(yearssincepublication))
    #                         except Exception as e:
    #                             writelog("ERROR: " + str(e) + "\n\n")

    #                         try:
    #                             writelog("   Publication Date: " + str(metadata['data']['schema:datePublished']) + "")
    #                             datepublished = str(metadata['data']['schema:datePublished'])

    #                         except Exception as e:
    #                             writelog("   Publication Date: ")
    #                             datepublished = ""

    #                         try:
    #                             writelog("   Distribution Date: " + str(metadata['data']['distributionDate']) + "")
    #                             datedistributed = str(metadata['data']['distributionDate'])

    #                         except Exception as e:
    #                             writelog("   Distribution Date: ")
    #                             datedistributed = ""


    #                     # if "ERROR" in str(datasetsizevaluegb):
    #                     #     input(">>>>")
    #                     #     datasetsizevaluegb = ""
    #                     #     datasetdetailsrow = [doi, title, author, authorcontactemail, latestversionstate, datedeposited, datepublished, datedistributed, yearssincedeposit, yearssincepublication, yearssincedistribution, datasetsizevaluegb, uniquedownloads, str(len(citations['data'])), fundinginfo, exemptionnotes]

    #                     #     writerowtocsv(couldnotbeevaluatedcsvpath, datasetdetailsrow, "a")
    #                     #     writelog("      ERROR: " + str(datasetsize))
    #                     #     writelog("      this dataset could not be evaluated because of insufficient privileges to access data size information")



    #                     # else:
    #                         # datasetsizevaluegb = int(str(datasetsize).split("dataset:")[1].split(" b")[0].strip().replace(",",""))
    #                         # datasetsizevaluegb = round((datasetsizevaluegb/1073741824),3)

    #                         # distributionyear = int(metadata['data']['citation:distributionDate'].split("-")[0])
    #                         # distributionmonth = int(metadata['data']['citation:distributionDate'].split("-")[1])
    #                         # distributionday = int(metadata['data']['citation:distributionDate'].split("-")[2])
    #                         #
    #                         # writelog("   distributionyear = " + str(distributionyear))
    #                         # writelog("   distributionmonth = " + str(distributionmonth))
    #                         # writelog("   distributionday = " + str(distributionday))
    #                         #
    #                         # yearssincedistribution = float(relativedelta(datetime.now(), datetime(distributionyear,distributionmonth,distributionday,0,0,0,0)).years + (relativedelta(datetime.now(), datetime(distributionyear,distributionmonth,distributionday,0,0,0,0)).months/12))
    #                         # writelog("   yearssincedistribution = " + str(yearssincedistribution))


    #                         # publicationyear = int(metadata['data']['schema:datePublished'].split("-")[0])
    #                         # publicationmonth = int(metadata['data']['schema:datePublished'].split("-")[1])
    #                         # publicationday = int(metadata['data']['schema:datePublished'].split("-")[2])
    #                         #
    #                         # writelog("   publicationyear = " + str(publicationyear))
    #                         # writelog("   publicationmonth = " + str(publicationmonth))
    #                         # writelog("   publicationday = " + str(publicationday))
    #                         #
    #                         # yearssincepublication = float(relativedelta(datetime.now(), datetime(publicationyear,publicationmonth,publicationday,0,0,0,0)).years + (relativedelta(datetime.now(), datetime(publicationyear,publicationmonth,publicationday,0,0,0,0)).months/12))
    #                         # writelog("   yearssincepublication = " + str(yearssincepublication))



    #                         # if config['showdatasetdetails']:
    #                         #     writelog()
    #                         #     for k,v in metadata['data'].items():
    #                         #         writelog(k, str(v))



    #                         for k, v in metadata['data'].items():

    #                             # writelog("      " + k + "\n          " + str(v))

    #                             if k == "title":
    #                                 writelog("   " + k + ": " + str(v))
    #                             if k == "grantNumber":
    #                                 writelog("   " + k + ": " + str(v))
    #                                 fundinginfo = str(v)
    #                             if k == "publication":
    #                                 writelog("   " + k + ": " + str(v))
    #                             if k == "dateOfDeposit":
    #                                 writelog("   " + k + ": " + str(v))
    #                             if k == "schema:license":
    #                                 writelog("   " + k + ": " + str(v))
    #                                 datalicense = str(v)
    #                             if k == "dvcore:fileTermsOfAccess":
    #                                 if v['dvcore:fileRequestAccess'] == False:
    #                                     writelog("   Access Level: Open Access")
    #                                 else:
    #                                     writelog("   Access Level: Restricted Access (request must be submitted to access files)")
    #                                 writelog("  " + k + ": " +  str(v))
                                    
    #                             if k == "author":
    #                                 writelog("   Author: " + str(v))
    #                             if k == "citation:datasetContact":
    #                                 writelog("   Dataset Contact: " + str(v))
    #                             if k == "citation:dsDescription":
    #                                 writelog("   Description Length: " + str(len(v)))




    #                         if len(citations['data']) >= int(config["mitigatingfactormincitationcount"]):
    #                             mitigatingfactorpresent = True
    #                             exemptionnotes += "High citation count; "

    #                         if int(uniquedownloads) >= int(config["mitigatingfactormindownloadcount"]):
    #                             mitigatingfactorpresent = True
    #                             exemptionnotes += "High unique download count; "

    #                         if len(fundinginfo) > 0:
    #                             mitigatingfactorpresent = True
    #                             exemptionnotes += "Funded research; "


    #                         datasetdetailsrow = [doi, title, author, authorcontactemail, latestversionstate, datedeposited, datepublished, datedistributed, yearssincedeposit, yearssincepublication, yearssincedistribution, datasetsizevaluegb, uniquedownloads, str(len(citations['data'])), fundinginfo, exemptionnotes]


    #                         writelog("   preparing to determine if dataset needs to be reviewed...")
    #                         writelog("       years since publication = " + str(yearssincepublication))
    #                         writelog("       config['publisheddatasetreviewthresholdinyears'] = " + str(config['publisheddatasetreviewthresholdinyears']))
    #                         writelog("       datasetsizevaluegb = " + str(datasetsizevaluegb))
    #                         writelog("       config['publisheddatasetreviewthresholdingb'] = " + str(config['publisheddatasetreviewthresholdingb']))

    #                         try:
    #                             if float(yearssincepublication) > float(config['publisheddatasetreviewthresholdinyears']) and float(datasetsizevaluegb) > float(config['publisheddatasetreviewthresholdingb']):
    #                                 publishedneedsreview = True

    #                                 if mitigatingfactorpresent:
    #                                     writerowtocsv(publishedmitigatingfactorcsvpath, datasetdetailsrow, "a")
    #                                     writelog("      THIS DATASET HAS A MITIGATING FACTOR AND DOES NOT NEED TO BE REVIEWED")
    #                                     mitigatingfactordatasetcount += 1

    #                                 else:
    #                                     writerowtocsv(publishedneedsreviewcsvpath, datasetdetailsrow, "a")
    #                                     writelog("      THIS DATASET NEEDS TO BE REVIEWED")
    #                                     needsreviewcount += 1

    #                             else:
    #                                 publishednoreviewneeded = True
    #                                 writerowtocsv(publishednoreviewneededcsvpath, datasetdetailsrow, "a")
    #                                 writelog("      this dataset does not need to be reviewed")
    #                                 passcount += 1

    #                         except Exception as e:
    #                             writelog("        " + str(e))
    #                             writelog("        " + "STATUS UNKNOWN DUE TO ERROR")


    #                 except Exception as e:
    #                     writelog(str(e))
    #                     writelog("   Dataset is in the "+ str(config['institutionaldataverse']).upper() +" dataverse but privileges are insufficient for retrieving dataset size")
    #                     writerowtocsv(couldnotbeevaluatedcsvpath, datasetdetailsrow, "a")
    #                     insufficientprivilegestoprocesscount += 1




    #         # author
    #         # {'citation:authorName': 'Dainer-Best, Justin', 'citation:authorAffiliation': 'University of Texas at Austin', 'authorIdentifierScheme': 'ORCID', 'authorIdentifier': '0000-0002-1868-0337'}
    #         # citation:dsDescription
    #         # citation:datasetContact
    #         # http://creativecommons.org/publicdomain/zero/1.0
    #         # dvcore:fileTermsOfAccess
    #         # {'dvcore:fileRequestAccess': False}


    #               # publication
    #               #     {'publicationCitation': 'Nazmus Sakib & Amit Bhasin (2019) Measuring polarity-based distributions (SARA) of bitumen using simplified chromatographic techniques, International Journal of Pavement Engineering, 20:12, 1371-1384, DOI: 10.1080/10298436.2018.1428972', 'publicationIDType': 'doi', 'publicationIDNumber': '10.1080/10298436.2018.1428972', 'publicationURL': 'https://doi.org/10.1080/10298436.2018.1428972'}


    #               # grantNumber
    #               #     {'citation:grantNumberAgency': 'NASA', 'citation:grantNumberValue': 'NNX17AG70G'}

    #         # 130211
    #         # https://dataverse.tdl.org/dataset.xhtml?persistentId=doi:10.18738/T8/PRAGLR

    #         # PUBLICATION INFO
    #         # {"typeName":"publication","multiple":true,"typeClass":"compound","value":[{"publicationCitation":{"typeName":"publicationCitation","multiple":false,"typeClass":"primitive","value":"Harris KM, Hubbard DD, Kuwajima M, Abraham WC, Bourne JN, Bowden JB, Haessly A, Mendenhall JM, Parker PH, Shi B, Spacek J. (2022) Dendritic spine density scales with microtubule number in rat hippocampal dendrites. Neuroscience. https://doi.org/10.1016/j.neuroscience.2022.02.021"},"publicationURL":{"typeName":"publicationURL","multiple":false,"typeClass":"primitive","value":"https://doi.org/10.1016/j.neuroscience.2022.02.021"}}]},

    #         # GRANT INFO
    #         # {"typeName":"grantNumber","multiple":true,"typeClass":"compound","value":[{"grantNumberAgency":{"typeName":"grantNumberAgency","multiple":false,"typeClass":"primitive","value":"National Institutes of Health"},"grantNumberValue":{"typeName":"grantNumberValue","multiple":false,"typeClass":"primitive","value":"MH095980"}},{"grantNumberAgency":{"typeName":"grantNumberAgency","multiple":false,"typeClass":"primitive","value":"National Institutes of Health"},"grantNumberValue":
    #                 # writelog("   Associated Publication: " + "")
    #                 # writelog("   Associated Grant: " + "")
    #                 # writelog("   Funder Requirements: " + "")
    #                 # writelog("   Data Access Restrictions: " + "")
    #                 # writelog("   Metadata Quality Score: " + "")




    #         except Exception as e:
    #             writelog(str(e))

    # with open("outputs/" + todayDate + "/all_results_summary.txt", "a") as resultssummaryfile:
    #     resultssummaryfile.write("   PUBLISHED DATASETS\n")
    #     resultssummaryfile.write("        number evaluated: " + str(processedpublisheddatasets) + "\n")
    #     resultssummaryfile.write("        stage 1 pass count: " + str(passcount) + "\n")
    #     resultssummaryfile.write("        stage 2 mitigating factor dataset count: " + str(mitigatingfactordatasetcount) + "\n")
    #     resultssummaryfile.write("        stage 3 needs review count: " + str(needsreviewcount) + "\n")
    #     resultssummaryfile.write("        insufficient privileges to process: " + str(insufficientprivilegestoprocesscount) + "\n")



with open("outputs/" + todayDate + "/all_results_summary.txt", "a") as resultssummaryfile:

    totalseconds = int(time.time() - ot)
    m, s = str(int(math.floor(totalseconds/60))), int(round(totalseconds%60))
    if s < 10:
        sstr = "0" + str(s)
    else:
        sstr = str(s)

    resultssummaryfile.write("\n")
    resultssummaryfile.write("   RUN TIME\n")
    resultssummaryfile.write("        minutes elapsed = "+ m + ":" + sstr + "  \n")
    try: #handles if one category of dataset is not processed
        writelog("")
        writelog("PROCESSING COMPLETED SUCCESSFULLY")
        # writelog("      total datasets evaluated: " + str(processedpublisheddatasets) + "\n")
        writelog("      stage 1 pass count: " + str(passcount) + "\n")
        # writelog("      stage 2 mitigating factor dataset count: " + str(mitigatingfactordatasetcount) + "\n")
        writelog("      stage 3 needs review count: " + str(needsreviewcount) + "\n")
        # writelog("      insufficient privileges to process: " + str(insufficientprivilegestoprocesscount) + "\n")
        writelog("")
        writelog("      minutes elapsed = "+ m + ":" + sstr + "  \n")
    except Exception as e:
        pass

#identifying published datasets that you do not have admin privileges to process
if crossvalidate == "True":
    if config['email'] == "Outlook":
        #define search parameters
        sender = "dataverse@tdl.org" #email address TDR uses to send biweekly reports
        subject = "Dataverse reports for"

        #define paths for downloading and importing files to/from
        scriptdirectory = os.path.dirname(os.path.abspath(__file__))
        tdrdataversereports = os.path.join(scriptdirectory, 'tdr-dataverse-reports')
        outputsdirectory = os.path.join(scriptdirectory, 'outputs')

        #default Outlook settings, should work for most accounts
        outlook = win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")
        root_folder = outlook.GetDefaultFolder(6)  #6 = Inbox
        folders_to_search = [root_folder]
        found = False

        while folders_to_search and not found:
            current_folder = folders_to_search.pop(0)
            folders_to_search.extend(list(current_folder.Folders))

            try:
                messages = current_folder.Items
                messages.Sort("[ReceivedTime]", True)  #sort by newest first

                for message in messages:
                    try:
                        if message.Class == 43:  # MailItem
                            if (subject in message.Subject) and (message.SenderEmailAddress == sender):
                                if message.Attachments.Count > 0:
                                    sent_date = message.SentOn.strftime("%Y%m%d")  # Format as YYYYMMDD
                                    for attachment in message.Attachments:
                                        filename = f"{sent_date}_{attachment.FileName}"
                                        attachment.SaveAsFile(os.path.join(tdrdataversereports, filename))
                                    print(f"Saved from: {message.Subject}")
                                found = True
                                break  #stop after first match
                    except Exception as e:
                        print(f"Skipped one item due to error: {e}")
            except Exception as folder_error:
                print(f"Could not access folder: {current_folder.Name} — {folder_error}")

    #import latest dataverse report
    pattern1 = '-dataverse-reports.xlsx'
    dataversereport = loadlatestdataversereport(tdrdataversereports, pattern1)
    dataversereport['doi'] = 'doi:'+ dataversereport['authority'].astype(str) + '/' + dataversereport['identifier'].astype(str)
    print("Data file loaded successfully.")
    draftsall = dataversereport[(dataversereport['versionState'] == "DRAFT") & (dataversereport['viewsUnique'].isnull())] #remove previously published, in draft

    #import latest dataverse report
    pattern2 = 'stage1-passed-unpublished'
    stage1drafts, specificoutputdirectory = loadlatestoutputfile(outputsdirectory, pattern2)
    stage1drafts['stage'] = 'stage1'
    pattern3 = 'stage3-needsreview-unpublished'
    stage3drafts, specificoutputdirectory = loadlatestoutputfile(outputsdirectory, pattern3)
    stage3drafts['stage'] = 'stage3'
    draftssome = pd.concat([stage1drafts, stage3drafts], ignore_index=True)
    print("Data files loaded successfully.")

    draftscombined = pd.merge(draftsall, draftssome, on='doi', how='left')
    draftscombined['admin_privileges'] = np.where(draftscombined['stage'].isnull(), 'No privileges', 'Privileges') #can use any column that is always filled in the outputs file
    draftscombined.to_csv(specificoutputdirectory+f'/{todayDate}-{str(config['institutionaldataverse'])}-drafts-cross-validation.csv')

    ##### IN DEVELOPMENT AS OF 2025-08-18, not tested for functionality #######

    # #set filename
    # publishedadminprivilegescsvpath = "outputs/" + todayDate + "/all-published-admin-privileges-list-" + todayDate + "-" + str(config['institutionaldataverse']) + ".csv"

    # #set CSV header rows
    # publishedadminheaderrow = ["doi","title","author", "author contact email", "latest version state", "date created","date last updated", "date published", "years since creation", "years since last update", "years since publication", "version", "size(GB)", "unique downloads", "citation count", "funding", "exemption notes"]

    # #create output CSV file
    # writerowtocsv(publishedadminprivilegescsvpath,publishedadminheaderrow,"w")

    # writelog("\n\nRETRIEVING PUBLISHED DATASETS FROM MyData ENDPOINT\n\n")
    # ROLE_IDS = str(1) #admin role
    # DVOBJECT_TYPES="Dataset"
    # PUBLISHED_STATES="Published"

    # publishedddatasetcounter = 0
    # currentpageofresults = 0
    # pagecount = config['paginationlimit']
    # pageincrement = config['pageincrement']
    # pagesize = config['pagesize']

    # while currentpageofresults < pagecount:

    #         try:
    #             currentpageofresults += 1

    #             # deaccessionedqueryurl = "https://dataverse.tdl.org/api/mydata/retrieve?role_ids=" + ROLE_IDS + "&dvobject_types=" +DVOBJECT_TYPES + "&published_states=" +PUBLISHED_STATES + "&selected_page=" + str(currentpageofresults)

    #             #substituting search endpoint
    #             publisheddatasetslist = requests.get("https://dataverse.tdl.org/api/mydata/retrieve?role_ids=" + ROLE_IDS + "&dvobject_types=" + DVOBJECT_TYPES + "&published_states=" + PUBLISHED_STATES + "&selected_page=" + str(currentpageofresults), headers={"X-Dataverse-key":config['dataverse_api_key']})

    #             publisheddata = json.loads(publisheddatasetslist.text)['data']
    #             print(publisheddata['start'])

    #             pagecount = publisheddata['pagination']['pageCount']

    #             if currentpageofresults == 1:
    #                 writelog("NUMBER OF PUBLISHED RESULTS: " + str(publisheddata['total_count']))


    #             for publishedddatasetcounter, publisheddatasetinfo in enumerate(json.loads(publisheddatasetslist.text)['data']['items']):

    #                 writelog("#" + str(publishedddatasetcounter) + " DEACCESSIONED DATASET")
    #                 publishedddatasetcounter += 1

    #                 for k,v in publisheddatasetinfo.items():
    #                     writelog("   " + k + ": "+ str(v))

    #                 doi = publisheddatasetinfo['global_id']
    #                 entityid = publisheddatasetinfo['entity_id']
    #                 title = publisheddatasetinfo['name']
    #                 author = str(publisheddatasetinfo['authors'])
    #                 authorcontactemail = ""
    #                 datecreated = str(publisheddatasetinfo['createdAt'])
    #                 datelastupdated = str(publisheddatasetinfo['updatedAt'])
    #                 yearssincecreation = ""
    #                 yearssincelastupdated = ""
    #                 datasetsizevaluegb = ""
    #                 fundinginfo = ""
    #                 datalicense = ""
    #                 latestversionstate = ""
    #                 exemptionnotes = ""
    #                 status = publisheddatasetinfo['versionState']
    #                 deaccessionreason = publisheddatasetinfo['deaccession_reason']

    #                 writelog("\n\n")

    #                 datasetdetailsrow = [doi, title, author, authorcontactemail, latestversionstate, datecreated, datelastupdated, yearssincecreation, yearssincelastupdated, datasetsizevaluegb, fundinginfo, exemptionnotes, status, deaccessionreason]


    #                 writerowtocsv(deaccessionedcsvpath, datasetdetailsrow, "a")


    #         except Exception as e:
    #             writelog(str(e))
    #             break