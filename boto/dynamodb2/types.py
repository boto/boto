# Shadow the DynamoDB v1 bits.
# This way, no end user should have to cross-import between versions & we
# reserve the namespace to extend v2 if it's ever needed.
from boto.dynamodb.types import Dynamizer


# Some constants for our use.
STRING = 'S'
NUMBER = 'N'
BINARY = 'B'
STRING_SET = 'SS'
NUMBER_SET = 'NS'
BINARY_SET = 'BS'
