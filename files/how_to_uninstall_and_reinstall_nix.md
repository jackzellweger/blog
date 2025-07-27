---
title: How to reinstall nix on macos
date: 2024-10-12
tags: tech
---
# How to uninstall and reinstall nix
### Sources
- https://github.com/NixOS/nix/issues/1402
- [How to completely remove Nix from OS X](https://github.com/NixOS/nix/issues/458#issuecomment-1019743603)
### Steps
* Take a deep breath
* Remove Nix from launchd (see `/Library/LaunchDaemons` and `~/Library/LaunchDaemons`)
  * This doesn’t exist
* Remove `nix` from `/etc/synthetic.conf`
  * Need to sudo vim this
* Remove `nix` from `/etc/fstab` (use `vifs`). Just run the `vifs` command in a terminal located in the `/etc` folder.
  * edit this and remove the line with vim
  * May have to grand access w/ inspector if sudo doesn’t work
* Remove Nix from shell (e.g. `~/.zshrc`)
* Go into disk utility and erase the `Nix` volume, then delete apfs volume
* (good time to reboot)
* Delete symlinks `rm -rf ~/.nix-*`
* Remove Nix user group (once again not sure how to with shell, can System Preferences > Users & Groups covers this)
* Remove users with `sudo dscl . delete /Users/_nixbld1`
* Remove any nix traces in `~/Applications`
* Remove `.nix*` files in `~/`, `~/.config` and `~/.cache`
* Remove `/etc/nix`
* Remove `.nix*` files in `/var/root/` and `/var/root/.cache`
* Cleanup `/etc/bashrc`, `/etc/zshrc` using your backup files if you have one. Backups look like `bashrc.backup-before-nix` and `zshrc.backup-before-nix`
```bash
  # This is what your .bashrc should look like
  # System-wide .bashrc file for interactive bash(1) shells.
  if [ -z "$PS1" ]; then
     return
  fi
  
  PS1='\h:\W \u\$ '
  # Make bash check its window size after a process completes
  shopt -s checkwinsize
  
  [ -r "/etc/bashrc_$TERM_PROGRAM" ] && . "/etc/bashrc_$TERM_PROGRAM"
  
```
* Cleanup `/etc/zshrc` 
  * What do you mean here
* As a final cleanup step, replace `<YOUR_USER>` with your user, and run `sudo rm -rf /etc/nix /nix /var/root/.nix-profile /var/root/.nix-defexpr /var/root/.nix-channels /Users/<YOUR_USER>/.nix-profile /Users/<YOUR_USER>/.nix-defexpr /Users/<YOUR_USER>/.nix-channels`
* Run this, if it fails, try again
```bash
curl --proto '=https' --tlsv1.2 -sSf -L \
  https://install.determinate.systems/nix | sh -s -- install
```
