NO_DEVICE_ERROR = "Could not register your device"

DISALLOWED_EMAILS = [
    "bullbeer.net",
    "stattech.info",
    "sharklasers.com",
    "guerrillamail.info",
    "grr.la",
    "guerrillamail.biz",
    "guerrillamail.com",
    "guerrillamail.de",
    "guerrillamail.net",
    "guerrillamail.org",
    "guerrillamailblock.com",
    "pokemail.net",
    "spam4.me",
    "desoz.com",
    "urhen.com",
]

# Voting
DOWN = 0
UP = 1
NEUTRAL_FROM_DOWN = 2
NEUTRAL_FROM_UP = 3
UP_FROM_DOWN = 4
DOWN_FROM_UP = 5

UPVOTE_CHOICES = [UP, NEUTRAL_FROM_DOWN, UP_FROM_DOWN]
DOWNVOTE_CHOICES = [DOWN, NEUTRAL_FROM_UP, DOWN_FROM_UP]
UPVOTE_ONLY = [UP, UP_FROM_DOWN]
DOWNVOTE_ONLY = [DOWN, DOWN_FROM_UP]
SINGLE_UP = [UP, NEUTRAL_FROM_DOWN]
SINGLE_DOWN = [DOWN, NEUTRAL_FROM_UP]
UPVOTE = "up"
DOWNVOTE = "down"

NEWS_NOTIFICATION = 1
COMMENT_NOTIFICATION = 0

CLOUDFRONT_DOMAIN = "https://d2cwe0vw7pxea6.cloudfront.net"
S3_BUCKET_IMAGES = "https://holiday-images.s3.amazonaws.com"
