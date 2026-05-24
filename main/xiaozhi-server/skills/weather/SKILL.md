---
name: weather
description: Use when the user asks about current weather, temperature, rain, wind, air conditions, or a forecast for a location or upcoming days.
metadata:
  xiaozhi:
    functions:
      - get_weather
---

# Weather

When the user asks about weather, temperature, rain, wind, air conditions, or a forecast, use `get_weather`.

If the user does not name a location, let `get_weather` use the configured default location. Do not invent real-time weather from memory.
