#!/bin/bash

splunk_user="pi"
if [[ "${DCSPLUNKUSER}" != "" ]]; then
    splunk_user="${DCSPLUNKUSER}"
fi
splunk_password="123321"
if [[ "${DCSPLUNKPASSWORD}" != "" ]]; then
    splunk_password="${DCSPLUNKPASSWORD}"
fi

# only get the first token in the list
docker exec -it splunk /bin/bash -c "ps auwwx ; /opt/splunk/bin/splunk http-event-collector list -uri "https://${splunk_user}:${splunk_password}@localhost:8089"" | grep 'token='  | sed -e 's/=/ /g' | awk '{print $NF}' | sed "s/\n//g" | sed "s/\r//g" | head -1

exit 0
