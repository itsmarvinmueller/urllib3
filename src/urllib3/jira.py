import base64
import datetime
import json
from dataclasses import dataclass

@dataclass
class JIRA_Configuration:
    API_URL: str
    API_TOKEN: str
    USER_EMAIL: str
    DEPRECATION_ISSUE_TYPE_KEY: str
    DEPRECATION_ISSUE_TYPE_ID: str
    PROJECT_KEY: str
    PROJECT_ID: str
    DEPRECATION_URL_FIELD: str
    DEPRECATION_URL_FIELD_NAME: str
    DEPRECATION_HTTP_FIELD: str
    DEPRECATION_HTTP_FIELD_NAME: str
    SUNSET_HTTP_FIELD: str
    SUNSET_HTTP_FIELD_NAME: str
    HTTP_METHOD_FIELD: str
    HTTP_METHOD_FIELD_NAME: str
    DEPRECATED_PARAMETER_FIELD: str
    DEPRECATED_PARAMETER_FIELD_NAME: str
    BASE64_AUTH: str = None

def create_base64_auth(config: JIRA_Configuration) -> JIRA_Configuration:
    """
    Creates the authentication for the jira API.

    :param config: Configuration of the jira integration
    """
    auth_str = f"{config.USER_EMAIL}:{config.API_TOKEN}"
    base64_auth = base64.b64encode(auth_str.encode("ascii"))
    config.BASE64_AUTH = base64_auth.decode("ascii")
    return config

def check_if_issue_exists(config: JIRA_Configuration, deprecation_url: str, http_method: str, deprecated_parameter: list[str] = None, deprecation_datetime: datetime.datetime = None, sunset_datetime: datetime.datetime = None) -> bool:
    """
    Checks if jira issue with the given parameter already exists. If only some deprecated_parameter are missing, they are added and returns true.

    :param config: Configuration of the jira integration
    :param deprecation_url: The URL of the deprecated API
    :param http_method: The HTTP method used to call the deprecated API
    :param deprecated_parameter: The parameter that are deprecated form the HTTP call
    :param deprecation_datetime: A datetime object of the deprecation HTTP header
    :param sunset_datetime: A datetime object of the sunset HTTP header

    :return: A bool whether the issue already exists.
    """

    # Create the header for the HTTP request.
    header = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': "Basic %s" % config.BASE64_AUTH
    }

    # Create new PoolManager for API calls. Import needs to be inside the function to prevent circular imports.
    from .poolmanager import PoolManager
    http = PoolManager()

    # Create base query string to filter the issues, if the same one exists already.
    queryString = f'type = {config.DEPRECATION_ISSUE_TYPE_KEY} AND project = {config.PROJECT_KEY} AND "{config.DEPRECATION_URL_FIELD_NAME.lower()}[url field]" = "{deprecation_url}" AND "{config.HTTP_METHOD_FIELD_NAME.lower()}[short text]" ~ "{http_method.upper()}" AND status != Done'
    
    # Get server datetime/timezone.
    response = http.request("GET", f"{config.API_URL}/3/serverInfo", headers=header)
    server_datetime_string = response.json()["serverTime"]
    server_datetime = datetime.datetime.strptime(server_datetime_string, "%Y-%m-%dT%H:%M:%S.%f%z")
    
    # Add optional filter options.
    if deprecation_datetime:
        deprecation_datetime = deprecation_datetime.astimezone(server_datetime.tzinfo)
        queryString += f' AND "{config.DEPRECATION_HTTP_FIELD_NAME.lower()}[time stamp]" >= "{deprecation_datetime.strftime("%Y-%m-%d %H:%M")}" AND "{config.DEPRECATION_HTTP_FIELD_NAME.lower()}[time stamp]" <= "{deprecation_datetime.strftime("%Y-%m-%d %H:%M")}"'
    if sunset_datetime:
        sunset_datetime = sunset_datetime.astimezone(server_datetime.tzinfo)
        queryString += f' AND "{config.SUNSET_HTTP_FIELD_NAME.lower()}[time stamp]" >= "{sunset_datetime.strftime("%Y-%m-%d %H:%M")}" AND "{config.SUNSET_HTTP_FIELD_NAME.lower()}[time stamp]" <= "{sunset_datetime.strftime("%Y-%m-%d %H:%M")}"'
    if deprecated_parameter == None:
        queryString += f' AND "{config.DEPRECATED_PARAMETER_FIELD_NAME.lower()}[labels]" is EMPTY'

    # Create query parameter for the HTTP request.
    query = {
        'jql': queryString,
        'fields': '*all',
    }

    # Build the url of the jira api endpoint.
    url = f"{config.API_URL}/3/search/jql"

    # Make HTTP call with the given arguments.
    response = http.request("GET", url, fields=query, headers=header)
    response_data = response.json()

    # This block is needed because jql would return the issue if one of the parameter match. This is not what we want, because we want to have all matching. IF this would be posible we would also inspect if the same ticket already exists and add the parameters if they are not existend.
    if not deprecated_parameter or response_data["issues"] == []:
        # Return whether the issue already exists.
        return response_data["issues"] != []
    else: 
        # Same deprecation url and same http-method and if existing deprecation datetime and sunset datetime.
        # If implemented correctly there should be max. one issue with the charackteristics above.
        issue = response_data["issues"][0]
        query_deprecated_parameter = issue["fields"][config.DEPRECATED_PARAMETER_FIELD]
        for param in deprecated_parameter:
            # If the parameter is not already in the issue we add it.
            if param not in query_deprecated_parameter:
                url = f"{config.API_URL}/3/issue/{issue["id"]}"
                payload = json.dumps({
                    "update": { 
                        config.DEPRECATED_PARAMETER_FIELD: [
                            {
                                "add": param
                            }
                        ]}
                    })
                response = http.request("PUT", url, body=payload, headers=header)
        return True

def create_new_jira_issue(config: JIRA_Configuration, deprecation_url: str, http_method: str, deprecated_parameter: list[str] = None, deprecation_datetime: datetime.datetime = None, sunset_datetime: datetime.datetime = None):
    """
    Creates a new jira issue with the given parameter.

    :param config: Configuration of the jira integration
    :param deprecation_url: The URL of the deprecated API
    :param http_method: The HTTP method used to call the deprecated API
    :param deprecated_parameter: The parameter that are deprecated form the HTTP call
    :param deprecation_datetime: A datetime object of the deprecation HTTP header
    :param sunset_datetime: A datetime object of the sunset HTTP header
    """

    header = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': "Basic %s" % config.BASE64_AUTH
    }

    # Create new PoolManager for API calls. Import needs to be inside the function to prevent circular imports.
    from .poolmanager import PoolManager
    http = PoolManager()

    # Create title for the issue
    summaryOperation = f"The API endpoint {deprecation_url} is deprecated."
    summaryParameter = f"At least one parameter of the API endpoint {deprecation_url} is deprecated."
    summary = summaryParameter if deprecated_parameter != None else summaryOperation

    # Create payload for the issue
    payload = json.dumps({
        "fields": {
            config.DEPRECATION_URL_FIELD: deprecation_url, # URL of the deprecated API endpoint
            config.DEPRECATION_HTTP_FIELD: deprecation_datetime.isoformat() if deprecation_datetime else deprecation_datetime, # Deprecation Timestamp
            config.SUNSET_HTTP_FIELD: sunset_datetime.isoformat() if sunset_datetime else sunset_datetime, # Sunset Timestamp
            config.HTTP_METHOD_FIELD: http_method.upper(), # HTTP-Method
            config.DEPRECATED_PARAMETER_FIELD: deprecated_parameter, # Deprecated parameter as label
            "issuetype": {
                "name": config.DEPRECATION_ISSUE_TYPE_KEY # Custom Issue Type for Deprecation
            },
            "project": {
                "key": config.PROJECT_KEY # Project Key
            },
            "summary": summary,
            },
        })
    response = http.request("POST", f"{config.API_URL}/3/issue", body=payload, headers=header)