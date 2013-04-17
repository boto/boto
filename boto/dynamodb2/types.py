# Shadow the DynamoDB v1 bits.
# This way, no end user should have to cross-import between versions & we
# reserve the namespace to extend v2 if it's ever needed.
from boto.dynamodb.types import Dynamizer
