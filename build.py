#!/usr/bin/env python3
"""Rebuild index.html with a fresh line 58 timetable from PID open data.

Usage:  python3 build.py            (downloads PID_GTFS.zip, ~46 MB)
        python3 build.py path.zip   (uses an already downloaded zip)

The page needs only the inbound trips (direction Palmovka) up to Nový Prosek,
so the embedded timetable is ~10 kB. PID publishes a new GTFS daily; the page
keeps working after the embedded timetable expires (it assumes the weekly
pattern repeats), but rebuilding every few weeks keeps it exact.
"""
import collections, csv, io, json, os, sys, tempfile, urllib.request, zipfile

ROUTE, TARGET = "L58", "U500Z2P"  # line 58, Nový Prosek platform B (to Palmovka)
URL = "https://data.pid.cz/PID_GTFS.zip"
# Share of each stop-to-stop stretch that has a bus lane in the 58's direction.
# Measured from OpenStreetMap along the 58's route shape (Nov 2026); stretches not listed have none.
BUS_LANES = {
    "U1000Z3P>U606Z2P": 0.05,  # Letňany → Letňanská: only ~40 m just before Letňanská
    "U606Z2P>U500Z2P": 0.70,   # Letňanská → Nový Prosek: Prosecká lane from ~110 m after Letňanská
    "U405Z2P>U1000Z3P": 0.36,  # Výstaviště Letňany → Letňany: ~180 m on Tupolevova/Beladova
}
HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    if len(sys.argv) > 1:
        zpath = sys.argv[1]
    else:
        zpath = os.path.join(tempfile.mkdtemp(), "PID_GTFS.zip")
        print("Downloading", URL)
        urllib.request.urlretrieve(URL, zpath)
    z = zipfile.ZipFile(zpath)

    def rd(name):
        return csv.DictReader(io.TextIOWrapper(z.open(name), encoding="utf-8-sig"))

    def sec(t):
        h, m, s = map(int, t.split(":"))
        return h * 3600 + m * 60 + s

    all_trips = {r["trip_id"]: r for r in rd("trips.txt")}
    trips = {k: r for k, r in all_trips.items() if r["route_id"] == ROUTE}
    st = collections.defaultdict(list)
    other = collections.defaultdict(list)  # stop times of other lines, filled after we know the 58's stops
    rows = []
    for r in rd("stop_times.txt"):
        row = (r["trip_id"], int(r["stop_sequence"]), r["stop_id"], sec(r["arrival_time"]), sec(r["departure_time"]))
        if r["trip_id"] in trips:
            st[r["trip_id"]].append(row[1:])
        else:
            rows.append(row)

    patterns, plist, out, services, stops = {}, [], [], set(), set()
    blocks = {}  # every 58 trip, both directions: start and end (s after service-day midnight)
    for tid, lst in st.items():
        lst.sort()
        blocks[tid] = [lst[0][3], lst[-1][2]]
        ids = [x[1] for x in lst]
        if TARGET not in ids:
            continue
        lst = lst[: ids.index(TARGET) + 1]
        t0 = lst[0][3]
        key = tuple((x[0], x[1], x[2] - t0, x[3] - t0) for x in lst)
        if key not in patterns:
            patterns[key] = len(plist)
            plist.append([list(k) for k in key])
        services.add(trips[tid]["service_id"])
        stops.update(ids[: ids.index(TARGET) + 1])
        out.append([tid, trips[tid]["service_id"], t0, patterns[key]])
    out.sort(key=lambda r: (r[1], r[2]))

    # Other lines that drive the same stop-to-stop stretches in the same direction (same platforms).
    segs = {(a[1], b[1]) for p in plist for a, b in zip(p, p[1:])}
    for row in rows:
        if row[2] in stops:
            other[row[0]].append(row[1:])
    rows = None
    spat, splist, sout, sroutes = {}, [], [], {}
    route_names = {r["route_id"]: r["route_short_name"] for r in rd("routes.txt")}
    for tid, lst in other.items():
        lst.sort()
        keep = set()
        for a, b in zip(lst, lst[1:]):
            if b[0] == a[0] + 1 and (a[1], b[1]) in segs:
                keep.update((a, b))
        if not keep:
            continue
        kl = sorted(keep)
        t0 = kl[0][3]
        key = tuple((x[0], x[1], x[2] - t0, x[3] - t0) for x in kl)
        if key not in spat:
            spat[key] = len(splist)
            splist.append([list(k) for k in key])
        rid = all_trips[tid]["route_id"]
        sroutes[rid] = route_names.get(rid, rid)
        sout.append([tid, t0, spat[key]])
    sout.sort(key=lambda r: r[0])

    days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    cal = {r["service_id"]: {"days": "".join(r[d] for d in days), "start": r["start_date"], "end": r["end_date"]}
           for r in rd("calendar.txt") if r["service_id"] in services}
    exc = collections.defaultdict(lambda: {"add": [], "remove": []})
    for r in rd("calendar_dates.txt"):
        if r["service_id"] in services:
            exc[r["service_id"]]["add" if r["exception_type"] == "1" else "remove"].append(r["date"])
    names, coords = {}, {}
    for r in rd("stops.txt"):
        if r["stop_id"] in stops:
            names[r["stop_id"]] = r["stop_name"]
            coords[r["stop_id"]] = [round(float(r["stop_lat"]), 6), round(float(r["stop_lon"]), 6)]
    fi = next(rd("feed_info.txt"))

    tt = {"route": ROUTE, "target": TARGET, "feedStart": fi["feed_start_date"], "feedEnd": fi["feed_end_date"],
          "calendar": cal, "exceptions": exc, "stops": names, "patterns": plist, "trips": out,
          "busLanes": BUS_LANES, "coords": coords, "blocks": blocks, "shared": {"routes": sroutes, "patterns": splist, "trips": sout}}
    js = json.dumps(tt, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    tpl = open(os.path.join(HERE, "template.html"), encoding="utf-8").read()
    assert "__TIMETABLE__" in tpl
    open(os.path.join(HERE, "index.html"), "w", encoding="utf-8").write(tpl.replace("__TIMETABLE__", js))
    print("shared-stretch lines:", ", ".join(sorted(sroutes.values(), key=lambda s: s.zfill(4))),
          f"({len(sout)} trips, {len(splist)} patterns, {len(js) // 1024} kB embedded)")
    print(f"index.html written: {len(out)} trips, {len(plist)} stop patterns, timetable valid "
          f"{fi['feed_start_date']}–{fi['feed_end_date']}")


if __name__ == "__main__":
    main()
