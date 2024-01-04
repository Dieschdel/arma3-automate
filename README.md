# arma3-automate

Python script to automatically download ARMA3 mods for Linux servers.

## How it works

Below you find a Step-By-Step instruction, on how to use this script. 

1. Install Steam-CMD, Python 3 and a vanilla installation of the ARMA-3 Server. You probably have both installed, but in case you need a reference, here you go [https://community.bistudio.com/wiki/Arma_3:_Dedicated_Server](https://community.bistudio.com/wiki/Arma_3:_Dedicated_Server) 😉
2. Download (Clone) this repository into whatever folder you like

    ```sh
    # obviously replace <whatever folder you like> with your desired installation path.
    cd <whatever folder you like> && git clone https://github.com/Dieschdel/arma3-automate
    ```

3. Install all required python3 dependencies

   ```sh
   cd <whatever folder you like>/arma3-automate && pip install -r ./requirements.txt
   ```

4. Adjust the `config.json` file inside the download folder to your folder and system structure. You can find more information on how to inside the [config section](#config).

5. Run the script

    ```sh
    ./arma3-automate.py
    ```

    You can access info on further configuration options via running the `--help` command

    ```sh
    ./arma3-automate.py --help
    ```

## Config


The script requires a `config.json` file which holds the necessary mod, path and user configurations.

Below your find a small example as well as a table explaining the individual attributes.

```json
{
    "steam_cmd": "/usr/games/steamcmd",
    "server_directory": "/games/arma3",
    "mod_directory": "/games/arma3/mods",
    "arma3_workshop_id": "107410",
    "steam_user": "my_username",
    "mods": {
        "@cba_a3":                  "450814997",
        "@enhanced_movement":       "333310405",
        "@enhanced_rappelling":     "713709341",
        "@enhanced_gps":            "2480263219",
        "@enhanced_missile_smoke":  "1484261993",
        "@weather_plus":            "2735613231",
        "@whiplash_animations":     "1522831842"
    }
}
```

| Attribute Name  | Description  | Example |
|---|---|---|
| `steam_cmd`  | Path to Steam-CMD script or application | `/usr/games/steamcmd` (apt package) |
| `server_directory`  | Absolute Path to the directory the server is installed in | `/games/arma3` |
| `mod_directoy` |  Absolute Path to the directory the mods shall be downloaded to (must exits) | `/games/arma3/mods` |
| `arma3_workshop_id` |  Arma3 Workshop ID. This should probably not change, but I included it here just in case | `107410` |
| `steam_user` | **Optional** username which will be used to log into steam cmd. If this attribute is not set you will be prompted later in the script | `my_username` |
|`mods`| `<mod_name>: <mod_id>` dictionary specifying all mods to be installed. The name can be chosen freely; the id can be found inside the URL of the mods steam workshop page. | `{"@cba_a3": "450814997", "@enhanced_movement": "333310405"}`|

## Disclaimer

This work was in part inspired by **[a3update.py](https://gist.github.com/Freddo3000/a5cd0494f649db75e43611122c9c3f15)** by Freddo3000 (although I ended up not really using any significant parts of his original script). The original work by Freddo3000 was published under the MIT license.