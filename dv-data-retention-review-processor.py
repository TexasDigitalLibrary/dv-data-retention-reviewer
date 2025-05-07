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
# import datetime
# import pandas as pd

print("all packages imported successfully")



#function for writing new rows to output csv files
def writerowtocsv(outputcsvpath,row,mode):
    with open(outputcsvpath, mode, newline="") as opencsv:
        csvwriter = csv.writer(opencsv)
        csvwriter.writerow(row)


# Open and read config parameters from .env file
configfile = ".env"
with open(configfile) as envfile:
    config = json.loads(envfile.read())


#if outputs directory does not yet exist, create it
if not os.path.isdir("./outputs/" + datetime.now().strftime("%Y-%m-%d")):
    os.mkdir("outputs/" + datetime.now().strftime("%Y-%m-%d"))
    print("outputs/" + datetime.now().strftime("%Y-%m-%d") + " has been created successfully")





#create summary file
with open("outputs/" + datetime.now().strftime("%Y-%m-%d") + "/all_results_summary.txt", "w") as resultssummaryfile:
    resultssummaryfile.write("Results summary " + datetime.now().strftime("%Y-%m-%d") + "\n\n")
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
publishedneedsreviewcsvpath = "outputs/" + datetime.now().strftime("%Y-%m-%d") + "/stage3-needsreview-published-list-" + datetime.now().strftime("%Y-%m-%d") + "-ut-austin.csv"
unpublishedneedsreviewcsvpath = "outputs/" + datetime.now().strftime("%Y-%m-%d") + "/stage3-needsreview-unpublished-list-" + datetime.now().strftime("%Y-%m-%d") + "-ut-austin.csv"
publishedmitigatingfactorcsvpath = "outputs/" + datetime.now().strftime("%Y-%m-%d") + "/stage2-mitigatingfactor-published-list-" + datetime.now().strftime("%Y-%m-%d") + "-ut-austin.csv"
publishednoreviewneededcsvpath = "outputs/" + datetime.now().strftime("%Y-%m-%d") + "/stage1-passed-published-list-" + datetime.now().strftime("%Y-%m-%d") + "-ut-austin.csv"
unpublishednoreviewneededcsvpath = "outputs/" + datetime.now().strftime("%Y-%m-%d") + "/stage1-passed-unpublished-list-" + datetime.now().strftime("%Y-%m-%d") + "-ut-austin.csv"
couldnotbeevaluatedcsvpath = "outputs/" + datetime.now().strftime("%Y-%m-%d") + "/could-not-be-evaluated-" + datetime.now().strftime("%Y-%m-%d") + "-ut-austin.csv"
deaccessionedcsvpath = "outputs/" + datetime.now().strftime("%Y-%m-%d") + "/deaccessioned-" + datetime.now().strftime("%Y-%m-%d") + "-ut-austin.csv"


#set output csv header row column names and write header rows to output csvs
publishedheaderrow = ["doi","title","author", "author contact email", "latest version state", "date deposited","date published", "date distributed", "years since deposit", "years since publication", "years since distribution", "size(GB)", "unique downloads", "citation count", "funding", "exemption notes"]
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
    pagecount = 9999

    while currentpageofresults < pagecount:

        try:
            currentpageofresults += 1

            deaccessionedqueryurl = "https://dataverse.tdl.org/api/mydata/retrieve?role_ids=" + ROLE_IDS + "&dvobject_types=" +DVOBJECT_TYPES + "&published_states=" +PUBLISHED_STATES + "&selected_page=" + str(currentpageofresults)

            writelog(deaccessionedqueryurl)

            deaccessioneddatasetlist = requests.get(deaccessionedqueryurl, headers={"X-Dataverse-key":config['dataverse_api_key']})

            deaccessioneddata = json.loads(deaccessioneddatasetlist.text)['data']

            pagecount = deaccessioneddata['pagination']['pageCount']

            if currentpageofresults == 1:
                writelog("NUMBER OF DEACCESSIONED RESULTS: " + str(deaccessioneddata['pagination']['numResults']))


            for deaccessioneddatasetsprocessedcount, deaccessioneddatasetinfo in enumerate(json.loads(deaccessioneddatasetlist.text)['data']['items']):

                writelog("#" + str(deaccessioneddatasetsprocessedcount) + " DEACCESSIONED DATASET")
                deaccessioneddatasetcounter += 1

                for k,v in deaccessioneddatasetinfo.items():
                    writelog("   " + k + ": "+ str(v))

                doi = deaccessioneddatasetinfo['global_id']
                entityid = deaccessioneddatasetinfo['entity_id']
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


        except Exception as e:
            writelog(str(e))

    with open("outputs/" + datetime.now().strftime("%Y-%m-%d") + "/all_results_summary.txt", "a") as resultssummaryfile:
        resultssummaryfile.write("   DEACCESSIONED DATASETS\n")
        resultssummaryfile.write("        number evaluated: " + str(deaccessioneddatasetcounter) + "\n\n")

writelog("\nFINISHED PROCESSING DEACCESSIONED DATASETS\n\n")









#TRY NEW METHOD TO RETRIEVE INFO ABOUT ALL PUBLISHED DATASETS


writelog("STARTING NEW METHOD TO PROCESS PUBLISHED DATASETS \n\n")


unpublisheddatasetcounter = 0
passcount = 0
needsreviewcount = 0
currentpageofresults = 0
pagecount = 2

while currentpageofresults < pagecount:

    try:
        currentpageofresults += 1

        writelog("https://dataverse.tdl.org/api/search?q=*&subtree=utexas&fq=publicationStatus:Published&type=dataset")

        publisheddatasetlist = requests.get("https://dataverse.tdl.org/api/search?q=*&subtree=utexas&fq=publicationStatus:Published&type=dataset", headers={"X-Dataverse-key":config['dataverse_api_key']})

        publisheddata = json.loads(publisheddatasetlist.text)['data']

        totalresults = publisheddata['total_count']

        for dataset in publisheddata['items']:
            for k,v in dataset.items():
                print(k + ": " + str(v))
        print("\n\n")


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

    except Exception as e:
        print(str(e))







#RETRIEVE INFORMATION ABOUT UNPUBLISHED DATASETS
if config["processunpublisheddatasets"] == "True":

    writelog("STARTING TO PROCESS UNPUBLISHED DATASETS \n\n")

    ROLE_IDS = str(1) #admin role
    DVOBJECT_TYPES="Dataset"
    PUBLISHED_STATES="Unpublished"

    
    unpublisheddatasetcounter = 0
    passcount = 0
    needsreviewcount = 0
    currentpageofresults = 0
    pagecount = 9999

    while currentpageofresults < pagecount:

        try:
            currentpageofresults += 1

            writelog("https://dataverse.tdl.org/api/mydata/retrieve?role_ids=" + ROLE_IDS + "&dvobject_types=" +DVOBJECT_TYPES + "&published_states=" +PUBLISHED_STATES + "&selected_page=" + str(currentpageofresults))

            unpublisheddatasetlist = requests.get("https://dataverse.tdl.org/api/mydata/retrieve?role_ids=" + ROLE_IDS + "&dvobject_types=" + DVOBJECT_TYPES + "&published_states=" + PUBLISHED_STATES + "&selected_page=" + str(currentpageofresults), headers={"X-Dataverse-key":config['dataverse_api_key']})

            unpublisheddata = json.loads(unpublisheddatasetlist.text)['data']

            # writelog(unpublisheddata)

            pagecount = unpublisheddata['pagination']['pageCount']

            if currentpageofresults == 1:
                writelog("NUMBER OF UNPUBLISHED RESULTS ACCESSIBLE UNDER USER ROLE STATUS "+ ROLE_IDS +": " + str(unpublisheddata['pagination']['numResults']))


            for unpublisheddatasetsprocessedcount, unpublisheddatasetinfo in enumerate(unpublisheddata['items']):

            # doi,title,author,author contact email,latest version state,date deposited,date published,date distributed,years since deposit,years since publication,years since distribution,size(GB),unique downloads,citation count,funding,exemption notes

                # writelog("CREATED: " + str(unpublisheddatasetinfo['createdAt']))
                # writelog("UPDATED: " + str(unpublisheddatasetinfo['updatedAt']))
                unpublisheddatasetcounter += 1
                writelog("#" + str(unpublisheddatasetcounter) + " UNPUBLISHED DATASET")
                for k,v in unpublisheddatasetinfo.items():
                    writelog(k + ": "+ str(v))


                doi = unpublisheddatasetinfo['global_id']
                entityid = unpublisheddatasetinfo['entity_id']
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


                try:
                    citationcount = str(len(citations['data']))

                except:
                    citationcount = 0


                # datetimeofmostrecentupdate = datetime.strptime(repo['updated_at'], '%Y-%m-%dT%H:%M:%SZ')

                # monthssincemostrecentupdate = float(relativedelta(datetime.now(), datetime(yearofmostrecentupdate,monthofmostrecentupdate,dayofmostrecentupdate,0,0,0,0)).months)


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


                datasetsizerequest = requests.get("https://dataverse.tdl.org/api/datasets/" + str(entityid) + "/storagesize", headers={"X-Dataverse-key":config['dataverse_api_key']})
                datasizemessage = str(json.loads(datasetsizerequest.text)['data'])
                datasetsizevaluegb = float(int(datasizemessage.split("dataset:")[1].split(" bytes")[0].strip().replace(",","")) / 1000000000)
                writelog("size = " + str(round(datasetsizevaluegb,3) + " GB"))


                datasetinfo = requests.get("https://dataverse.tdl.org/api/datasets/:persistentId/versions/:draft?persistentId=" + doi, headers={"X-Dataverse-key":config['dataverse_api_key']})
                # writelog(json.loads(datasetinfo.text)['data'])
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




        except Exception as e:
            writelog(str(e))


    with open("outputs/" + datetime.now().strftime("%Y-%m-%d") + "/all_results_summary.txt", "a") as resultssummaryfile:
        resultssummaryfile.write("   UNPUBLISHED DATASETS\n")
        resultssummaryfile.write("        number evaluated: " + str(unpublisheddatasetcounter) + "\n")
        resultssummaryfile.write("        stage 1 pass count: " + str(passcount) + "\n")
        resultssummaryfile.write("        stage 1 review count: " + str(needsreviewcount) + "\n\n")


writelog("\n\nFINISHED PROCESSING UNPUBLISHED DATASETS\n\n")


















#ORIGINAL PROCESS TO RETRIEVE INFORMATION ABOUT PUBLISHED DATASETS THAT DOES NOT SUCCESSFULLY FIND ALL DATASETS
if config["processpublisheddatasets"] == "True":

    call = config['dataverse_api_host'] + "/api/info/metrics/uniquedownloads?parentAlias=" + config['institutionaldataverse']
    writelog("data request url = " + call)

    datasetdoianddownloadcountlist = requests.get(call)

    processedpublisheddatasets = 0
    mitigatingfactordatasetcount = 0
    passcount = 0
    needsreviewcount = 0
    insufficientprivilegestoprocesscount = 0
    # writelog(datasetdoianddownloadcountlist.text)



    for datasetsprocessedcount, rawdoianddownloadcount in enumerate(datasetdoianddownloadcountlist.text.split("\n")):

        if datasetsprocessedcount > 0:

            try:

                publishedneedsreview = False
                unpublishedneedsreview = False
                publishednoreviewneeded = False
                unpublishednoreviewneeded = False
                mitigatingfactorpresent = False

                doi = ""
                entityid = ""
                title = ""
                author = ""
                authorcontactemail = ""
                datedeposited = ""
                datepublished = ""
                datedistributed = ""
                yearssincedeposit = ""
                yearssincepublication = ""
                yearssincedistribution = ""
                uniquedownloads = ""
                fundinginfo = ""
                datalicense = ""
                latestversionstate = ""
                exemptionnotes = ""

                # datasetretentionscore = 0
                cleaneddoianddownloadcount = rawdoianddownloadcount.replace("\"","")
                doi = cleaneddoianddownloadcount.split(",")[0]
                uniquedownloads = cleaneddoianddownloadcount.split(",")[1]

                writelog("\n\n\n")
                writelog("#" + str(datasetsprocessedcount) + " Starting to process " + doi)

                processedpublisheddatasets += 1

                citationsrequest = requests.get("https://dataverse.tdl.org/api/datasets/:persistentId/makeDataCount/citations?persistentId=" + doi)
                citations = json.loads(citationsrequest.content.decode("latin-1"))

                datasetgeneralinforequest = requests.get("https://dataverse.tdl.org/api/datasets/:persistentId/?persistentId=" + doi)
                datasetgeneralinforequest= json.loads(datasetgeneralinforequest.content.decode("latin-1"))

                try:
                    latestversionstate = str(datasetgeneralinforequest['data']['latestVersion']['versionState'])
                except Exception as e:
                    writelog(str(e))

                writelog("versionState:  " + str(datasetgeneralinforequest['data']['latestVersion']['versionState']))
                datasetid = str(datasetgeneralinforequest['data']['id'])


                metadatarequest = requests.get("https://dataverse.tdl.org/api/datasets/"+datasetid+"/versions/1.0/metadata", headers={"X-Dataverse-key":config['dataverse_api_key']})
                metadata = json.loads(metadatarequest.content.decode("latin-1"))

                for k,v in metadata['data'].items():
                    try:
                        if len(str(v)) > 50:
                            writelog("   " + k + ":  " + str(v)[:50].replace("\n") + "....")
                        else:
                            writelog("   " + k + ":  " + str(v))
                    except:
                        pass

                # datasetsizerequest = requests.get("https://dataverse.tdl.org/api/datasets/"+datasetid+"/storagesize", headers={"X-Dataverse-key":config['dataverse_api_key']})
                # datasetsize = json.loads(datasetsizerequest.content.decode("latin-1"))

                ispartofdata = metadata['data']['schema:isPartOf']
                dataversehierarchy = []
                spacing = "   "

                
                while ispartofdata['@id'] != 'https://dataverse.tdl.org/dataverse/root':
                    try:
                        dataversehierarchy.append(ispartofdata['schema:name'])
                        writelog(spacing + "is part of " + ispartofdata['schema:name'])
                        spacing += spacing
                        ispartofdata = ispartofdata['schema:isPartOf']
                    except Exception as e:
                        print(str(e))

                try:
                    dataversehierarchy.append('TDR Root')
                    dataversehierarchy.reverse()
                    dataversehierarchy.append("dataset")

                    title = metadata['data']['title']
                    author = metadata['data']['citation:datasetContact']['citation:datasetContactName']
                    authorcontactemail = metadata['data']['citation:datasetContact']['citation:datasetContactEmail']
                except Exception as e:
                    print(str(e))

                # creationyear = int(datecreated.lower().split("t")[0].split("-")[0])
                # creationmonth = int(datecreated.lower().split("t")[0].split("-")[1])
                # creationday = int(datecreated.lower().split("t")[0].split("-")[2])
                #
                # writelog("creationyear = " + str(creationyear))
                # writelog("creationmonth = " + str(creationmonth))
                # writelog("creationday = " + str(creationday))
                #
                # yearssincecreation = float(relativedelta(datetime.now(), datetime(creationyear,creationmonth,creationday,0,0,0,0)).years + (relativedelta(datetime.now(), datetime(creationyear,creationmonth,creationday,0,0,0,0)).months/12) + (relativedelta(datetime.now(), datetime(creationyear,creationmonth,creationday,0,0,0,0)).days/365))
                #
                # writelog("yearssincecreation = " + str(yearssincecreation))
                #
                #
                # lastupdatedyear = int(datecreated.lower().split("t")[0].split("-")[0])
                # lastupdatedmonth = int(datecreated.lower().split("t")[0].split("-")[1])
                # lastupdatedday = int(datecreated.lower().split("t")[0].split("-")[2])
                #
                # writelog("lastupdatedyear = " + str(lastupdatedyear))
                # writelog("lastupdatedmonth = " + str(lastupdatedmonth))
                # writelog("lastupdatedday = " + str(lastupdatedday))
                #
                # yearssincelastupdated = float(relativedelta(datetime.now(), datetime(lastupdatedyear,lastupdatedmonth,lastupdatedday,0,0,0,0)).years + (relativedelta(datetime.now(), datetime(lastupdatedyear,lastupdatedmonth,lastupdatedday,0,0,0,0)).months/12) + (relativedelta(datetime.now(), datetime(creationyear,creationmonth,creationday,0,0,0,0)).days/365))
                #
                # writelog("yearssincelastupdated = " + str(yearssincelastupdated))




                if "University of Texas at Austin Dataverse Collection" not in str(metadata['data']['schema:isPartOf']) and config['institutionaldataverse'] != "*":
                    writelog(spacing + " skipping dataset because it is in not in the " + config['institutionaldataverse'] + " dataverse")


                if str("https://dataverse.tdl.org/dataverse/" + config['institutionaldataverse']) in str(metadata) or config['institutionaldataverse'] == "*":
                    writelog(spacing + " dataset is within a dataverse that is designated for processing, continuing to evaluate dataset...")


                    writelog("   preparing to request dataset size.....")

                    try:
                        datasetsizerequest = requests.get("https://dataverse.tdl.org/api/datasets/" + str(datasetid) + "/storagesize", headers={"X-Dataverse-key":config['dataverse_api_key']})
                        datasizemessage = str(json.loads(datasetsizerequest.text)['data'])
                        datasetsizevaluegb = float(int(datasizemessage.split("dataset:")[1].split(" bytes")[0].strip().replace(",","")) / 1073741824)

                        writelog("   size = " + str(datasetsizevaluegb) + "GB")

                        if config['showdatasetdetails'] == "True":
                            writelog("   Dataset DOI: " + str(doi) + "")
                            writelog("   Dataset ID: " + str(datasetid) + "")
                            writelog("   Unique Downloads: " + uniquedownloads + "")
                            writelog("   Citation Count: " + str(len(citations['data'])) + "")
                            writelog("   Citation List: " + str(citations['data']) + "")
                            writelog("   Corresponding Author Name: " + metadata['data']['citation:datasetContact']['citation:datasetContactName'] + "")
                            writelog("   Corresponding Author Email: " + metadata['data']['citation:datasetContact']['citation:datasetContactEmail'] + "")
                            writelog("   Dataset Size (GB): " + str(round(datasetsizevaluegb,4)) + "")
                            # writelog("   Grant Number(s): " + str(metadata['data']))
                            writelog("   Data Access Restrictions: " + str(metadata['data']['dvcore:fileTermsOfAccess']['dvcore:fileRequestAccess']) + "")

                            try:
                                writelog("   Deposit Date: " + str(metadata['data']['dateOfDeposit']) + "")
                                datedeposited = str(str(metadata['data']['dateOfDeposit']))
                                deposityear = int(metadata['data']['dateOfDeposit'].split("-")[0])
                                depositmonth = int(metadata['data']['dateOfDeposit'].split("-")[1])
                                depositday = int(metadata['data']['dateOfDeposit'].split("-")[2])
                                yearssincepublication = float(relativedelta(datetime.now(), datetime(deposityear,depositmonth,depositday,0,0,0,0)).years + (relativedelta(datetime.now(), datetime(deposityear,depositmonth,depositday,0,0,0,0)).months/12))
                                yearssincepublication = round(yearssincepublication,3)
                                # writelog("   deposityear = " + str(deposityear))
                                # writelog("   depositmonth = " + str(depositmonth))
                                # writelog("   depositday = " + str(depositday))
                                # writelog("   yearssincepublication = " + str(yearssincepublication))
                            except Exception as e:
                                writelog("ERROR: " + str(e) + "\n\n")

                            try:
                                writelog("   Publication Date: " + str(metadata['data']['schema:datePublished']) + "")
                                datepublished = str(metadata['data']['schema:datePublished'])

                            except Exception as e:
                                writelog("   Publication Date: ")
                                datepublished = ""

                            try:
                                writelog("   Distribution Date: " + str(metadata['data']['distributionDate']) + "")
                                datedistributed = str(metadata['data']['distributionDate'])

                            except Exception as e:
                                writelog("   Distribution Date: ")
                                datedistributed = ""


                        # if "ERROR" in str(datasetsizevaluegb):
                        #     input(">>>>")
                        #     datasetsizevaluegb = ""
                        #     datasetdetailsrow = [doi, title, author, authorcontactemail, latestversionstate, datedeposited, datepublished, datedistributed, yearssincedeposit, yearssincepublication, yearssincedistribution, datasetsizevaluegb, uniquedownloads, str(len(citations['data'])), fundinginfo, exemptionnotes]

                        #     writerowtocsv(couldnotbeevaluatedcsvpath, datasetdetailsrow, "a")
                        #     writelog("      ERROR: " + str(datasetsize))
                        #     writelog("      this dataset could not be evaluated because of insufficient privileges to access data size information")



                        # else:
                            # datasetsizevaluegb = int(str(datasetsize).split("dataset:")[1].split(" b")[0].strip().replace(",",""))
                            # datasetsizevaluegb = round((datasetsizevaluegb/1073741824),3)

                            # distributionyear = int(metadata['data']['citation:distributionDate'].split("-")[0])
                            # distributionmonth = int(metadata['data']['citation:distributionDate'].split("-")[1])
                            # distributionday = int(metadata['data']['citation:distributionDate'].split("-")[2])
                            #
                            # writelog("   distributionyear = " + str(distributionyear))
                            # writelog("   distributionmonth = " + str(distributionmonth))
                            # writelog("   distributionday = " + str(distributionday))
                            #
                            # yearssincedistribution = float(relativedelta(datetime.now(), datetime(distributionyear,distributionmonth,distributionday,0,0,0,0)).years + (relativedelta(datetime.now(), datetime(distributionyear,distributionmonth,distributionday,0,0,0,0)).months/12))
                            # writelog("   yearssincedistribution = " + str(yearssincedistribution))


                            # publicationyear = int(metadata['data']['schema:datePublished'].split("-")[0])
                            # publicationmonth = int(metadata['data']['schema:datePublished'].split("-")[1])
                            # publicationday = int(metadata['data']['schema:datePublished'].split("-")[2])
                            #
                            # writelog("   publicationyear = " + str(publicationyear))
                            # writelog("   publicationmonth = " + str(publicationmonth))
                            # writelog("   publicationday = " + str(publicationday))
                            #
                            # yearssincepublication = float(relativedelta(datetime.now(), datetime(publicationyear,publicationmonth,publicationday,0,0,0,0)).years + (relativedelta(datetime.now(), datetime(publicationyear,publicationmonth,publicationday,0,0,0,0)).months/12))
                            # writelog("   yearssincepublication = " + str(yearssincepublication))



                            # if config['showdatasetdetails']:
                            #     writelog()
                            #     for k,v in metadata['data'].items():
                            #         writelog(k, str(v))



                            for k, v in metadata['data'].items():

                                # writelog("      " + k + "\n          " + str(v))

                                if k == "title":
                                    writelog("   " + k + ": " + str(v))
                                if k == "grantNumber":
                                    writelog("   " + k + ": " + str(v))
                                    fundinginfo = str(v)
                                if k == "publication":
                                    writelog("   " + k + ": " + str(v))
                                if k == "dateOfDeposit":
                                    writelog("   " + k + ": " + str(v))
                                if k == "schema:license":
                                    writelog("   " + k + ": " + str(v))
                                    datalicense = str(v)
                                if k == "dvcore:fileTermsOfAccess":
                                    if v['dvcore:fileRequestAccess'] == False:
                                        writelog("   Access Level: Open Access")
                                    else:
                                        writelog("   Access Level: Restricted Access (request must be submitted to access files)")
                                    writelog("  " + k + ": " +  str(v))
                                    
                                if k == "author":
                                    writelog("   Author: " + str(v))
                                if k == "citation:datasetContact":
                                    writelog("   Dataset Contact: " + str(v))
                                if k == "citation:dsDescription":
                                    writelog("   Description Length: " + str(len(v)))




                            if len(citations['data']) >= int(config["mitigatingfactormincitationcount"]):
                                mitigatingfactorpresent = True
                                exemptionnotes += "High citation count; "

                            if int(uniquedownloads) >= int(config["mitigatingfactormindownloadcount"]):
                                mitigatingfactorpresent = True
                                exemptionnotes += "High unique download count; "

                            if len(fundinginfo) > 0:
                                mitigatingfactorpresent = True
                                exemptionnotes += "Funded research; "


                            datasetdetailsrow = [doi, title, author, authorcontactemail, latestversionstate, datedeposited, datepublished, datedistributed, yearssincedeposit, yearssincepublication, yearssincedistribution, datasetsizevaluegb, uniquedownloads, str(len(citations['data'])), fundinginfo, exemptionnotes]


                            writelog("   preparing to determine if dataset needs to be reviewed...")
                            writelog("       years since publication = " + str(yearssincepublication))
                            writelog("       config['publisheddatasetreviewthresholdinyears'] = " + str(config['publisheddatasetreviewthresholdinyears']))
                            writelog("       datasetsizevaluegb = " + str(datasetsizevaluegb))
                            writelog("       config['publisheddatasetreviewthresholdingb'] = " + str(config['publisheddatasetreviewthresholdingb']))

                            try:
                                if float(yearssincepublication) > float(config['publisheddatasetreviewthresholdinyears']) and float(datasetsizevaluegb) > float(config['publisheddatasetreviewthresholdingb']):
                                    publishedneedsreview = True

                                    if mitigatingfactorpresent:
                                        writerowtocsv(publishedmitigatingfactorcsvpath, datasetdetailsrow, "a")
                                        writelog("      THIS DATASET HAS A MITIGATING FACTOR AND DOES NOT NEED TO BE REVIEWED")
                                        mitigatingfactordatasetcount += 1

                                    else:
                                        writerowtocsv(publishedneedsreviewcsvpath, datasetdetailsrow, "a")
                                        writelog("      THIS DATASET NEEDS TO BE REVIEWED")
                                        needsreviewcount += 1

                                else:
                                    publishednoreviewneeded = True
                                    writerowtocsv(publishednoreviewneededcsvpath, datasetdetailsrow, "a")
                                    writelog("      this dataset does not need to be reviewed")
                                    passcount += 1

                            except Exception as e:
                                writelog("        " + str(e))
                                writelog("        " + "STATUS UNKNOWN DUE TO ERROR")


                    except Exception as e:
                        writelog(str(e))
                        writelog("   Dataset is in the UT Austin dataverse but privileges are insufficient for retrieving dataset size")
                        writerowtocsv(couldnotbeevaluatedcsvpath, datasetdetailsrow, "a")
                        insufficientprivilegestoprocesscount += 1




            # author
            # {'citation:authorName': 'Dainer-Best, Justin', 'citation:authorAffiliation': 'University of Texas at Austin', 'authorIdentifierScheme': 'ORCID', 'authorIdentifier': '0000-0002-1868-0337'}
            # citation:dsDescription
            # citation:datasetContact
            # http://creativecommons.org/publicdomain/zero/1.0
            # dvcore:fileTermsOfAccess
            # {'dvcore:fileRequestAccess': False}


                  # publication
                  #     {'publicationCitation': 'Nazmus Sakib & Amit Bhasin (2019) Measuring polarity-based distributions (SARA) of bitumen using simplified chromatographic techniques, International Journal of Pavement Engineering, 20:12, 1371-1384, DOI: 10.1080/10298436.2018.1428972', 'publicationIDType': 'doi', 'publicationIDNumber': '10.1080/10298436.2018.1428972', 'publicationURL': 'https://doi.org/10.1080/10298436.2018.1428972'}


                  # grantNumber
                  #     {'citation:grantNumberAgency': 'NASA', 'citation:grantNumberValue': 'NNX17AG70G'}

            # 130211
            # https://dataverse.tdl.org/dataset.xhtml?persistentId=doi:10.18738/T8/PRAGLR

            # PUBLICATION INFO
            # {"typeName":"publication","multiple":true,"typeClass":"compound","value":[{"publicationCitation":{"typeName":"publicationCitation","multiple":false,"typeClass":"primitive","value":"Harris KM, Hubbard DD, Kuwajima M, Abraham WC, Bourne JN, Bowden JB, Haessly A, Mendenhall JM, Parker PH, Shi B, Spacek J. (2022) Dendritic spine density scales with microtubule number in rat hippocampal dendrites. Neuroscience. https://doi.org/10.1016/j.neuroscience.2022.02.021"},"publicationURL":{"typeName":"publicationURL","multiple":false,"typeClass":"primitive","value":"https://doi.org/10.1016/j.neuroscience.2022.02.021"}}]},

            # GRANT INFO
            # {"typeName":"grantNumber","multiple":true,"typeClass":"compound","value":[{"grantNumberAgency":{"typeName":"grantNumberAgency","multiple":false,"typeClass":"primitive","value":"National Institutes of Health"},"grantNumberValue":{"typeName":"grantNumberValue","multiple":false,"typeClass":"primitive","value":"MH095980"}},{"grantNumberAgency":{"typeName":"grantNumberAgency","multiple":false,"typeClass":"primitive","value":"National Institutes of Health"},"grantNumberValue":
                    # writelog("   Associated Publication: " + "")
                    # writelog("   Associated Grant: " + "")
                    # writelog("   Funder Requirements: " + "")
                    # writelog("   Data Access Restrictions: " + "")
                    # writelog("   Metadata Quality Score: " + "")




            except Exception as e:
                writelog(str(e))

    with open("outputs/" + datetime.now().strftime("%Y-%m-%d") + "/all_results_summary.txt", "a") as resultssummaryfile:
        resultssummaryfile.write("   PUBLISHED DATASETS\n")
        resultssummaryfile.write("        number evaluated: " + str(processedpublisheddatasets) + "\n")
        resultssummaryfile.write("        stage 1 pass count: " + str(passcount) + "\n")
        resultssummaryfile.write("        stage 2 mitigating factor dataset count: " + str(mitigatingfactordatasetcount) + "\n")
        resultssummaryfile.write("        stage 3 needs review count: " + str(needsreviewcount) + "\n")
        resultssummaryfile.write("        insufficient privileges to process: " + str(insufficientprivilegestoprocesscount) + "\n")



with open("outputs/" + datetime.now().strftime("%Y-%m-%d") + "/all_results_summary.txt", "a") as resultssummaryfile:

    totalseconds = int(time.time() - ot)
    m, s = str(int(math.floor(totalseconds/60))), int(round(totalseconds%60))
    if s < 10:
        sstr = "0" + str(s)
    else:
        sstr = str(s)

    resultssummaryfile.write("\n")
    resultssummaryfile.write("   RUN TIME\n")
    resultssummaryfile.write("        minutes elapsed = "+ m + ":" + sstr + "  \n")