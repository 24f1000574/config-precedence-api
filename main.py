from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from dotenv import dotenv_values
import yaml
import os

app = FastAPI()

# Allow the grader/browser to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

DEFAULTS = {
    "port": 8000,
    "workers": 1,
    "debug": False,
    "log_level": "info",
    "api_key": "default-secret-000",
}


def to_bool(value):
    if isinstance(value, bool):
        return value

    return str(value).strip().lower() in {
        "true", "1", "yes", "on"
    }


def coerce(key, value):
    if key in ("port", "workers"):
        return int(value)

    if key == "debug":
        return to_bool(value)

    return str(value)


def load_config():
    # Layer 1: defaults
    config = DEFAULTS.copy()

    # Layer 2: config.development.yaml
    if os.path.exists("config.development.yaml"):
        with open("config.development.yaml", "r", encoding="utf-8") as f:
            yaml_config = yaml.safe_load(f) or {}

        for key, value in yaml_config.items():
            config[key] = coerce(key, value)

    # Layer 3: .env
    if os.path.exists(".env"):
        env_config = dotenv_values(".env")

        for key, value in env_config.items():
            if value is None:
                continue

            # NUM_WORKERS is an alias for workers
            if key == "NUM_WORKERS":
                config["workers"] = coerce("workers", value)

            elif key.startswith("APP_"):
                config[key[4:].lower()] = coerce(
                    key[4:].lower(), value
                )

    # Layer 4: OS environment variables
    for key, value in os.environ.items():
        if not key.startswith("APP_"):
            continue

        config_key = key[4:].lower()
        config[config_key] = coerce(config_key, value)

    return config


@app.get("/effective-config")
def effective_config(
    set: list[str] | None = Query(default=None)
):
    config = load_config()

    # Highest precedence: CLI/query overrides
    if set:
        for item in set:
            if "=" not in item:
                continue

            key, value = item.split("=", 1)
            key = key.strip().lower()

            config[key] = coerce(key, value)

    # Ensure all expected keys exist
    result = {
        "port": int(config.get("port", 8000)),
        "workers": int(config.get("workers", 1)),
        "debug": to_bool(config.get("debug", False)),
        "log_level": str(config.get("log_level", "info")),
        "api_key": "****",
    }

    return result