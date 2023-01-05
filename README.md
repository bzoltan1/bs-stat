# Data mining tool for Open Build Service
The bs-stat.py tool is to browse any available project on a Open Build Service instance and create a list of contributors with various roles.
## Requirements

The tool is a python3 script what imports

* python-dotenv
* osc-tiny
* ldap3
* cached_property
* cachetools
* shelved_cache

The following command installs all the required python libraries:
```
pip install -r requirements.txt
```

## How to use
Create a .env file. The empty_env_template is a good template
The following environment variabls are used by the tool
  
* OBS_USERNAME
  + The username what has access to the OBS instance
* OBS_PASSWORD
  + The password for the username on the build system. Only necessary to set if the OBS instance is using password as authentucation. Shuld be unset if other authentication method is used.
* SSH_KEY_FILE
  + The full path the private ssh key if the build system supports that authentication. Shuld be unset if other authentication method is used.
* PERSON_DETAIL
  + Set only if the tool can look up the real user name in an LDAP server. By default is should be false.
* LDAP_SERVER_URI
  + URL for ldap queries in 'ldap://some.host' format. 
* SEARCH_BASE
  + The base for the LDAP search in 'OU=stuff,DC=some,DC=foo,DC=bar' format
* API_URL
  + The URL for the OBS api server in 'https://your.api.server.hostname' format
* PROJECT
  + The project to scan and get information. For example 'openSUSE:Factory'
