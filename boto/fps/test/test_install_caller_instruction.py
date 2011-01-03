from boto.fps.connection import FPSConnection
conn = FPSConnection()
conn.install_caller_instruction()
conn.install_recipient_instruction()
