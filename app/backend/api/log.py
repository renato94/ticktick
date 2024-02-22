import logging.config
import os

import logging


class CustomFormatter(logging.Formatter):
    green = "\x1b[32;20m"
    blue = "\x1b[34;20m"
    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    format = "[%(levelname)s] (%(filename)s:%(lineno)d) [%(asctime)s]: %(message)s"

    FORMATS = {
        logging.DEBUG: green + format + reset,
        logging.INFO: blue + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset,
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


# uvicorn_error = logging.getLogger("uvicorn.error")
# uvicorn_error.propagate = False
# uvicorn_error.disabled = True
# uvicorn_access = logging.getLogger("uvicorn.access")
# uvicorn_access.propagate = False
# uvicorn_access.disabled = True
import json


class CombinedJsonFormatter(logging.Formatter):
    # Define colors for different log levels
    colors = {
        logging.DEBUG: "\x1b[32;20m",  # Green
        logging.INFO: "\x1b[34;20m",  # Blue
        logging.WARNING: "\x1b[33;20m",  # Yellow
        logging.ERROR: "\x1b[31;20m",  # Red
        logging.CRITICAL: "\x1b[31;1m",  # Bold Red
    }
    reset = "\x1b[0m"

    # Log format to include in JSON output
    log_format = "[%(levelname)s] (%(filename)s:%(lineno)d) [%(asctime)s]: %(message)s"

    def __init__(self):
        super(CombinedJsonFormatter, self).__init__()

    def format(self, record):
        # Create the JSON record
        json_record = {
            "message": record.getMessage(),
            "filename": record.filename,
            "lineno": record.lineno,
            "asctime": self.formatTime(record, self.datefmt),
        }

        # Add colored level name for console readability
        color = self.colors.get(record.levelno, self.reset)

        # Optionally, format the message using the custom log format for console output
        # Uncomment the following lines if you want the console output to be formatted
        # instead of the raw JSON. This can be useful for development or debugging.
        # formatter = logging.Formatter(self.log_format)
        # formatted_message = formatter.format(record)
        # json_record["formatted_message"] = formatted_message

        json_string = json.dumps(json_record, ensure_ascii=False)
        return f"{color}{json_string}{self.reset}"


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Use CombinedJsonFormatter for the logger
ch = logging.StreamHandler()
ch.setFormatter(CombinedJsonFormatter())
logger.addHandler(ch)
