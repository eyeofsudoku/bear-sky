# bear-sky

Berlin's sky on [Delilerden Sen Anlarsın](https://delilerdensenanlarsin.bearblog.dev/).

Every 30 minutes a GitHub Action checks the weather and time of day in Berlin
(Open-Meteo, no account needed) and sends a matching theme to the blog through
the Bear API: dawn, day, dusk or night, with clear sky, clouds, rain, snow or fog.
Everything is still; nothing animates.

Once a day it collects every line from the tagged posts into a hidden pool on the home page.
A few lines of JavaScript in the blog footer pick one at random on every visit,
show it in large type, and keep the Berlin clock in the corner badge ticking.

## Files

- `sky/base.css`: the blog's own theme. **Edit the look here**, not in the Bear dashboard,
  because the script overwrites the dashboard CSS every 30 minutes.
- `sky/sky.py`: the script (palettes, weather layers, quote collection).
- `footer.html`: pasted once into Bear (Settings → Header and footer directives → footer).
- `.github/workflows/sky.yml`: the schedule.

## Settings

- The API key lives in the repo secret `BEAR_API_KEY`.
- Only posts tagged `quotable` are quoted. Tag new posts in the Bear editor when you want them in the pool.
- `tag-all` (run once by hand) tags every existing post except those listed in `EXCLUDE_TITLE_PREFIXES`.
- Run a job by hand: Actions → Berlin sky → Run workflow.
