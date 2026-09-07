# NER-LogixAI — Thursday Judging Runbook (one page)

Everything runs **on this laptop** — nothing is hosted. All data lives in JSON files on disk,
so a crash loses nothing: **restart = same state in ~10 seconds.** Commands below are
PowerShell, run from the repo root (`C:\Users\Acer\Documents\ammu\Ner-logixAI-github`) with the
`.venv` prompt active.

## The 4 commands

**1. START / RESTART the server** (this is also the crash-recovery command):
```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```
Wait ~5 s, then open `localhost:8000` in the browser. If the old process is still alive you'll
get "address already in use" — do step 2 first.

**2. CHECK it's alive / find what owns port 8000:**
```powershell
curl.exe http://127.0.0.1:8000/health          # expect {"status":"ok"}
netstat -ano | findstr :8000                    # last column = PID
```

**3. KILL a stale process, then restart (step 1):**
```powershell
taskkill /PID 6600 /F      # replace 6600 with the PID from netstat
```

**4. REFRESH the live-data pill** (if the console says "weather: stale · rainfall: stale"):
```powershell
.\.venv\Scripts\python.exe -m backend.services.monitor --once
```
Takes ~20 s, then refresh the page. Do this **before the judges arrive**.

Demo URLs — dashboard: `localhost:8000` · field reporter: `localhost:8000/field`

## The 5-minute flow (practice twice: once full, once as a crash drill)

| Time | What to do | What to say |
|---|---|---|
| 0:00 | Dashboard on screen, red **"Active high-severity alert"** pill visible | "North East India's logistics break when landslides and floods cut the roads. This platform tells you — before you dispatch a truck — which routes are risky, why, and what the river and rain are doing right now." |
| 0:30 | **Check a location** → `Mangan` → *Assess location risk* | "Moderate risk, ~42/100. The landslide score is High from real terrain plus live rainfall. The flood line is the river itself: the Teesta at X m³/s vs its own p90 — that's GloFAS satellite river data. Nothing here is invented." Click **हिं/অস** (bottom-right) once to show the multilingual toggle. |
| 2:00 | **Analyze a delivery route** → From `Shillong`, To `Guwahati`, Cargo **Medicines**, Priority **Emergency response** | "The engine checked real OSRM road segments — 94.9 km, 1 hr 13 min. For emergency it weights safety 85% and speed 15%, so it picks a longer, safer corridor when the highway is at risk. Note it says *no verified closure* — we never claim a road is safe, only that no confirmed blockage is in the data." |
| 3:30 | Open **`localhost:8000/field`**. Submit a "Rockfall — NH-6" report with a photo. **Offline proof:** F12 → Network tab → tick *Offline* → submit another → see "Offline — queueing" badge → untick → **⇄ Sync now** | "This is the field-official app for remote districts: geo-tagged, photo evidence, and it queues offline with a unique ID so a retry after network failure never creates a duplicate." Then refresh the console and point at the new orange report pin. |
| 4:30 | Scroll **Live operations** + **District watch** | "The status line is our honesty policy: weather and rainfall are fresh/live, flood and landslide are labelled historical evidence. District watch flags Assam Very High from real records. One platform — live river and rain, risk scoring on every district, mission-aware routing, offline field reporting, and honest labels on every number. Thank you." |

## If something goes wrong mid-demo

- **Live weather/route call fails** (no wifi): the card shows a clean error box — never a crash.
  Pivot instantly to what still works offline: alerts, report pins, vehicle markers, district
  watch, and the field app queue. Say: *"The page and all local data run from this laptop; live
  feeds degrade gracefully."*
- **Server dies / page won't load:** run command 1 (restart), refresh. ~10 s, same data.
- **Port busy after a crash:** command 2 → command 3 → command 1.

## Judge Q&A one-liners

- **Where's the data from?** Open-Meteo (live weather/rain), GloFAS (live river), OSRM/OSM
  (roads), NASA GIBS (satellite), India Flood Inventory + NASA Landslide Catalog + our own field
  reports.
- **Is the landslide score real?** Real catalog records where they exist, plus a live
  rainfall × terrain model — the UI labels it *"estimate, not a recorded event"* when modelled.
- **What don't you claim?** No individual-boulder detection, satellite is screening only
  (cloud-limited), and history ≠ a current closure.
