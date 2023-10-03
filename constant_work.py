import numpy
import random
import matplotlib.pyplot as plt

total_period_secs = 120
request_duration_ms = 50

def steal_time(load):
    class Request:
        def __init__(self, arrival_ms, duration_ms=request_duration_ms):
            self.arrival_ms = arrival_ms
            self.duration_ms = duration_ms
            self.remaining_ms = duration_ms
            self.completion_ms = None
            self.max_load = 0

    total_requests = load * total_period_secs * 1000 / request_duration_ms

    requests = []
    for r in range(int(total_requests)):
        r = Request(arrival_ms=random.uniform(0, total_period_secs * 1000), duration_ms=request_duration_ms)
        requests.append(r)
    requests.sort(key=lambda r: r.arrival_ms)

    def process_in_flight(now, next_request, in_flight):
        end_ms = now + 120000 if next_request is None else next_request.arrival_ms

        # assume completion in order; needs to be changed if request durations are not constant
        load = len(in_flight)
        while(load > 0):
            first = in_flight[0]
            window_ms = end_ms - now
            needed_ms = first.remaining_ms * load
            completed = needed_ms < window_ms

            if not completed:
                needed_ms = window_ms

            now += needed_ms

            if completed:
                first.remaining_ms = 0
                first.completion_ms = now
                in_flight.pop(0)

            work_ms = needed_ms / load
            for r in in_flight:
                r.remaining_ms -= work_ms
                r.max_load = max(r.max_load, load)

            if not completed:
                break

            load = len(in_flight)

    if len(requests) == 0:
        return 0, 0, 0

    in_flight = []
    now = 0
    for r in requests:
        process_in_flight(now, r, in_flight)
        in_flight.append(r)
        now = r.arrival_ms
    process_in_flight(now, None, in_flight)

    steal_time_ms = 0
    tot_duration_ms = 0
    tot_max_load = 0
    for r in requests:
        duration_ms = r.completion_ms - r.arrival_ms
        # print(f"{r.arrival_ms:.3f}-{r.completion_ms:.3f} ({duration_ms:.3f})")
        tot_duration_ms += duration_ms
        steal_time_ms += duration_ms - r.duration_ms
        tot_max_load += r.max_load
    return steal_time_ms, tot_duration_ms / len(requests), tot_max_load / len(requests)

load = []
st = []
d = []
aml = []
for i in range(0, 101, 5):
    total_st, duration, avg_max_load = steal_time(i / 100.0)
    rel_st = total_st / (1000 * total_period_secs)
    rel_d = duration / request_duration_ms
    st.append(rel_st)
    d.append(rel_d)
    aml.append(avg_max_load)
    load.append(i)
    print(f"load {i}, st {rel_st:.3f}, d {duration:.3f}, aml {avg_max_load:.3f}")
plt.plot(load, st)
plt.xlabel('load')
plt.ylabel('st')
plt.yscale('log')
plt.show()

plt.plot(load, d)
plt.xlabel('load')
plt.ylabel('duration')
plt.yscale('log')
plt.show()

plt.plot(load, aml)
plt.xlabel('load')
plt.ylabel('avg max load')
plt.yscale('log')
plt.show()

