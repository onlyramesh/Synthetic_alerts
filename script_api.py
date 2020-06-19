#!/usr/bin/python3.8
import os
import requests
import time
from datetime import datetime
import mysql.connector
import config
import slack
import sys
import config
import json
import codecs  

def slack_msg(msg='API alerts',color='#d6170d'):
    client.chat_postMessage(
                                channel="#synthetic-alerts",
                                blocks=[
                                    {
                                        "type": "section",
                                        "text": {
                                            "type": "mrkdwn",
                                            "text": "status"
                                        }
                                    }
                                ],
                            attachments=[
                                { 
                                "fallback": "Required plain-text summary of the attachment.",
                                "color": color,
                                #   "pretext": "Optional text that appears above the attachment block",
                                "author_name": msg
                                }
                            ]   
                        )
SLACK_API_TOKEN=config.slack_token['SLACK_API_TOKEN']
client = slack.WebClient(token=SLACK_API_TOKEN,ssl=False)

mydb = mysql.connector.connect(
    host=config.db_creds['host'],
    user=config.db_creds['username'],
    password=config.db_creds['password'])
cur = mydb.cursor()

msg=""
color=""

# file_path=config.api['path']
file_path='/app/API_list.txt'
res = {}
app_name=""


print("check starts")
while True:
# for i in range(1):
    
    file=open(file_path,'r')
    
    for data in file:
        json_data=""
        print("data is",data)
        api=data.strip('\n').split(',')[0]
        print("api is ",api)
        if(len(api.split("/"))==6):
            type1=api.split("/")[5]
            print(type1)
            app_name=api.split("/")[3]
            print(app_name)
        else:
            type1="Generic"
        
        print(data.strip('\n').split(','))
        time_in_seconds=int(data.strip('\n').split(',')[1])
        res["api"] = api
        today =  datetime.today()
        res["run_date"] = today.timestamp()
        res["api_status"]=0
        res["error_reason"] = None
        res["duration"] = 0
        start_time = time.time() * 1000
        try:
            print("\n")
            resp=requests.get(api,timeout=time_in_seconds)
            json_data=resp.text
            res["status_code"] = resp.status_code

            if resp.status_code == 200:
                res["api_status"] = 1
            else:
                res["api_status"] = 0
                reason = "non 200 code : " +  str(resp.status_code)
                res["error_reason"] = reason
       
        except requests.exceptions.Timeout:
            print("Timeout Error")
            res["api_status"] = 0
            res["status_code"] = 408
            res["error_reason"] = "Timeout Error"
            
        except requests.exceptions.TooManyRedirects:
            print("Too many Redirects")
            res["error_reason"] = "Too many Redirects"
            res["api_status"] = 0
            res["status_code"] = 301
            
        except requests.exceptions.RequestException:
            print("Request Exception")
            res["api_status"] = 0
            res["error_reason"] = "Request Exception"
            res["status_code"] = 400
            

        end_time = time.time() * 1000
        res["duration"]=end_time-start_time

        request_query="select api_id,api_name,api_status,response_code,respons_in_milisec,reason_for_failure,run_date from data12.api_status_checking where api_name="+"'"+res["api"]+"'"+"order by api_id desc limit 1;"
        cur.execute(request_query)
        result=cur.fetchall()
        prev_result = {}
        columns = [column[0] for column in cur.description]
        if len(result) > 1:
            print("More than 1 result returned")
            continue
        elif  len(result) == 0:
            print("No result found in database- inserting ",res["api"])
            insert_to_db="insert into data12.api_status_checking(respons_in_milisec,api_status,run_date,reason_for_failure,response_code,api_name) values ("+str(res["duration"])+","+"'"+str(res["api_status"])+"'"+","+"'"+str(res["run_date"])+"'"+","+"'"+str(res["error_reason"])+"'"+","+str(res["status_code"])+","+"'"+str(res["api"])+"'"+");"
            cur.execute(insert_to_db)
            mydb.commit()
            continue
        else:
            # 1 row returned
            row = result[0]
            prev_result.update(dict(zip(columns, row)))
            
        if (res["api_status"] != int(prev_result["api_status"])):
            # either success to failure
            # or failure to success
            if (res["api_status"] == 0):
        
                # print the failure log content for the API which is being failed
                print("failed API ",res["api"],"json data for failed API request",json_data)
                # print("json data for failed API request",json_data,"api is",res["api"])
                print(res["api"], " : ", res["status_code"], " : ", res["error_reason"], " : ", res["duration"])
                msg=" "+res["api"]+" Failed  \n" +json_data +"\n" +str(res["status_code"])+" status code \n" + str(res["error_reason"])+" Failure reason \n "+str(res["duration"])+" response time \n "
                # print(msg)
                #insert the failed api downtime i.e when it was failed 
                now= datetime.now()
                failed_time=now.strftime("%Y-%m-%d %H:%M:%S")
                print("failed time ",failed_time)
                color="#d6170d"
                slack_msg(msg,color)
                insert_downtime="insert into data12.downtime(api_name,type,app_name,created_at,downtime_at) values("+"'"+api+"'"+","+"'"+type1+"'"+","+"'"+app_name+"'"+",now(),"+"'"+str(failed_time)+"'"+")"
                print(msg)
                cur.execute(insert_downtime)
                mydb.commit()
                
                
            elif(res["api_status"] == 1):
                
                print("was failing - now RECOVERED")
                print(res["api"], " : ", res["status_code"], " : was giving ", prev_result["reason_for_failure"], " : ", res["duration"])
                msg=" "+res["api"]+" Recovered \n"  #+str(res["status_code"])+" status code \n" + str(res["error_reason"])+" Failure reason \n "+str(res["duration"])+" response time \n"
                color="#0dd649"
                slack_msg(msg,color)
                print(msg)
                #following code update the uptime of the failed API
                now= datetime.now()
                up_time=now.strftime("%Y-%m-%d %H:%M:%S")
                print("up time ",up_time)
                get_downtime="select downtime_at from data12.downtime where api_name="+"'"+api+"'"+" order by id desc limit 1;"
                cur.execute(get_downtime)
                downtimeAt = ''
                for i in cur.fetchall():
                    downtimeAt = i[0]
                    #a = *res
                print(downtimeAt," downtime")
                total_downtime="select TIMEDIFF("+"'"+str(up_time)+"'"+","+"'"+str(downtimeAt)+"'"+");"
                cur.execute(total_downtime)
                result=cur.fetchall()
                datetostr=str(result)
                initial = datetostr.find('=')+1
                final = datetostr.find(')',initial)
                var = datetostr[initial:final]
                print(var,"down time in seconds  ")
                update_down_time="update data12.downtime set uptime_at="+"'"+str(up_time)+"',updated_at="+"'"+str(up_time)+"',downtime="+"'"+str(var)+"' where api_name="+"'"+res["api"]+"'order by id desc limit 1;"
                cur.execute(update_down_time)
                mydb.commit()
                print("downtime updated \n")
            else:
                continue      
        else:
            
            # print("status has not changed for ", res["api"])
            msg=" "+res["api"]+" "  #+str(res["status_code"])+" status code \n" + str(res["error_reason"])+" Failure reason \n "+str(res["duration"])+" response time \n"
            print(msg)
           
               
        # make db entry
        insert_to_db="insert into data12.api_status_checking(respons_in_milisec,api_status,run_date,reason_for_failure,response_code,api_name) values ("+str(res["duration"])+","+"'"+str(res["api_status"])+"'"+","+"'"+str(res["run_date"])+"'"+","+"'"+str(res["error_reason"])+"'"+","+str(res["status_code"])+","+"'"+str(res["api"])+"'"+");"
        # print("insert every record")
        cur.execute(insert_to_db)
        mydb.commit()

    print("check ends ")
    # sys.exit()
    time.sleep(150)
   