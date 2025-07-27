---
title: How to reset the nix build user on macos
date: 2025-02-07
tags: tech
---
# How to reset the nix build user on macos

```shell
# 1. Clean existing setup
sudo dscl . delete /Users/_nixbld1          # Remove nixbld user if exists
sudo dscl . delete /Groups/nixbld           # Remove nixbld group if exists

# 2. Create group
sudo dscl . create /Groups/nixbld           # Create new nixbld group
sudo dscl . create /Groups/nixbld PrimaryGroupID 30000  # Set group ID to 30000

# 3. Create user
sudo dscl . create /Users/_nixbld1          # Create new nixbld user
sudo dscl . create /Users/_nixbld1 UniqueID 30001      # Set unique user ID
sudo dscl . create /Users/_nixbld1 PrimaryGroupID 30000  # Associate with nixbld group
sudo dscl . create /Users/_nixbld1 NFSHomeDirectory /var/empty  # Set empty home directory
sudo dscl . create /Users/_nixbld1 UserShell /sbin/nologin     # Prevent login shell access
sudo dscl . create /Users/_nixbld1 RealName "Nix Build User 1" # Set display name

# 4. Add user to group
sudo dscl . append /Groups/nixbld GroupMembership _nixbld1  # Add user to group

# 5. Verify fix
sudo -i nix upgrade-nix  # Test if nix upgrade works
```
