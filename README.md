# appd_agents_inventory
python script to create analytics dashbaord as well as a csv report for all machine and app agents

![Import Dashboards](agents_inventory_dashbaord.png)
#Step 1
update autConfig.json with your controller access info 
```
{
    "config":
        {
            "host": ".saas.appdynamics.com",
            "port": 443,
            "ssl" : true,
            "account": "",
            "user": "",
            "password": "",
            "applications": ".*",
            "global_account_name": "",
            "analytics_api_key":"",
            "event_service_url":"https://analytics.api.appdynamics.com"
        }
}

```
#Step 2: Create Analytics Custom Schema 
```
curl --location --request POST 'https://analytics.api.appdynamics.com/events/schema/agents_inventory' \
--header 'Content-Type: application/vnd.appd.events+json;v=2' \
--header 'X-Events-API-Key: ' \
--header 'X-Events-API-AccountName: ' \
--data-raw '{
    "schema": {
        "controller_name": "string",
        "application_name": "string",
        "node_name": "string",
        "machine_name": "string",
        "agent_type": "string",
        "agent_version": "string",
        "agent_version_number": "integer"
    }
}'

```

#Step 3: Run the script or schedule it as a cron job
```
python async_Agents_Version.py 
```

#Step 4: Import the custom dashboard saved in this directory into your controller
CustomDashboard_Agents+Inventory_.json