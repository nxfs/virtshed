import math
import numpy
import random
import matplotlib.pyplot as plt

def simulate(load, cpu_count=24, request_duration_ms=50, total_period_secs=120):
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
        return 0, 0, 0, 0

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

# runs simulation from 1 to 100% load
def plot_for_each_load():
    util = []
    load = []
    st = []
    d = []
    max_rq = []
    for i in range(1, 100, 1):
        request_duration_ms = 50
        total_st, duration, mrq, rel_st = simulate(i / 100.0, request_duration_ms=request_duration_ms)
        rel_d = duration / request_duration_ms - 1
        st.append(int(rel_st * 1000) / 1000)
        d.append(rel_d * 100)
        max_rq.append(mrq)
        util.append(i)
        l = i + rel_st * 100
        load.append(l)
        print(f"util {i}, load {l:.3f}, st {rel_st:.3f} or {rel_d:.3f}, d {duration:.3f}, max_rq {mrq:.3f}")
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

# run simulation for different pool sizes
def plot_steal_time_for_each_pool_size():
    cpu = []
    st = []
    load = 0.8
    for cpu_count in range(8, 32, 1):
        # load = 0.9 - 0.4 / pow(2, cpu_count / 10)
        # if load < 0.2:
        #   load = 0.2
        load = 0.8
        request_duration_ms = 50
        total_st, duration, mrq, rel_st = simulate(load=load, cpu_count=cpu_count, request_duration_ms=request_duration_ms)
        st.append(rel_st * 100)
        cpu.append(cpu_count)
        print(f"cpu_count {cpu_count}, util {load:3f}, st {rel_st:3f}")

    plt.plot(cpu, st)
    plt.xlabel('nest size [cpus]')
    plt.ylabel('relative steal time [%]')
    plt.title(f'load = 0.8')
    plt.ylim(0, 20)
    plt.show()

# run simulation at given steal time for different pool sizes
def plot_fixed_steal_time_for_each_pool_size():
    cpu = []
    loads = []
    steal_time = 0.025
    for cpu_count in range(2, 32, 1):
        request_duration_ms = 50
        low_load = 0
        high_load = 1
        rel_st = -1
        while abs(rel_st - steal_time) > 0.001 and high_load - low_load > 0.001:
            print(f"bin search cpu_count {cpu_count}, load range {low_load:3f}-{high_load:3f}")
            load = (low_load + high_load) / 2
            total_st, duration, mrq, rel_st = simulate(load=load, cpu_count=cpu_count, request_duration_ms=request_duration_ms)
            if rel_st > steal_time:
                high_load = load
            else:
                low_load = load
        loads.append(load * 100)
        cpu.append(cpu_count)
        print(f"cpu_count {cpu_count}, util {load}, st {rel_st:3f}")
        cpu_count = cpu_count * 2

    plt.plot(cpu, loads)
    plt.xlabel('pool size [cpus]')
    plt.ylabel('load [%]')
    plt.title(f'steal_time = {steal_time}')
    plt.show()


# run simulation for different pool sizes
def plot_steal_time_for_each_load():
    cpu = []
    st = []
    loads = []
    prev_cpu_count = -1
    for load in range(0, 101, 2):
        if load == 0:
            continue
        max_cpu_count = 32
        rel_load = load / 100
        agg_load = rel_load * max_cpu_count

        # real algo is here
        # fake_cpus = 3
        # fake_agg_load = agg_load + fake_cpus
        # fake_max_cpu_count = max_cpu_count + fake_cpus
        # cpu_count = fake_agg_load / 0.8 * (max_cpu_count / fake_max_cpu_count)
        cpu_count = agg_load * 1.15 + 4

        # sanity checks
        if cpu_count < 1:
            cpu_count = 1
        if rel_load > 0:
            pool_load = rel_load * (max_cpu_count / cpu_count)
        else:
            pool_load = 0
        fcpu_count = cpu_count
        cpu_count = int(cpu_count)
        if cpu_count > max_cpu_count:
            cpu_count = max_cpu_count
            # break

        # small instances
        if cpu_count < 8:
            cpu_count = 8
            # continue

        # make graph pretty
        # if prev_cpu_count == cpu_count:
            # continue
        prev_cpu_count = cpu_count

        total_st, duration, mrq, rel_st = simulate(load=pool_load, cpu_count=cpu_count, total_period_secs=120)
        st.append(rel_st * 100)
        cpu.append(fcpu_count)
        loads.append(load)
        print(f"load {load}, agg_load {agg_load}, cpu_count {cpu_count}, pool_load {pool_load:3f}, st {rel_st:3f}")
    plt.plot(loads, cpu)
    plt.xlabel('load [%]')
    plt.ylabel('nest size [cpus]')
    plt.show()

    plt.plot(cpu, st)
    plt.xlabel('nest size [cpus]')
    plt.ylabel('relative steal time [%]')
    plt.title(f'adjusted target load = {0.8}')
    plt.ylim([0,20])
    plt.show()

    plt.plot(loads, st)
    plt.xlabel('load [%]')
    plt.ylabel('relative steal time [%]')
    plt.title(f'adjusted load')
    plt.show()

plot_steal_time_for_each_load()
# plot_steal_time_for_each_pool_size()
