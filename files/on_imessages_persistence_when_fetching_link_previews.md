---
title: On imessage's persistence when fetching link previews
date: 2025-07-13
tags: tech
---
# On imessage's persistence when fetching link previews

When I paste a link to my website into iMessage, I see the following log stream on my server.

```shell
[INFO] code 404, message File not found
[INFO] "GET /apple-touch-icon.png HTTP/1.1" 404 -
[INFO] code 404, message File not found
[INFO] "GET /favicon.ico HTTP/1.1" 404 -
[INFO] code 404, message File not found
[INFO] "GET /apple-touch-icon-precomposed.png HTTP/1.1" 404 -
[INFO] "GET /tuning_intermediatemass_black_hole_gravitational_wave_detection_algorithms.md HTTP/1.1" 200 -
[INFO] "GET /images/waveform-shape.png HTTP/1.1" 200 -
[INFO] "GET /images/acf-true.gif HTTP/1.1" 200 -
[INFO] "GET /images/hoft-ss.gif HTTP/1.1" 200 -
```

I count 7 get requests, just so iMessage can have a little image to show in the chat. Looks like it first tries to get the resource `apple-touch-icon.png` at the base URL, then kind of waterfalls down to the favicon, `/apple-touch-icon-precomposed.png`, and then the first 3 images it sees on the web page itself. Interesting—wonder why it gets the first 3?
