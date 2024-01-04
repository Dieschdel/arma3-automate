#!/usr/bin/python3

import os
import os.path
import re

from datetime import datetime
from urllib import request
from pathlib import Path
import json
import jsonschema

import argparse

import shutil

from colorama import Fore, Style

from enum import Enum

from typing import Any
from functools import wraps

import glob


class LogLevel(Enum):
    DEBUG = 1
    INFO = 2
    WARNING = 3
    ERROR = 4

    def __str__(self) -> str:
        return str(self.value)


class Log:
    _logLevel = LogLevel.INFO

    @staticmethod
    def requiredLogLevel(level: LogLevel) -> Any:
        def logLevelDecorator(func: Any):
            @wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                if Log._logLevel.value <= level.value:
                    return func(*args, **kwargs)
            return wrapper
        return logLevelDecorator

    @staticmethod
    def _log(msg: str, color: str | None = None, prefix: str = "") -> None:
        print(f"{color}{prefix}{msg}{Style.RESET_ALL}")

    @staticmethod
    def setLogLevel(level: LogLevel):
        Log._logLevel = level

    @staticmethod
    @requiredLogLevel(LogLevel.DEBUG)
    def debug(msg: str) -> None:
        Log._log(msg, color=Fore.CYAN, prefix="DEBUG: ")

    @staticmethod
    @requiredLogLevel(LogLevel.INFO)
    def info(msg: str) -> None:
        Log._log(msg, color=Fore.BLUE, prefix="INFO: ")

    @staticmethod
    @requiredLogLevel(LogLevel.ERROR)
    def success(msg: str) -> None:
        Log._log(msg, color=Fore.GREEN, prefix="SUCCESS: ")

    @staticmethod
    @requiredLogLevel(LogLevel.WARNING)
    def warning(msg: str) -> None:
        Log._log(msg, color=Fore.YELLOW, prefix="WARNING: ")

    @staticmethod
    @requiredLogLevel(LogLevel.ERROR)
    def error(msg: str) -> None:
        Log._log(msg, color=Fore.RED, prefix="ERROR: ")


class Config:

    _CONFIG_SCHEMA = {
        "type": "object",
        "properties": {
            "steam_cmd": {"type": "string"},
            "server_directory": {"type": "string"},
            "mod_directory": {"type": "string"},
            "steam_user": {"type": "string"},
            "mods": {"type": "object"},
            "do_game_update": {"type": "boolean"},
            "arma3_workshop_id": {"type": "string"},
        },
        "required": ["steam_cmd", "server_directory", "mod_directory", "mods", "arma3_workshop_id"]
    }

    def __init__(self, path: str = ".", filename: str = "config.json"):
        try:
            with open(Path(path) / filename) as jsonFile:
                configJson = json.load(jsonFile)
                jsonschema.validate(configJson, Config._CONFIG_SCHEMA)
                self._configJson = configJson
        except FileNotFoundError:
            Log.error(
                f"File {path}/{filename} does not exist or is not accessible.")
            exit()
        except json.decoder.JSONDecodeError as error:
            Log.error(f"Malformed json file. {error}")
            exit()
        except jsonschema.ValidationError as error:  # type: ignore
            # unknownMemberType: ignore
            Log.error(f"Malformed json file. {error.message}")
            exit()

        self._extractConfig()

    def _extractConfig(self) -> None:
        self.STEAM_CMD = str(self._configJson["steam_cmd"])
        self.SERVER_DIR = Path(self._configJson["server_directory"])
        self.MODS_DIR = Path(self._configJson["mod_directory"])

        self.MODS: list[tuple[str, str]] = list(
            self._configJson["mods"].items())

        self.STEAM_USER = str(
            self._configJson.get("steam_user") if self._configJson.get("steam_user") is not None else None)

        self.ARMA_3_WORKSHOP_ID = str(self._configJson["arma3_workshop_id"])
        self.WORKSHOP_DIR = self.SERVER_DIR / \
            f"steamapps/workshop/content/{self.ARMA_3_WORKSHOP_ID}"


class SteamCmdQuery:
    _baseQuery = ""
    _parameters: list[str] = []

    def __init__(self, exe: str, forceInstallDir: Path, username: str | None = None, autoQuit: bool = True, runAsSudo: bool = True):
        self._baseQuery = exe
        self._autoQuit = autoQuit
        self._runAsSudo = runAsSudo

        self.addParameter(f"+force_install_dir {forceInstallDir}")

        if username != None:
            self.addParameter(f"+login {username}")

    def addParameter(self, parameter: str) -> None:
        self._parameters.append(parameter)

    def _getQueryString(self) -> str:
        parameterString = " ".join(self._parameters)

        return f"{'sudo ' if self._runAsSudo else ''}{self._baseQuery} {parameterString}"

    def run(self):
        if self._autoQuit:
            self.addParameter("+quit")

        queryString = self._getQueryString()
        Log.debug(queryString)

        os.system(queryString)


def addModDownloadsToQueryParameters(steamCmdQuery: SteamCmdQuery, config: Config) -> SteamCmdQuery:
    A3_WORKSHOP_DIR = Path(config.SERVER_DIR) / \
        f"steamapps/workshop/content/{config.ARMA_3_WORKSHOP_ID}"

    def doesModNeedDownload(modId: str, path: Path) -> bool:
        UPDATE_PATTERN = re.compile(
            r"workshopAnnouncement.*?<p id=\"(\d+)\">", re.DOTALL)
        WORKSHOP_CHANGELOG_URL = "https://steamcommunity.com/sharedfiles/filedetails/changelog"
        if os.path.isdir(path) and os.path.isdir(path / str(modId)):
            response = request.urlopen(
                f"{WORKSHOP_CHANGELOG_URL}/{modId}").read()
            response = response.decode("utf-8")
            match = UPDATE_PATTERN.search(response)

            if match:
                updated_at = datetime.fromtimestamp(int(match.group(1)))
                created_at = datetime.fromtimestamp(os.path.getctime(path))

                return updated_at >= created_at
        return True

    for modName, modId in config.MODS:
        if doesModNeedDownload(modId, A3_WORKSHOP_DIR):
            steamCmdQuery.addParameter(
                f"+workshop_download_item {config.ARMA_3_WORKSHOP_ID} {modId}")
            Log.debug(
                f"Added \"{modName}\" ({modId}) to the List of mods to download.")
        else:
            Log.info(
                f"No download or update required for \"{modName}\" ({modId})... SKIPPING")
            continue

    return steamCmdQuery


def addGameUpdateToQueryParameters(steamCmdQuery: SteamCmdQuery) -> SteamCmdQuery:
    ARMA_3_SERVER_ID = "233780"
    steamCmdQuery.addParameter(f"+app_update {ARMA_3_SERVER_ID} validate")

    return steamCmdQuery


def assertAllModsAreDownloaded(config: Config) -> None:
    def isModDownloaded(modId: str, config: Config) -> bool:
        path = Path(config.WORKSHOP_DIR) / modId

        return (os.path.isdir(path) is True)

    abortScript = False

    for modName, modId in config.MODS:
        if not isModDownloaded(modId, config):
            Log.error(
                f"Mod \"{modName}\" ({modId}) could not be downloaded! Please check steam-cmd error above and retry later.")
            abortScript = True

    if abortScript:
        Log.error("Unrecoverable error. ABORTING!!!")
        exit()


def createModSymlinks(mods: list[tuple[str, str]], config: Config) -> None:
    for modName, modId in mods:
        link_path = f"{config.MODS_DIR}/{modName}"
        real_path = f"{config.WORKSHOP_DIR}/{modId}"

        if os.path.isdir(real_path):
            if not os.path.islink(link_path):
                os.symlink(real_path, link_path)
                Log.debug("Creating symlink '{link_path}'.")
            else:
                Log.debug("Symlink '{link_path}' already present.")
        else:
            Log.error(
                f"Mod '{modName}' was expected in {real_path} but is not present. Are there any download errors?")
            exit()


def download_mods(config: Config) -> None:
    steamCmdQuery = SteamCmdQuery(
        config.STEAM_CMD, config.SERVER_DIR, config.STEAM_USER)

    steamCmdQuery = addModDownloadsToQueryParameters(steamCmdQuery, config)

    Log.info("Starting Steam-CMD for automatic download/update.")
    steamCmdQuery.run()
    Log.info("Downloading Complete")

    assertAllModsAreDownloaded(config)

    Log.info("Creating Mod directories (symbolic links)")
    createModSymlinks(config.MODS, config)

    Log.success("All Mods successfully downloaded!")


def clean(config: Config) -> None:
    if os.path.isdir(config.WORKSHOP_DIR):
        Log.debug(f"Deleting '{config.WORKSHOP_DIR}'")
        shutil.rmtree(config.WORKSHOP_DIR)

    if os.path.isdir(config.MODS_DIR):
        Log.debug(f"Deleting '{config.MODS_DIR}/*'")
        modFolders = glob.glob(f"{config.MODS_DIR}/*'")
        for f in modFolders:
            os.remove(f)

    Log.info("Auxiliary files deleted.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Arma 3 mod server mod downloaded. See https://github.com/Dieschdel/arma3-automate for more info')
    parser.add_argument(
        '--clean', help='deletes all downloaded mods and auxiliary files', action="store_true")
    parser.add_argument(
        "--no-download-mods", action="store_true", help="stops the download of mods but still processes the other flags (debug)")
    parser.add_argument(
        "--log-level", choices=[level.name for level in list(LogLevel)], help="Sets Log-Level to the specified option")
    args = parser.parse_args()

    if args.log_level:
        Log.setLogLevel(LogLevel[args.log_level])

    config = Config(filename="config.json")
    Log.info("Config loaded.")

    if args.clean:
        clean(config)

    if not args.no_download_mods:
        download_mods(config)
