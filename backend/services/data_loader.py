from pathlib import Path
import json
import csv


# ============================================================
# NER-LOGIXAI DATA LOADER
# ============================================================
#
# Purpose:
# - Discover all local disaster/weather datasets
# - Read JSON / GeoJSON / CSV data
# - Extract usable state-level evidence
# - Feed structured data into Phase 5
#
# IMPORTANT:
# This file does NOT download data.
# data_sources.py handles downloading.
# This file only LOADS and INTEGRATES data already present
# inside backend/data/raw/.
# ============================================================


# ============================================================
# PROJECT DIRECTORIES
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]

RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"

WEATHER_DIR = RAW_DIR / "weather"
RAINFALL_DIR = RAW_DIR / "rainfall"
FLOOD_DIR = RAW_DIR / "flood"
LANDSLIDE_DIR = RAW_DIR / "landslide"


SUPPORTED_EXTENSIONS = {
    ".csv",
    ".json",
    ".geojson",
    ".txt",
    ".xlsx",
    ".xls",
    ".nc",
    ".grib",
    ".grb",
    ".grib2",
    ".tif",
    ".tiff",
}


# ============================================================
# NORTH-EASTERN STATES
# ============================================================

NORTH_EAST_STATES = [
    "Arunachal Pradesh",
    "Assam",
    "Manipur",
    "Meghalaya",
    "Mizoram",
    "Nagaland",
    "Sikkim",
    "Tripura",
]


STATE_ALIASES = {
    "arunachal": "Arunachal Pradesh",
    "arunachal pradesh": "Arunachal Pradesh",
    "assam": "Assam",
    "manipur": "Manipur",
    "meghalaya": "Meghalaya",
    "mizoram": "Mizoram",
    "nagaland": "Nagaland",
    "sikkim": "Sikkim",
    "tripura": "Tripura",
}


# ============================================================
# DIRECTORY SETUP
# ============================================================

def ensure_directories():
    """Create all required data directories."""

    for directory in [
        RAW_DIR,
        PROCESSED_DIR,
        WEATHER_DIR,
        RAINFALL_DIR,
        FLOOD_DIR,
        LANDSLIDE_DIR,
    ]:
        directory.mkdir(parents=True, exist_ok=True)


# ============================================================
# STATE NORMALIZATION
# ============================================================

def normalize_state(value):
    """
    Convert different state-name formats into the
    standard NER state name.
    """

    if value is None:
        return None

    text = str(value).strip().lower()

    text = text.replace("_", " ")
    text = text.replace("-", " ")

    return STATE_ALIASES.get(text)


# ============================================================
# FILE DISCOVERY
# ============================================================

def list_data_files(category: str):
    """List supported files for a data category."""

    ensure_directories()

    category_dir = RAW_DIR / category

    if not category_dir.exists():
        return []

    files = []

    for path in category_dir.rglob("*"):

        if not path.is_file():
            continue

        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue

        files.append({
            "name": path.name,
            "path": str(path),
            "extension": path.suffix.lower(),
            "size_bytes": path.stat().st_size,
        })

    return files


# ============================================================
# INVENTORY
# ============================================================

def inventory():
    """Return all available local datasets."""

    ensure_directories()

    return {
        "weather": list_data_files("weather"),
        "rainfall": list_data_files("rainfall"),
        "flood": list_data_files("flood"),
        "landslide": list_data_files("landslide"),
    }


# ============================================================
# FILE READERS
# ============================================================

def read_csv(path):
    """Read CSV safely."""

    with open(
        path,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        return list(csv.DictReader(file))


def read_json(path):
    """Read JSON or GeoJSON."""

    with open(
        path,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


# ============================================================
# GENERIC DATA READER
# ============================================================

def read_data_file(path):
    """
    Read a supported local data file.

    Returns:
        parsed Python object
        or None when the file cannot be read.
    """

    path = Path(path)

    extension = path.suffix.lower()

    try:

        if extension == ".csv":
            return read_csv(path)

        if extension in {".json", ".geojson"}:
            return read_json(path)

        # Text files
        if extension == ".txt":

            with open(
                path,
                "r",
                encoding="utf-8"
            ) as file:

                return file.read()

        return None

    except Exception as exc:

        print(
            f"[WARNING] Could not read {path.name}: {exc}"
        )

        return None


# ============================================================
# NUMERIC VALUE EXTRACTION
# ============================================================

def _number(value):
    """
    Convert a value into float.

    Returns None if conversion is impossible.
    """

    if value is None:
        return None

    if isinstance(value, bool):
        return None

    try:

        if isinstance(value, str):

            value = (
                value
                .replace(",", "")
                .replace("mm", "")
                .strip()
            )

        return float(value)

    except Exception:
        return None


# ============================================================
# FIND STATE IN FILE
# ============================================================

def find_state(data, filename):
    """
    Determine which NER state a dataset belongs to.

    Priority:
    1. Explicit state field
    2. Filename
    """

    # --------------------------------------------------------
    # Search filename
    # --------------------------------------------------------

    name = Path(filename).stem.lower()

    for alias, state in STATE_ALIASES.items():

        if alias in name:
            return state

    # --------------------------------------------------------
    # Search dictionary
    # --------------------------------------------------------

    if isinstance(data, dict):

        for key in [
            "state",
            "State",
            "STATE",
            "name",
            "Name",
            "district",
            "District",
        ]:

            if key in data:

                state = normalize_state(data[key])

                if state:
                    return state

    # --------------------------------------------------------
    # Search list
    # --------------------------------------------------------

    if isinstance(data, list):

        for row in data:

            if not isinstance(row, dict):
                continue

            for key in [
                "state",
                "State",
                "STATE",
                "name",
                "Name",
            ]:

                if key in row:

                    state = normalize_state(row[key])

                    if state:
                        return state

    return None


# ============================================================
# WEATHER EXTRACTION
# ============================================================

def extract_weather_data(data):
    """
    Extract useful weather values from an Open-Meteo style
    response or other weather JSON.

    Returns a normalized dictionary.
    """

    result = {}

    if not isinstance(data, dict):
        return result

    # --------------------------------------------------------
    # Top-level normalized wrapper
    # --------------------------------------------------------

    if isinstance(data.get("data"), dict):

        source_data = data["data"]

    else:

        source_data = data

    # --------------------------------------------------------
    # Current weather
    # --------------------------------------------------------

    current = source_data.get("current")

    if isinstance(current, dict):

        for key in [
            "temperature_2m",
            "relative_humidity_2m",
            "precipitation",
            "rain",
            "wind_speed_10m",
            "weather_code",
        ]:

            if key in current:

                value = _number(current[key])

                if value is not None:
                    result[key] = value

    # --------------------------------------------------------
    # Hourly data
    # --------------------------------------------------------

    hourly = source_data.get("hourly")

    if isinstance(hourly, dict):

        result["hourly"] = {}

        for key in [
            "time",
            "temperature_2m",
            "relative_humidity_2m",
            "precipitation",
            "rain",
            "weather_code",
            "wind_speed_10m",
        ]:

            if key in hourly:

                values = hourly[key]

                if isinstance(values, list):

                    result["hourly"][key] = values

    # --------------------------------------------------------
    # Daily data
    # --------------------------------------------------------

    daily = source_data.get("daily")

    if isinstance(daily, dict):

        result["daily"] = {}

        for key, values in daily.items():

            result["daily"][key] = values

    return result


# ============================================================
# RAINFALL EXTRACTION
# ============================================================

def extract_rainfall_data(data):
    """
    Extract rainfall values from weather/rainfall datasets.
    """

    rainfall_values = []

    if isinstance(data, dict):

        # ----------------------------------------------------
        # Direct rainfall fields
        # ----------------------------------------------------

        for key in [
            "rainfall",
            "rainfall_mm",
            "daily_rainfall",
            "precipitation",
            "precipitation_mm",
            "rain",
        ]:

            if key in data:

                value = data[key]

                if isinstance(value, list):

                    for item in value:

                        number = _number(item)

                        if number is not None:
                            rainfall_values.append(number)

                else:

                    number = _number(value)

                    if number is not None:
                        rainfall_values.append(number)

        # ----------------------------------------------------
        # Open-Meteo current
        # ----------------------------------------------------

        current = data.get("current")

        if isinstance(current, dict):

            for key in [
                "rain",
                "precipitation",
            ]:

                if key in current:

                    number = _number(current[key])

                    if number is not None:
                        rainfall_values.append(number)

        # ----------------------------------------------------
        # Open-Meteo hourly
        # ----------------------------------------------------

        hourly = data.get("hourly")

        if isinstance(hourly, dict):

            for key in [
                "rain",
                "precipitation",
            ]:

                values = hourly.get(key)

                if isinstance(values, list):

                    for item in values:

                        number = _number(item)

                        if number is not None:
                            rainfall_values.append(number)

        # ----------------------------------------------------
        # Wrapped Open-Meteo data
        # ----------------------------------------------------

        if isinstance(data.get("data"), dict):

            rainfall_values.extend(
                extract_rainfall_data(
                    data["data"]
                )
            )

    elif isinstance(data, list):

        for row in data:

            rainfall_values.extend(
                extract_rainfall_data(row)
            )

    return rainfall_values


# ============================================================
# FLOOD / LANDSLIDE EXTRACTION
# ============================================================

def extract_hazard_data(data, hazard):
    """
    Extract explicit flood or landslide indicators.
    Handles numeric ratings, severity levels, and nested observations.
    """

    values = []

    if not isinstance(data, (dict, list)):
        return values

    keys = {

        "flood": [
            "flood",
            "flood_risk",
            "flood_status",
            "flood_alert",
            "flood_severity",
            "flood_score",
            "water_level",
            "river_level",
            "flood_index",
            "severity",
            "fatalities",
            "human_fatality",
            "duration_days",
            "average_severity",
            "latest_severity",
        ],

        "landslide": [
            "landslide",
            "landslide_risk",
            "landslide_status",
            "landslide_alert",
            "landslide_severity",
            "landslide_score",
            "landslide_index",
            "slope_risk",
            "severity",
            "fatalities",
            "fatality_count",
            "average_severity",
            "latest_severity",
        ],

    }

    size_map = {
        "small": 1.0,
        "medium": 2.0,
        "large": 3.0,
        "very_large": 4.0,
        "very large": 4.0,
    }

    wanted = keys.get(hazard, [])

    if isinstance(data, dict):

        for key in wanted:

            if key in data:

                raw_val = data[key]

                if isinstance(raw_val, list):
                    for item in raw_val:
                        num = _number(item)
                        if num is not None:
                            values.append(num)

                elif isinstance(raw_val, str) and raw_val.strip().lower() in size_map:
                    values.append(size_map[raw_val.strip().lower()])

                else:
                    num = _number(raw_val)
                    if num is not None:
                        values.append(num)

        # Inspect nested observations list
        if isinstance(data.get("observations"), list):
            for obs in data["observations"]:
                values.extend(extract_hazard_data(obs, hazard))

        # Nested wrapper
        if isinstance(data.get("data"), (dict, list)):

            values.extend(
                extract_hazard_data(
                    data["data"],
                    hazard
                )
            )

    elif isinstance(data, list):

        for row in data:

            values.extend(
                extract_hazard_data(
                    row,
                    hazard
                )
            )

    return values


# ============================================================
# INSPECT FILE
# ============================================================

def inspect_file(path):

    path = Path(path)

    result = {
        "name": path.name,
        "extension": path.suffix.lower(),
        "size_bytes": path.stat().st_size,
    }

    try:

        data = read_data_file(path)

        if path.suffix.lower() == ".csv":

            result["type"] = "csv"

            if isinstance(data, list):

                result["rows"] = len(data)

                result["columns"] = (
                    list(data[0].keys())
                    if data
                    else []
                )

        elif path.suffix.lower() in {
            ".json",
            ".geojson"
        }:

            result["type"] = "json"

            if isinstance(data, dict):

                result["keys"] = list(
                    data.keys()
                )

                if "features" in data:

                    features = data["features"]

                    if isinstance(features, list):

                        result["feature_count"] = len(
                            features
                        )

        else:

            result["type"] = (
                path.suffix.lower()
                .lstrip(".")
            )

    except Exception as exc:

        result["error"] = str(exc)

    return result


# ============================================================
# LOAD CATEGORY
# ============================================================

def load_category(category):
    """
    Load every readable file in a category.

    Returns a list of structured dataset records.
    """

    category_dir = RAW_DIR / category

    results = []

    if not category_dir.exists():
        return results

    for path in category_dir.rglob("*"):

        if not path.is_file():
            continue

        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue

        try:

            data = read_data_file(path)

            if data is None:
                continue

            state = find_state(
                data,
                path.name
            )

            record = {
                "state": state,
                "file": path.name,
                "path": str(path),
                "category": category,
                "raw": data,
            }

            # ------------------------------------------------
            # Weather
            # ------------------------------------------------

            if category == "weather":

                record["weather"] = (
                    extract_weather_data(data)
                )

                rainfall = extract_rainfall_data(data)

                if rainfall:
                    record["rainfall_values"] = rainfall

            # ------------------------------------------------
            # Rainfall
            # ------------------------------------------------

            elif category == "rainfall":

                rainfall = extract_rainfall_data(data)

                record["rainfall_values"] = rainfall

            # ------------------------------------------------
            # Flood
            # ------------------------------------------------

            elif category == "flood":

                record["hazard_values"] = (
                    extract_hazard_data(
                        data,
                        "flood"
                    )
                )

            # ------------------------------------------------
            # Landslide
            # ------------------------------------------------

            elif category == "landslide":

                record["hazard_values"] = (
                    extract_hazard_data(
                        data,
                        "landslide"
                    )
                )

            results.append(record)

        except Exception as exc:

            print(
                f"[WARNING] Failed loading "
                f"{path.name}: {exc}"
            )

    return results


# ============================================================
# BUILD STATE-LEVEL DATA
# ============================================================

def build_state_data():

    ensure_directories()

    state_data = {}

    for state in NORTH_EAST_STATES:

        state_data[state] = {
            "state": state,
            "weather": [],
            "rainfall": [],
            "flood": [],
            "landslide": [],
        }

    # --------------------------------------------------------
    # WEATHER
    # --------------------------------------------------------

    for record in load_category("weather"):

        state = record.get("state")

        if state in state_data:

            state_data[state]["weather"].append(
                record
            )

    # --------------------------------------------------------
    # RAINFALL
    # --------------------------------------------------------

    for record in load_category("rainfall"):

        state = record.get("state")

        if state in state_data:

            state_data[state]["rainfall"].append(
                record
            )

    # --------------------------------------------------------
    # FLOOD
    # --------------------------------------------------------

    for record in load_category("flood"):

        state = record.get("state")

        if state in state_data:

            state_data[state]["flood"].append(
                record
            )

    # --------------------------------------------------------
    # LANDSLIDE
    # --------------------------------------------------------

    for record in load_category("landslide"):

        state = record.get("state")

        if state in state_data:

            state_data[state]["landslide"].append(
                record
            )

    return state_data


# ============================================================
# MAIN INTEGRATION FUNCTION
# ============================================================

def get_all_data_summary():
    """
    Return structured disaster/weather data for Phase 5.

    IMPORTANT:
    Despite the historical function name, this now returns
    a structured dictionary rather than only a text summary.

    Phase 5 can therefore identify the eight NER states and
    extract actual rainfall/weather/hazard evidence.
    """

    state_data = build_state_data()

    return {
        "region": "North-Eastern India",
        "states": state_data,
        "inventory": inventory(),
    }


def load_all_data():
    """Load all integrated disaster and weather datasets for all 8 NER states."""
    return get_all_data_summary()


# ============================================================
# HUMAN-READABLE SUMMARY
# ============================================================

def get_data_summary_text():

    state_data = build_state_data()

    summaries = []

    for state in NORTH_EAST_STATES:

        data = state_data[state]

        summaries.append(
            f"""
=== {state.upper()} ===
Weather files: {len(data["weather"])}
Rainfall files: {len(data["rainfall"])}
Flood files: {len(data["flood"])}
Landslide files: {len(data["landslide"])}
"""
        )

    return "\n".join(summaries)


# ============================================================
# COMMAND LINE TEST
# ============================================================

if __name__ == "__main__":

    print("=" * 70)
    print("NER-LogixAI DATA INTEGRATION")
    print("=" * 70)

    ensure_directories()

    data = get_all_data_summary()

    print(
        json.dumps(
            data,
            indent=2,
            ensure_ascii=False,
            default=str
        )[:10000]
    )

    print()
    print("=" * 70)
    print("DATA SUMMARY")
    print("=" * 70)

    print(get_data_summary_text())