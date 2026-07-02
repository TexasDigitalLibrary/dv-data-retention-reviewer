import os
import sys
import json
import csv
import shutil
import requests
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import time
import math
import numpy as np
import pandas as pd


if sys.platform == "darwin":
    pass

if sys.platform == "linux":
    pass

# certain functionality in this scripted process can currently only run on the Windows operating system
if sys.platform == "win32":
    import win32com.client


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
    leveltime = ct-timeprintlist[-1]
    timeprintlist.append(ct)
    timestoprocess = [leveltime, totaltime]
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
        print(f"ERROR: could not successfully write to log file ({e})")


writelog("all packages imported successfully")


# Open and read config parameters from .env file
with open(".env", "r") as configfile:
    config = json.loads(configfile.read())


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
        writelog(f"No file with '{pattern}' was found in '{tdrdataversereports}'.")
        return None

    else:
        file_path = os.path.join(tdrdataversereports, latest_file)
        df = pd.read_excel(file_path, sheet_name='datasets', engine='openpyxl')
        writelog(f"The most recent file '{latest_file}' has been loaded successfully.")
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
                writelog(f"The most recent file '{file}' from folder '{recent_folder}' has been loaded successfully.")
                return df, folder_path

    writelog(f"No file with '{pattern}' was found in any subfolder of '{directory}'.")
    return None

#function to indent text
def singletab(text, indent="   "):
    return '\n'.join([indent + line for line in text.split('\n')])

def doubletab(text):
    indent = "\t\t"  # Two tab characters
    return '\n'.join([indent + line for line in text.split('\n')])



#define whether to run in test mode
if config['test']:
    subset = 10
    writelog(f"only testing with the first {subset} records")


#if tdr-dataverse-reports directory does not yet exist, create it
if not os.path.isdir("tdr-dataverse-reports"):
    os.mkdir("tdr-dataverse-reports")

#if outputs directory does not yet exist, create it
if not os.path.isdir("outputs"):
    os.mkdir("outputs")

#if outputs directory does not yet exist, create it
if not os.path.isdir(f"./outputs/{todayDate}"):
    os.mkdir(f"outputs/{todayDate}")
    writelog(f"outputs/{todayDate} has been created successfully")





#create summary file
with open("outputs/" + todayDate + "/all_results_summary.txt", "w") as resultssummaryfile:
    resultssummaryfile.write(f"Results summary {todayDate}\n\n")
    resultssummaryfile.write(singletab("REVIEW CRITERIA") + "\n")
    resultssummaryfile.write(doubletab("UNPUBLISHED DATA years since created = ") + str(config['unpublisheddatasetreviewthresholdinyears']) +"  \n")
    resultssummaryfile.write(doubletab("UNPUBLISHED DATA dataset size threshold = ")+ str(config['unpublisheddatasetreviewthresholdingb']) +"  \n")
    resultssummaryfile.write(doubletab("PUBLISHED DATA years since published = ") + str(config['publisheddatasetreviewthresholdinyears']) +"\n")
    resultssummaryfile.write(doubletab("PUBLISHED DATA dataset size threshold = ") + str(config['publisheddatasetreviewthresholdingb']) +"  \n")
    resultssummaryfile.write(doubletab("PUBLISHED DATA mitigating factor minimum downloads = ") + str(config['mitigatingfactormindownloadcount']) +"\n")
    resultssummaryfile.write(doubletab("PUBLISHED DATA mitigating factor: minimum citations = ") + str(config['mitigatingfactormincitationcount']) +"  \n\n")
    resultssummaryfile.write(doubletab("CROSSVALIDATION PERFORMED: ") + str(config['crossvalidate']) +"  \n\n")


#set initial counts to 0
totaldatasetsindataverse = 0
totaldatasetsindataverseovertenyearsold = 0
totaldatasetsindataverseoveroverfivegb = 0
totaldatasetsindataverseovertenyearsoldandoverfivegb = 0


#define file paths for all output CSV files
publishedneedsreviewcsvpath = "outputs/" + todayDate + "/level3-needsreview-published-list-" + todayDate + "-" + str(config['institutionaldataverse']) + ".csv"
unpublishedneedsreviewcsvpath = "outputs/" + todayDate + "/level3-needsreview-unpublished-list-" + todayDate + "-" + str(config['institutionaldataverse']) + ".csv"
publishedmitigatingfactorcsvpath = "outputs/" + todayDate + "/level2-mitigatingfactor-published-list-" + todayDate + "-" + str(config['institutionaldataverse']) + ".csv"
publishednoreviewneededcsvpath = "outputs/" + todayDate + "/level1-passed-published-list-" + todayDate + "-" + str(config['institutionaldataverse']) + ".csv"
unpublishednoreviewneededcsvpath = "outputs/" + todayDate + "/level1-passed-unpublished-list-" + todayDate + "-" + str(config['institutionaldataverse']) + ".csv"
couldnotbeevaluatedcsvpath = "outputs/" + todayDate + "/could-not-be-evaluated-" + todayDate + "-" + str(config['institutionaldataverse']) + ".csv"
deaccessionedcsvpath = "outputs/" + todayDate + "/deaccessioned-" + todayDate + "-" + str(config['institutionaldataverse']) + ".csv"


#set output csv header row column names and write header rows to output csvs
publishedheaderrow = ["doi","title","author", "author contact email", "latest version state", "date created","date last updated", "date published", "years since creation", "years since last update", "years since publication", "version", "size(GB)", "unique downloads", "citation count", "funding", "exemption notes"]
unpublishedheaderrow = ["doi","title","author", "author contact email", "latest version state", "date created", "date last updated", "years since creation", "years since last update", "size(GB)", "funding", "exemption notes"]
deaccessionedheaderrow = ["doi","title","author", "author contact email", "latest version state", "date created", "date last updated", "years since creation", "years since last update", "size(GB)", "funding", "exemption notes", "status", "deaccession reason"]


#create output CSV files if config file indicates they should be created
if config["processunpublisheddatasets"]:
    writerowtocsv(unpublishedneedsreviewcsvpath,unpublishedheaderrow,"w")
    writerowtocsv(unpublishednoreviewneededcsvpath,unpublishedheaderrow,"w")

if config["processpublisheddatasets"]:
    writerowtocsv(publishedneedsreviewcsvpath,publishedheaderrow,"w")
    writerowtocsv(publishednoreviewneededcsvpath,publishedheaderrow,"w")
    writerowtocsv(publishedmitigatingfactorcsvpath,publishedheaderrow,"w")

if config["processdeaccessioneddatasets"]:
    writerowtocsv(deaccessionedcsvpath,deaccessionedheaderrow,"w")

writerowtocsv(couldnotbeevaluatedcsvpath,publishedheaderrow,"w")




writelog("Starting TDR Data Retention review process at " + datetime.now().strftime("%Y-%m-%d__%H:%M:%S"))

writelog("all major script parameters defined successfully\n")





#RETRIEVE INFORMATION ABOUT DEACCESSIONED DATASETS
if config["processdeaccessioneddatasets"]:
    writelog("STARTING TO PROCESS DEACCESSIONED DATASETS")
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

        try:
            deaccessioneddata = json.loads(deaccessioneddatasetlist.text)['data']

        except Exception as e:
            writelog(str(e) + "\n")
            writelog(deaccessioneddatasetlist.text + "\n")
            writelog("Error returning results - check to make sure that API key is valid in .env." + "\n")
            input("To ignore error and proceed, press any key to continue..." + "\n")

        writelog("NUMBER OF DEACCESSIONED RESULTS: " + str(deaccessioneddata['total_count']))

        writelog(f"Retrieving {len(deaccessioneddata['items'])} {PUBLISHED_STATES} datasets...\n")

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
        resultssummaryfile.write(singletab("DEACCESSIONED DATASETS") + "\n")
        resultssummaryfile.write(doubletab("number of DEACCESSIONED datasets evaluated: ") + str(deaccessioneddatasetcounter) + "\n\n")


    writelog("\nFINISHED PROCESSING DEACCESSIONED DATASETS\n\n")









#TRY NEW METHOD TO RETRIEVE INFO ABOUT ALL PUBLISHED DATASETS

if config["processpublisheddatasets"]:
    writelog("STARTING TO PROCESS PUBLISHED DATASETS \n\n")
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

    if config['test']:
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

            try:
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

                try:
                    latestversionstate = current_version.get('latestVersionPublishingState')
                    writelog("latestversionstate = " + str(latestversionstate))
                except Exception as e:
                    writelog("ERROR: latestVersionPublishingState information could not be retrieved")
                    writelog("ERROR: " + str(e))



                writelog("starting to check for mitigating factors...")
                mitigatingfactorpresent = False

                try:
                    writelog("starting to retrieve citation count data...")
                    citationsrequest = requests.get("https://dataverse.tdl.org/api/datasets/:persistentId/makeDataCount/citations?persistentId=" + doi)
                    writelog(citationsrequest.content.decode("latin-1"))

                    citationsresponse = json.loads(citationsrequest.content.decode("latin-1"))

                    try:
                        citations = str(citationsresponse["data"]["citations"])

                    except Exception as e:
                        writelog("ERROR: citations information could not be be derived from JSON response, value set to 0 by default")
                        citations = "0"

                    if int(totalcitations) > int(config['mitigatingfactormincitationcount']):
                        mitigatingfactorpresent = True

                except Exception as e:
                    totalcitations = "0"
                    writelog("GENERAL ERROR: citation information could not be retrieved from https://dataverse.tdl.org/api/datasets/:persistentId/makeDataCount/citations?persistentId=" + doi)
                    writelog("   SPECIFIC ERROR: " + str(e))



                try:
                    writelog("starting to retrieve unique download count data...")
                    uniquedownloadsrequest = requests.get("https://dataverse.tdl.org/api/datasets/:persistentId/makeDataCount/downloadsUnique?persistentId=" + doi)

                    writelog(uniquedownloadsrequest.content.decode("latin-1"))
                    uniquedownloadsresponse = json.loads(uniquedownloadsrequest.content.decode("latin-1"))

                    try:
                        uniquedownloads = str(uniquedownloadsresponse["data"]["downloadsUnique"])

                    except Exception as e:
                        writelog("ERROR: uniquedownloads information could not be be derived from JSON response, value set to 0 by default")
                        uniquedownloads = "0"

                    if int(uniquedownloads) > int(config['mitigatingfactormindownloadcount']):
                        mitigatingfactorpresent = True

                except Exception as e:
                    uniquedownloads = "0"
                    writelog("GENERAL ERROR: uniquedownloads information could not be retrieved from https://dataverse.tdl.org/api/datasets/:persistentId/makeDataCount/downloadsUnique?persistentId=" + doi)
                    writelog("   SPECIFIC ERROR: " + str(e))

            except Exception as e:
                writelog("ERROR: " + str(e))


            try:
                datasetdetailsrow = [doi, title, author, authorcontactemail, latestversionstate, datecreated, datelastupdated, datepublished, yearssincecreation, yearssincelastupdated, yearssincepublished, version, datasetsizevaluegb, uniquedownloads, totalcitations, fundinginfo, exemptionnotes]

                #published dataset is in compliance with dataset retention criteria because it is smaller than size threshold and below years since creation threshold (level 1)
                if yearssincelastupdated < float(config['publisheddatasetreviewthresholdinyears']) and datasetsizevaluegb < float(config['publisheddatasetreviewthresholdingb']):
                    writerowtocsv(publishednoreviewneededcsvpath, datasetdetailsrow, "a")
                    passcount += 1


                #published dataset is NOT in compliance with dataset retention criteria because it is larger than size threshold and over years since creation threshold (level 1)
                else:

                    #published dataset is out of compliance, but has mitigating factors (level 2)
                    if mitigatingfactorpresent:
                        writerowtocsv(publishedmitigatingfactorcsvpath,publishedheaderrow,"a")

                    else:
                        #published dataset is out of compliance, has no mitigating factors, and needs full review (level 3)
                        writerowtocsv(publishedneedsreviewcsvpath, datasetdetailsrow, "a")
                        needsreviewcount += 1

            except Exception as e:
                writelog("ERROR: " + str(e))


            writelog("\n\n")


    with open("outputs/" + todayDate + "/all_results_summary.txt", "a") as resultssummaryfile:
        resultssummaryfile.write(singletab("PUBLISHED DATASETS") + "\n")
        resultssummaryfile.write(doubletab("number evaluated: ") + str(publisheddatasetcounter) + "\n")
        resultssummaryfile.write(doubletab("count of PUBLISHED datasets in full data retention compliance (level 1): ") + str(passcount) + "\n")
        resultssummaryfile.write(doubletab("count of PUBLISHED datasets out of compliance but with mitigating factors (level 2): ") + str(needsreviewcount) + "\n\n")
        resultssummaryfile.write(doubletab("count of PUBLISHED datasets out of compliance and needing review (level 3): ") + str(needsreviewcount) + "\n\n")

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
if config["processunpublisheddatasets"]:


    writelog("STARTING TO PROCESS UNPUBLISHED DATASETS \n")

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

    if config['test']:
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

        try:
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
        except Exception as e:
            writelog("ERROR: " + str(e))
        writelog("\n\n")



    with open("outputs/" + todayDate + "/all_results_summary.txt", "a") as resultssummaryfile:
        resultssummaryfile.write(singletab("UNPUBLISHED DATASETS") + "\n")
        resultssummaryfile.write(doubletab("number evaluated: ") + str(unpublisheddatasetcounter) + "\n")
        resultssummaryfile.write(doubletab("count of UNPUBLISHED datasets in full data retention compliance (level 1): ") + str(passcount) + "\n")
        resultssummaryfile.write(doubletab("count of UNPUBLISHED datasets out of compliance and needing review (level 3): ") + str(needsreviewcount) + "\n\n")


    writelog("\n\nFINISHED PROCESSING UNPUBLISHED DATASETS\n\n")








#identifying published datasets that you do not have admin privileges to process
if config['crossvalidate'] and sys.platform == "win32":
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

    #import latest API outputs of DRAFT datasets
    pattern2 = 'level1-passed-unpublished'
    level1drafts, specificoutputdirectory = loadlatestoutputfile(outputsdirectory, pattern2)
    level1drafts['level'] = 'level1'
    pattern3 = 'level3-needsreview-unpublished'
    level3drafts, specificoutputdirectory = loadlatestoutputfile(outputsdirectory, pattern3)
    level3drafts['level'] = 'level3'
    draftssome = pd.concat([level1drafts, level3drafts], ignore_index=True)
    print("Data files loaded successfully.")

    draftscombined = pd.merge(draftsall, draftssome, on='doi', how='left')
    draftscombined['admin_privileges'] = np.where(draftscombined['level'].isnull(), 'No privileges', 'Privileges') #can use any column that is always filled in the outputs file
    draftscombined.to_csv(specificoutputdirectory+f'/{todayDate}-{str(config['institutionaldataverse'])}-drafts-cross-validation.csv')

    ##### IN DEVELOPMENT AS OF 2025-08-18, not tested for functionality #######

    #import latest API outputs of DRAFT datasets
    ##get previously published ones in draft status now
    tempdrafts = dataversereport[(dataversereport['versionState'] == "DRAFT") & (dataversereport['viewsUnique'].notnull())]
    ##API outputs of published datasets assigned to different levels
    pattern4 = 'level1-passed-published'
    level1published, specificoutputdirectory = loadlatestoutputfile(outputsdirectory, pattern4)
    level1published['level'] = 'level1'
    pattern5 = 'level2-mitigatingfactor-published'
    level2published, specificoutputdirectory = loadlatestoutputfile(outputsdirectory, pattern5)
    level2published['level'] = 'level2'
    pattern6 = 'level3-needsreview-published'
    level3published, specificoutputdirectory = loadlatestoutputfile(outputsdirectory, pattern6)
    level3published['level'] = 'level3'
    publishedall = pd.concat([level1published, level2published, level3published, tempdrafts], ignore_index=True)
    print("Data files loaded successfully.")

    #set filename
    publishedadminprivilegescsvpath = "outputs/" + todayDate + "/all-published-admin-privileges-list-" + todayDate + "-" + str(config['institutionaldataverse']) + ".csv"

    #set CSV header rows
    # publishedadminheaderrow = ["doi","title","author", "author contact email", "latest version state", "date created","date last updated", "date published", "years since creation", "years since last update", "years since publication", "version", "size(GB)", "unique downloads", "citation count", "funding", "exemption notes"]
    publishedadminheaderrow = ["doi","title","author", "date created","date last updated", "version"]

    #create output CSV file
    writerowtocsv(publishedadminprivilegescsvpath,publishedadminheaderrow,"w")

    writelog("\n\nRETRIEVING PUBLISHED DATASETS FROM MyData ENDPOINT\n\n")
    ROLE_IDS = str(1) #admin role
    DVOBJECT_TYPES="Dataset"
    PUBLISHED_STATES="Published"

    publishedddatasetcounter = 0
    currentpageofresults = 0
    pagecount = config['paginationlimit']
    pageincrement = config['pageincrement']
    pagesize = config['pagesize']

    while currentpageofresults < pagecount:

            try:
                currentpageofresults += 1

                # deaccessionedqueryurl = "https://dataverse.tdl.org/api/mydata/retrieve?role_ids=" + ROLE_IDS + "&dvobject_types=" +DVOBJECT_TYPES + "&published_states=" +PUBLISHED_STATES + "&selected_page=" + str(currentpageofresults)

                #substituting search endpoint
                publisheddatasetslist = requests.get("https://dataverse.tdl.org/api/mydata/retrieve?role_ids=" + ROLE_IDS + "&dvobject_types=" + DVOBJECT_TYPES + "&published_states=" + PUBLISHED_STATES + "&selected_page=" + str(currentpageofresults), headers={"X-Dataverse-key":config['dataverse_api_key']})

                publisheddata = json.loads(publisheddatasetslist.text)['data']
                print(publisheddata['start'])

                pagecount = publisheddata['pagination']['pageCount']

                if currentpageofresults == 1:
                    writelog("NUMBER OF PUBLISHED RESULTS: " + str(publisheddata['total_count']))


                for publishedddatasetcounter, publisheddatasetinfo in enumerate(json.loads(publisheddatasetslist.text)['data']['items']):

                    writelog("#" + str(publishedddatasetcounter) + " PUBLISHED DATASET")
                    publishedddatasetcounter += 1

                    for k,v in publisheddatasetinfo.items():
                        writelog("   " + k + ": "+ str(v))

                    doi = publisheddatasetinfo['global_id']
                    # entityid = unpublisheddatasetinfo['entity_id'] #only for MyData endpoint
                    title = publisheddatasetinfo['name']
                    author = str(publisheddatasetinfo['authors'])
                    # authorcontactemail = ""
                    datecreated = str(publisheddatasetinfo['createdAt'])
                    datelastupdated = str(publisheddatasetinfo['updatedAt'])
                    # datepublished = ""
                    # yearssincecreation = ""
                    # yearssincelastupdated = ""
                    # yearssincepublished = ""
                    major = publisheddatasetinfo['majorVersion']
                    minor = publisheddatasetinfo['minorVersion']
                    version = float(f"{major}.{minor}")
                    # datasetsizevaluegb = ""
                    # uniquedownloads = ""
                    # totalcitations = ""
                    # fundinginfo = ""
                    # datalicense = ""
                    # latestversionstate = ""
                    # exemptionnotes = ""

                    writelog("\n\n")

                    # datasetdetailsrow = [doi, title, author, authorcontactemail, latestversionstate, datecreated, datelastupdated, datepublished, yearssincecreation, yearssincelastupdated, yearssincepublished, version, datasetsizevaluegb, uniquedownloads, totalcitations, fundinginfo, exemptionnotes]

                    #restricting headers (not repeating Native API call)
                    datasetdetailsrow = [doi, title, author, datecreated, datelastupdated, version]

                    writerowtocsv(publishedadminprivilegescsvpath, datasetdetailsrow, "a")


            except Exception as e:
                writelog(str(e))
                break

    #read the CSV back in
    pattern7 = 'all-published-admin-privileges'
    adminpublished, specificoutputdirectory = loadlatestoutputfile(outputsdirectory, pattern7)

    publishedcombined = pd.merge(publishedall, adminpublished, on='doi', how='left')
    publishedcombined['admin_privileges'] = np.where(publishedcombined['version_y'].isnull(), 'No privileges', 'Privileges') #can use any column that is always filled in the file that was just created but be aware you may need to add '_y' if the same column appears twice
    publishedcombined.to_csv(specificoutputdirectory+f'/{todayDate}-{str(config['institutionaldataverse'])}-published-cross-validation.csv')






with open("outputs/" + todayDate + "/all_results_summary.txt", "a") as resultssummaryfile:

    totalseconds = int(time.time() - ot)
    m, s = str(int(math.floor(totalseconds/60))), int(round(totalseconds%60))
    if s < 10:
        sstr = "0" + str(s)
    else:
        sstr = str(s)

    if config['crossvalidate']:
        resultssummaryfile.write("\n")
        resultssummaryfile.write(singletab("USER ADMIN PRIVILEGES") + "\n")
        unpublishedcounts = draftscombined['admin_privileges'].value_counts()
        resultssummaryfile.write('Admin privileges for unpublished datasets:\n')
        resultssummaryfile.write(doubletab(unpublishedcounts.to_string()) + "\n\n")
        publishedcounts = publishedcombined['admin_privileges'].value_counts()
        resultssummaryfile.write('Admin privileges for published datasets:\n')
        resultssummaryfile.write(doubletab(publishedcounts.to_string()) + "\n\n")

    resultssummaryfile.write("\n")
    resultssummaryfile.write(singletab("RUN TIME") + "\n")
    resultssummaryfile.write(doubletab("minutes elapsed = ")+ m + ":" + sstr + "  \n")
    try: #handles if one category of dataset is not processed
        writelog("")
        writelog("PROCESSING COMPLETED SUCCESSFULLY")
        writelog("")
        writelog(singletab("minutes elapsed = ")+ m + ":" + sstr + "  \n")

    except Exception as e:
        writelog("ERROR: " + str(e))
