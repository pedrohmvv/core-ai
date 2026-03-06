from core.exceptions import CustomException


class BadRequestException(CustomException):
    code = 400
    error_code = "CHAT__BAD_REQUEST"
    message = "We apologize for the inconvenience, but we're currently experiencing an issue with the model. Our engineering team is already on the case and working to resolve it as quickly as possible."


class RateLimitException(CustomException):
    code = 429
    error_code = "CHAT__RATE_LIMIT"
    message = "We detected a high volume of messages in a short period of time. To ensure stability, please wait around 1 minute before continuing."

