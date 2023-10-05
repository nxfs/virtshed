import numpy
import random
import matplotlib.pyplot as plt

total_period_secs = 120
request_duration_ms = 50
cpu_count = 24

def simulate(load):
    class Request:
        def __init__(self, arrival_ms, duration_ms=request_duration_ms):
            self.arrival_ms = arrival_ms
            self.duration_ms = duration_ms
            self.remaining_ms = duration_ms
            self.completion_ms = None
            self.max_load = 0

    total_requests = cpu_count * load * total_period_secs * 1000 / request_duration_ms

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
            relative_load = max(load / cpu_count, 1)
            needed_ms = first.remaining_ms * relative_load
            completed = needed_ms < window_ms

            if not completed:
                needed_ms = window_ms

            now += needed_ms

            if completed:
                first.remaining_ms = 0
                # fix rounding errors
                first.completion_ms = max(now, first.arrival_ms + first.duration_ms)
                in_flight.pop(0)

            work_ms = needed_ms / relative_load
            for r in in_flight:
                r.remaining_ms -= work_ms
                r.max_load = max(r.max_load, relative_load)

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

    total_util_ms = 0
    total_steal_time_ms = 0

    stable_regime_margin_ms = (total_period_secs * 1000) / 100

    for r in requests:
        duration_ms = r.completion_ms - r.arrival_ms
        # print(f"{r.arrival_ms:.3f}-{r.completion_ms:.3f} ({duration_ms:.3f})")
        tot_duration_ms += duration_ms
        # rounding errors
        this_steal_time_ms = max(duration_ms - r.duration_ms, 0)
        steal_time_ms += this_steal_time_ms
        tot_max_load += r.max_load

        if r.arrival_ms > stable_regime_margin_ms and r.completion_ms < total_period_secs * 1000 - stable_regime_margin_ms:
            total_util_ms += r.duration_ms
            total_steal_time_ms += this_steal_time_ms

    relative_steal_time = total_steal_time_ms / total_util_ms
    return steal_time_ms, tot_duration_ms / len(requests), tot_max_load / len(requests), relative_steal_time

util = []
load = []
st = []
d = []
max_rq = []
for i in range(1, 100, 1):
    total_st, duration, mrq, rel_st = simulate(i / 100.0)
    rel_d = duration / request_duration_ms - 1
    st.append(int(rel_st * 1000) / 1000)
    d.append(rel_d * 100)
    max_rq.append(mrq)
    util.append(i)
    l = i + rel_st * 100
    load.append(l)
    print(f"util {i}, load {l:.3f}, st {rel_st:.3f}, d {duration:.3f}, max_rq {mrq:.3f}")
plt.plot(util, st)
plt.xlabel('util')
plt.ylabel('relative steal time (steal time / cpu util)')
plt.show()

fig, ax = plt.subplots()
# ax.set_ylim(0, 500)
ax.plot(util, d)
plt.xlabel('cpu pool util [%]')
plt.ylabel('relative steal time [%]')
plt.show()

plt.plot(load, d)
plt.xlabel('cpu pool load [%]')
plt.ylabel('relative steal time [%]')
plt.show()

plt.plot(max_rq, d)
plt.xlabel('max rq')
plt.ylabel('relative steal time [%]')
plt.show()
