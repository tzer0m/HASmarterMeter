# HASmarterMeter

A Home Assistant custom integration that exposes electricity usage, cost, and capture success rate from the [tzer0m SmarterMeter system](https://github.com/tzer0m/tzer0mApi) as native Home Assistant sensors.

## Requirements

This integration requires the [tzer0mApi](https://github.com/tzer0m/tzer0mApi) to be running and reachable from your Home Assistant instance, with the `/SmarterMeter/Readings` and `/SmarterMeter/Tariffs` endpoints available and an API key configured.

## What it does

This integration creates the following sensors:

- **Current Reading** — the latest cumulative meter reading in kWh
- **Usage Last 24 Hours** — kWh consumed in the last 24 hours
- **Cost Last 24 Hours** — electricity cost in £ for the last 24 hours
- **Usage Last 7 Days** — kWh consumed in the last 7 days
- **Cost Last 7 Days** — electricity cost in £ for the last 7 days
- **Usage Last 30 Days** — kWh consumed in the last 30 days
- **Cost Last 30 Days** — electricity cost in £ for the last 30 days
- **Reading Success Rate** — percentage of expected readings successfully captured in the last 200 hours

All sensors update every 5 minutes. Cost calculations account for multiple tariff periods and standing charges.

## Installation

### Via HACS (recommended)

1. In Home Assistant, go to HACS → three-dot menu → **Custom repositories**.
2. Add `https://github.com/tzer0m/HASmarterMeter`, category **Integration**.
3. Find **HASmarterMeter** in HACS and install it.
4. Restart Home Assistant.

### Manual

1. Copy the `custom_components/tzer0m_smartermeter` folder into your Home Assistant `config/custom_components/` directory.
2. Restart Home Assistant.

## Setup

1. In Home Assistant, go to **Settings → Devices & Services → Add Integration**.
2. Search for **HASmarterMeter**.
3. Enter the base URL of your tzer0mApi instance (e.g. `https://api.tzer0m.co.uk`) and the configured API key.

## License

Personal project, provided as-is.

---

Icon by [Flaticon](https://www.flaticon.com/free-icon/electric-meter_3251076).
