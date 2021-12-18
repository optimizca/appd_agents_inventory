# appd_agents_inventory
python script to create analytics dashbaord as well as a csv report for all machine and app agents

#Step 1
update autConfig.json with your controller access info 

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
        "agent_version": "string"
    }
}'

```

