#!/bin/bash

BEAR_DB_PATH="$HOME/Library/Group Containers/9K33E3U3T4.net.shinyfrog.bear/Application Data/database.sqlite"
TAG="${1:-#projects/blog/live}"
OUTPUT_DIR="${2:-./files}"
mkdir -p "$OUTPUT_DIR"

# Delete all existing .md files in the output directory
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
    
    # Remove the tag
    content=$(echo "$content" | sed "s|$TAG||g")
    
    # Create filename and save
    clean_title=$(echo "$title" | sed 's/[^a-zA-Z0-9 ]//g' | tr ' ' '_' | tr '[:upper:]' '[:lower:]')
    filename="${clean_title}.md"
    echo "$content" > "$OUTPUT_DIR/$filename"
done
