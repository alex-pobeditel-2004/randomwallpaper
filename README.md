# randomwallpaper
Python3 script that pulls reasonably random image from wallhaven.cc and sets it as your desktop wallpaper

You can:
* Send randomwallpaper.py to autostart (.sh and .bat scripts are provided)
* Change a config.yaml to choose some resulting image settings and to specify directory to store wallpapers
* Allow downloading images from NSFW category if Wallhaven login/password or API key are provided in the configuration file

Prerequisites:
* Python 3.4+
* `pip3 install -r requirements.txt`
* _(optional)_ Send provided .bat/.sh script to the system startup

Tested on:
* Windows 7, Windows 10 (should work under other Windows systems)
* Arch Linux with Cinnamon DE (should work under other Linux systems with Gnome and MATE DE)
* MacOS Catalina (should work under earlier MacOS versions)

Does not work with KDE.
