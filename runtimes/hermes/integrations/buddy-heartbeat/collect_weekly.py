from heartbeat import collect
import json
print(json.dumps(collect("weekly"), ensure_ascii=False))
