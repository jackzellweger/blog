---
title: Bear notes is this blog's cms
date: 2025-07-26
tags: tech
---
# Bear notes is this blog's cms
I love Bear and use it for everything. I've been meaning to start this blog for a while but didn't want to manage different versions of my content in different places. That's why I build a deployment pipeline that takes my writing directly from the Bear notes database and throws it up online.
A few components that constitute this site. First, a Digital Ocean Droplet. Was really easy to get started with them. On that host, I have K3s running. In K3s, we have a Python web-server pulling `.md` files from a PersistentVolume.
My deployment pipeline starts with a shell script that reads all my Bear notes tagged with `#live`, cleans them up, and dumps them into a folder. I can then do any cleanup I want and push them up to a repo. Here's the script.
```shell
#!/bin/bash

BEAR_DB_PATH="$HOME/Library/Group Containers/9K33E3U3T4.net.shinyfrog.bear/Application Data/database.sqlite"
TAG="${1:-#live}"
OUTPUT_DIR="${2:-./files}"
mkdir -p "$OUTPUT_DIR"
rm -f "$OUTPUT_DIR"/*.md

echo "Exporting Bear notes with tag: $TAG"

# Get note IDs
note_ids=$(sqlite3 -readonly "$BEAR_DB_PATH" "
SELECT Z_PK 
FROM ZSFNOTE 
WHERE ZTEXT LIKE '%$TAG%'
AND (ZTRASHED IS NULL OR ZTRASHED = 0)
AND (ZARCHIVED IS NULL OR ZARCHIVED = 0)
AND (ZPERMANENTLYDELETED IS NULL OR ZPERMANENTLYDELETED = 0)
ORDER BY ZMODIFICATIONDATE DESC;
")

for note_id in $note_ids; do
    title=$(sqlite3 -readonly "$BEAR_DB_PATH" "SELECT COALESCE(ZTITLE, 'Untitled') FROM ZSFNOTE WHERE Z_PK = $note_id;")
    content=$(sqlite3 -readonly "$BEAR_DB_PATH" "SELECT ZTEXT FROM ZSFNOTE WHERE Z_PK = $note_id;")
    content=$(echo "$content" | sed "s|$TAG||g")
    clean_title=$(echo "$title" | sed 's/[^a-zA-Z0-9 ]//g' | tr ' ' '_' | tr '[:upper:]' '[:lower:]')
    filename="${clean_title}.md"
    echo "$content" > "$OUTPUT_DIR/$filename"
done
```
Then in k3s, a git-sync pod on a cron fires up at a set interval to pull from the repo into a PersistentVolume. That pod computes a SHA‑256 of the server code and only restarts the Deployment if the hash changes.
There are definite improvements I could make to the server build process. Using a separate build step with a container registry would certainly be an upgrade. But this works, and it makes writing & pushing changes really easy.
