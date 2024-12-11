from .jira import JIRA_Configuration
from .slack import Slack_Configuration
import datetime
import logging
from dataclasses import dataclass


@dataclass
class Logging_Configuration:
    lvl = logging.DEBUG
    file: str = "deprecation.log"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    logger: logging.Logger = None

DEPRECATION_DETECTION_ENABLED = False
CUSTOM_HTTP_DEPRECATION_HEADER = []
LOGGING_DEPRECATION_CONFIGURATION = None
SLACK_DEPRECATION_CONFIGURATION = None
JIRA_DEPRECATION_CONFIGURATION = None

def is_operation_deprecated(oas: dict[str, str], path: str, method: str) -> bool:
    """
    This method checks whether an operation is deprecated, for an OpenAPI specifiaction.

    :param oas: 
        The OpenAPI specification in json format.
    :param path:
        The path of the operation. This needs the slash at the beginning.
    :param method:
        The method which is used to call this operation. It is irrelevant if it is lowercase or uppercase.

    :return:
        Returns a bool whether the operation is deprecated.
    """
    if path not in oas["paths"]:
        raise KeyError(f"Path {path} not found in the OpenAPI specification.")
    
    if method.lower() not in oas["paths"][path]:
        raise KeyError(f"Method {method.upper()} for path {path} not found in the OpenAPI specification.")
    
    if "deprecated" not in oas["paths"][path][method.lower()]:
        return False
    
    return oas["paths"][path][method.lower()]["deprecated"]

def are_parameter_deprecated(oas: dict[str, str], path: str, method: str, parameter: list[str]) -> tuple[bool, list[str]]:
    """
    This method checks whether any parameter of an operation is deprecated, for an OpenAPI specifiaction.

    :param oas: 
        The OpenAPI specification in json format.
    :param path:
        The path of the operation. This needs the slash at the beginning.
    :param method:
        The method which is used to call this operation. It is irrelevant if it is lowercase or uppercase.
    :param parameter:
        The parameter which are used to call this operation.

    :return:
        Returns a tuple containing a bool whether parameter are deprecated and a list of parameter that are deprecated.
    """
    if path not in oas["paths"]:
        raise KeyError(f"Path {path} not found in the OpenAPI specification.")
    
    if method.lower() not in oas["paths"][path]:
        raise KeyError(f"Method {method.upper()} for path {path} not found in the OpenAPI specification.")
    
    if "parameters" not in oas["paths"][path][method.lower()]:
        raise KeyError(f"No parameters found for {path} with method {method.upper()} in the OpenAPI specification.")
    
    deprecatedParams = []
    for parameter_object in oas["paths"][path][method.lower()]["parameters"]:
        if "deprecated" in parameter_object and parameter_object["deprecated"] and parameter_object["name"] in parameter and parameter_object["in"] == "query":
            deprecatedParams.append(parameter_object["name"])
    
    return (deprecatedParams != [], deprecatedParams)

def set_deprecation_notification(logging = None, slack: Slack_Configuration = None, jira: JIRA_Configuration = None) -> None:
    """
    Sets the configuration for the notifications that are send, when a depreaction is detected.

    :param logging: Sets the logging configuration
    :param slack: Sets the slack configuration
    :param jira: Sets the jira configuration
    """
    global LOGGING_DEPRECATION_CONFIGURATION, SLACK_DEPRECATION_CONFIGURATION, JIRA_DEPRECATION_CONFIGURATION
    if logging:
        LOGGING_DEPRECATION_CONFIGURATION = logging
    if slack:
        SLACK_DEPRECATION_CONFIGURATION = slack
    if jira:
        JIRA_DEPRECATION_CONFIGURATION = jira

def set_deprecation_http_header(http_header: list[str]) -> None:
    """
    Set the header fields that should be used to detect deprecation. "sunset" and "deprecation" are always used.

    :param http_header: A list of header names that should be used.
    """
    global CUSTOM_HTTP_DEPRECATION_HEADER
    CUSTOM_HTTP_DEPRECATION_HEADER = http_header

def add_deprecation_http_header(http_header: list[str]) -> None:
    """
    Add header fields, to existing ones that should be used to detect deprecation. "sunset" and "deprecation" are always used.

    :param http_header: A list of header names that should be used and extend the already existing ones.
    """
    global CUSTOM_HTTP_DEPRECATION_HEADER 
    CUSTOM_HTTP_DEPRECATION_HEADER.extend(http_header)

def deprecation_detection(enabled: bool) -> None:
    """
    Enables or disables the deprecation detection.

    :param enabled: Boolean whether or not the deprecation detection should be performed.
    """
    global DEPRECATION_DETECTION_ENABLED
    DEPRECATION_DETECTION_ENABLED = enabled

def get_deprecation_detection() -> bool:
    """
    Returns whether deprecation detection is enabled or not.
    """
    global DEPRECATION_DETECTION_ENABLED
    return DEPRECATION_DETECTION_ENABLED

def create_log(config: Logging_Configuration, deprecation_url: str, http_method: str, deprecated_parameter: list[str] = None, deprecation_datetime: datetime.datetime = None, sunset_datetime: datetime.datetime = None) -> None:
    """
    Creates a new log message with the given informations.

    :param config: Configuration of the logger
    :param deprecation_url: The URL of the deprecated API
    :param http_method: The HTTP method used to call the deprecated API
    :param deprecated_parameter: The parameter that are deprecated form the HTTP call
    :param deprecation_datetime: A datetime object of the deprecation HTTP header
    :param sunset_datetime: A datetime object of the sunset HTTP header
    """
    # Create logger on the first call.
    if config.logger == None:
        depreacation_logger = logging.getLogger("deprecation_logger")
        depreacation_logger.setLevel(config.lvl)
        file_handler = logging.FileHandler(config.file)
        formatter = logging.Formatter(config.format)
        file_handler.setFormatter(formatter)
        depreacation_logger.addHandler(file_handler)
        config.logger = depreacation_logger
    # Create log
    log_message = (
        f"Deprecation Alert: URL={deprecation_url}, "
        f"HTTP Method={http_method}, "
        f"Deprecated Parameters={deprecated_parameter if deprecated_parameter else "None"}, "
        f"Deprecation Date={deprecation_datetime.isoformat() if deprecation_datetime else "None"}, "
        f"Sunset Date={sunset_datetime.isoformat() if sunset_datetime else "None"}"
    )
    config.logger.warning(log_message)

def get_deprecation_http_header() -> list[str]:
    """
    Returns header fields that should be used to detect deprecation. "sunset" and "deprecation" are always used.
    """
    global CUSTOM_HTTP_DEPRECATION_HEADER 
    return CUSTOM_HTTP_DEPRECATION_HEADER

def get_logging_configuration() -> Logging_Configuration:
    """
    Returns logging configuration for the notifications.
    """
    global LOGGING_DEPRECATION_CONFIGURATION
    return LOGGING_DEPRECATION_CONFIGURATION

def get_slack_configuration() -> Slack_Configuration:
    """
    Returns slack configuration for the notifications.
    """
    global SLACK_DEPRECATION_CONFIGURATION
    return SLACK_DEPRECATION_CONFIGURATION

def get_jira_configuration() -> JIRA_Configuration:
    """
    Returns jira configuration for the notifications.
    """
    global JIRA_DEPRECATION_CONFIGURATION
    return JIRA_DEPRECATION_CONFIGURATION