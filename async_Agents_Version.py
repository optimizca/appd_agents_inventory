import json
import re
import sys
import csv
from dataclasses import dataclass
import logging

import numpy as np
import requests
import pandas as pd
import math
import aiohttp

from aiohttp import BasicAuth

from requests.adapters import HTTPAdapter


import asyncio


from datetime import datetime
import time

#inputPwd = getpass.getpass("Enter your password")
#controllerPassword = inputPwd
logging.basicConfig(filename='appd_violations_report.log',filemode='w',format='%(asctime)s - %(message)s', level=logging.DEBUG)
CONFIG_FILE = "autConfig.json"
try:
    with open(CONFIG_FILE) as json_file:
        json_file = json.load(json_file)
        data=json_file['config']
        controllerHost = data['host']
        controllerPort = data['port']
        controllerSSL = data['ssl']
        controllerAccount = data['account']
        controllerUser = data['user']
        controllerGlobalAccountName = data['global_account_name']
        analyticsApiKey = data['analytics_api_key']
        eventServiceURL = data['event_service_url']
        inputApplications = data['applications']
        controllerPassword= data['password']




except Exception as e:
    raise e

@dataclass
class ApiError(Exception):
    status_code: int
    message: str

    def __str__(self):
        return f'ApiError(status_code={self.status_code},message={self.message})'


class AppDController:
    def __init__(self, host: str, port: int, ssl: bool, account: str, username: str, password: str,global_account_name: str,analytics_api_key: str,event_service_url: str):
        self.url = f'{"https" if ssl else "http"}://{host}:{port}'
        self.auth = (username + '@' + account, password)
        self.global_account_name = global_account_name
        self.analytics_api_key = analytics_api_key
        self.event_service_url = event_service_url


        self.headers = self.__getControllerAuthHeaders()
        self.params = {'output': 'JSON'}

        s = requests.Session()
        s.mount(host, HTTPAdapter(max_retries=5))

    def __getControllerAuthHeaders(self):
        print(f'AppD-__getControllerAuthHeaders')
        endpoint = self.url + '/controller/auth'
        r = requests.get(url=endpoint, auth=self.auth, params={'action': 'login'})
        try:
            r.raise_for_status()
        except:
            print("~~~~~~~~~~~~~~~~~~~~~")
            logging.exception("Error occurred while connecting to controller")
            #logging.exception(e)

        if r.status_code != 200:
            logging.exception("Error occurred while connecting to controller" + str(r.status_code)+r.text)
            raise ApiError(r.status_code, r.text)

        jsessionid = re.search('JSESSIONID=(\\w|\\d)*', r.headers['Set-Cookie']) \
            .group(0).split('JSESSIONID=')[1]
        xcsrftoken = re.search('X-CSRF-TOKEN=(\\w|\\d)*', r.headers['Set-Cookie']) \
            .group(0).split('X-CSRF-TOKEN=')[1]
        headers = {
            'X-CSRF-TOKEN': xcsrftoken,
            'Cookie': f"JSESSIONID={jsessionid};X-CSRF-TOKEN={xcsrftoken};",
            'Content-Type': 'application/json;charset=UTF-8'
        }
        return headers
    async def getRequest(self, endpoint) :
        debugString = f"Getting request:{endpoint}"
        logging.debug(f"{debugString}")

        async with aiohttp.ClientSession(auth=BasicAuth(self.auth),headers=self.headers) as session:
            try:
                async with session.get(endpoint,ssl=False,raise_for_status=True) as response:
                    logging.debug("getRequest response:")
                    result = await response.json()
                    #print(response.status)

            except Exception as e:
                logging.exception('Error occurred in  getRequest: {} '.format(endpoint+str(e)))
                result = []



        return result
        # return json.loads(response.text)

    async def postRequest(self, endpoint,payload):
        debugString = f"Post request:{endpoint}"
        logging.debug(f"{debugString}")


        async with aiohttp.ClientSession(auth=BasicAuth(self.auth), headers=self.headers) as session:
            try:
                async with session.post(endpoint, ssl=False, raise_for_status=True,data=payload) as response:
                    logging.debug("postRequest response:")
                    result = await response.json()
                    # print(response.status)

            except Exception as e:

                logging.exception('Error occurred in  postRequest: {} '.format(endpoint + str(e)))
                result = []

        return result
        # return json.loads(response.text)
    async def getMachineAgentIds(self,requestPayload):
        gatherFutures = []
        requestUrl = f'{self.url}/controller/restui/agents/list/machine?output=JSON'

        gatherFutures.append(controller.postRequest(requestUrl,requestPayload))
        result = await gatherWithConcurrency(*gatherFutures)
        logging.debug(result)
        if result[0]["data"]:
            return [agent["machineId"] for agent in result[0]["data"]]
        return []
    async def getAppAgentIds(self,requestPayload):
        gatherFutures = []
        requestUrl = f'{self.url}/controller/restui/agents/list/appserver?output=JSON'

        gatherFutures.append(controller.postRequest(requestUrl,requestPayload))
        result = await gatherWithConcurrency(*gatherFutures)
        logging.debug(result)
        if result[0]["data"]:
            return [agent["applicationComponentNodeId"] for agent in result[0]["data"]]
        return []

    async def getMachineAgents(self) :
        debugString = f"Gathering Machine Agents"
        logging.debug(f"{self.url} - {debugString}")
        # get current timestamp in milliseconds
        currentTime = int(round(time.time() * 1000))
        # get the last 24 hours in milliseconds
        last24Hours = currentTime - (1 * 60 * 60 * 1000)
        body = {
            "requestFilter": {"queryParams": {"applicationAssociationType": "ALL"}, "filters": []},
            "resultColumns": [],
            "offset": 0,
            "limit": -1,
            "searchFilters": [],
            "columnSorts": [{"column": "HOST_NAME", "direction": "ASC"}],
            "timeRangeStart": last24Hours,
            "timeRangeEnd": currentTime,
        }
        agentIds = await controller.getMachineAgentIds(json.dumps(body))
        debugString = f"Gathering Machine Agents Agents List"
        allAgents = []
        batch_size = 50
        gatherFutures = []
        for i in range(0, len(agentIds), batch_size):
            logging.debug(f"Batch iteration {int(i / batch_size)} of {math.ceil(len(agentIds) / batch_size)}")
            chunk = agentIds[i: i + batch_size]
            body = {
                "requestFilter": chunk,
                "resultColumns": ["AGENT_VERSION", "APPLICATION_NAMES", "ENABLED"],
                "offset": 0,
                "limit": -1,
                "searchFilters": [],
                "columnSorts": [{"column": "HOST_NAME", "direction": "ASC"}],
                "timeRangeStart": last24Hours,
                "timeRangeEnd": currentTime,
            }
            requestUrl = f'{self.url}/controller/restui/agents/list/machine/ids?output=JSON'
            gatherFutures.append(controller.postRequest(requestUrl, json.dumps(body)))

        result = await gatherWithConcurrency(*gatherFutures)

        for item in result:
            for agent in item["data"]:
                machineAgentAppName=controller.getMachineAgentAppName(result,agent["hostName"],''.join(agent["applicationNames"]))
                outputObj = {"controller_name": controller.url, "application_name": machineAgentAppName,
                             "node_name": agent["hostName"],
                             "machine_name": agent["hostName"], "agent_type": controller.getMachineAgentType(agent["agentVersion"]),
                             "agent_version": agent["agentVersion"]}
                allAgents.append(outputObj)
        #print(allAgents)
        return allAgents
    async def getAppAgents(self) :
        debugString = f"Gathering Machine Agents"
        logging.debug(f"{self.url} - {debugString}")
        # get current timestamp in milliseconds
        currentTime = int(round(time.time() * 1000))
        # get the last 24 hours in milliseconds
        last24Hours = currentTime - (1 * 60 * 60 * 1000)
        body = {
            "requestFilter": {"queryParams": {"applicationAssociationType": "ALL"}, "filters": []},
            "resultColumns": [],
            "offset": 0,
            "limit": -1,
            "searchFilters": [],
            "columnSorts": [{"column": "HOST_NAME", "direction": "ASC"}],
            "timeRangeStart": last24Hours,
            "timeRangeEnd": currentTime,
        }
        agentIds = await controller.getAppAgentIds(json.dumps(body))
        debugString = f"Gathering App  Agents List"
        allAgents = []
        batch_size = 50
        gatherFutures = []
        for i in range(0, len(agentIds), batch_size):
            logging.debug(f"Batch iteration {int(i / batch_size)} of {math.ceil(len(agentIds) / batch_size)}")
            chunk = agentIds[i: i + batch_size]
            body = {
                "requestFilter": chunk,
                "resultColumns": [
                    "HOST_NAME",
                    "AGENT_VERSION",
                    "NODE_NAME",
                    "COMPONENT_NAME",
                    "APPLICATION_NAME",
                    "DISABLED",
                    "ALL_MONITORING_DISABLED",
                ],
                "offset": 0,
                "limit": -1,
                "searchFilters": [],
                "columnSorts": [{"column": "HOST_NAME", "direction": "ASC"}],
                "timeRangeStart": last24Hours,
                "timeRangeEnd": currentTime,
            }
            requestUrl = f'{self.url}/controller/restui/agents/list/appserver/ids?output=JSON'
            gatherFutures.append(controller.postRequest(requestUrl, json.dumps(body)))

        result = await gatherWithConcurrency(*gatherFutures)

        for item in result:
            for agent in item["data"]:
                machineAgentAppName=controller.getMachineAgentAppName(result,agent["hostName"],''.join(agent["applicationName"]))
                outputObj = {"controller_name": controller.url, "application_name": machineAgentAppName,
                             "node_name": agent["nodeName"],
                             "machine_name": agent["hostName"], "agent_type": agent["type"],
                             "agent_version": agent["agentVersion"]}
                allAgents.append(outputObj)
        #print(allAgents)
        return allAgents


    def getMachineAgentAppName(self,mahineAgentsResult,machineName, currentAppName):
        #enrich java machine agent for .NEt with AppName if not associated with an app
        if("-java-MA" in machineName):
            machineHostName=machineName.split('-java-MA')[0]
            if(len(currentAppName))<=0:
                for item in mahineAgentsResult:
                    for agent in item["data"]:
                        if(machineHostName==agent["hostName"]):
                            return ''.join(agent["applicationNames"])


        return currentAppName

    def getMachineAgentType(self,agent_version):
        if agent_version.startswith("Machine Agent"):
            return "machine_agent"
        else:
            return "dotnet_machine_agent"
    def convertAgentVersionToNumber(self,agent_version):
        agent_version_extract=agent_version.split("compatible")[0]
        pattern = r'(\d{1,2}\.\d{1,2}\.\d{1,2})'
        version=re.findall(pattern,agent_version_extract)
        if(len(version)>0):
            l = [int(x, 10) for x in version[0].split('.')]
            l.reverse()
            versionNumber = sum(x * (100 ** i) for i, x in enumerate(l))
            return versionNumber
        return -1



    def write_excel(self,filename, sheetname, dataframe):
        with pd.ExcelWriter(filename, engine='openpyxl', mode='a') as writer:
            workBook = writer.book
            try:
                workBook.remove(workBook[sheetname])
            except:
                print("Worksheet does not exist")
                logging.exception("Worksheet does not exist")
            finally:
                dataframe.to_excel(writer, sheet_name=sheetname, index=False, header=True)
                writer.save()

    async def exportAgentsInventory (self):
        fieldnames = ['controller_name','application_name', 'node_name', 'machine_name', 'agent_type', 'agent_version','agent_version_number']
        machineAgents= await controller.getMachineAgents()
        appAgents = await controller.getAppAgents()
        allAgents=[*machineAgents,*appAgents]

        with open("agents_inventory.csv", mode='w') as csv_output:
            csv_output_writer = csv.writer(csv_output, delimiter=',')
            csv_output_writer.writerow(fieldnames)
            for agent in allAgents:
                agent_version_number=controller.convertAgentVersionToNumber(agent["agent_version"])
                row = [[agent["controller_name"],agent["application_name"],agent["node_name"],
                        agent["machine_name"],agent["agent_type"],agent["agent_version"],agent_version_number]]
                csv_output_writer.writerows(row)
                outputObj = {"controller_name":agent["controller_name"],"application_name": agent["application_name"], "node_name": agent["node_name"],
                             "machine_name": agent["machine_name"],"agent_type": agent["agent_type"],"agent_version": agent["agent_version"],"agent_version_number": agent_version_number}
                OutputJsonList.append(outputObj);
                logging.debug(row)



    def writeToAnalytics(self, eventsData,schemaName):


        analytics_headers = {
            'X-Events-API-AccountName': self.global_account_name,
            'X-Events-API-Key': self.analytics_api_key,
            'Content-type': 'application/vnd.appd.events+json'
        }
        CHUNK_SIZE=1000
        if len(eventsData) > 0:
            chunkedEventsList = list(controller.chunks(eventsData, CHUNK_SIZE))
            for eventsItem in chunkedEventsList:
                eventsDataStr = json.dumps(eventsItem)
                logging.debug(f'AppD-writeToAnalytics')
                #print(eventsDataStr)
                endpoint = f'{self.event_service_url}/events/publish/{schemaName}'
                r = requests.request(method='POST', url=endpoint, data=eventsDataStr, auth=self.auth, headers=analytics_headers)

                if r.status_code >= 400:
                    logging.exception("Error occurred while writing to analytics"+eventsDataStr)

    def chunks(self,lst, n):
        for i in range(0, len(lst), n):
            yield lst[i:i + n]
async def gatherWithConcurrency(*tasks, size: int = 50):
    semaphore = asyncio.Semaphore(size)
    async def semTask(task):
        async with semaphore:
            return await task
    return await asyncio.gather(*[semTask(task) for task in tasks])

logging.info("START")
start = time.time()
controller = AppDController(
    host=controllerHost,
    port=controllerPort,
    ssl=controllerSSL,
    account=controllerAccount,
    username=controllerUser,
    password=controllerPassword,
    global_account_name=controllerGlobalAccountName,
    analytics_api_key=analyticsApiKey,
    event_service_url=eventServiceURL
)
OutputJsonList= []


async def main():
    await controller.exportAgentsInventory()


if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
asyncio.run(main())
controller.writeToAnalytics(OutputJsonList,'agents_inventory')

end = time.time()
total_time = end - start
logging.info("It took {} seconds to get results".format(total_time))
print("It took {} seconds to get results".format(total_time))
logging.info("END")