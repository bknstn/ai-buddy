from heartbeat import deliver
message = deliver()
if message:
    print(message)
