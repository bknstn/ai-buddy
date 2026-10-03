from heartbeat import collect
import json
print(json.dumps(collect("daily"), ensure_ascii=False))
