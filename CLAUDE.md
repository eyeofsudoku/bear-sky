# bear-sky: Berlin sky for "Delilerden Sen Anlarsın"

Onur's personal Turkish blog https://delilerdensenanlarsin.bearblog.dev (Bear Blog, upgraded). He writes every post himself; never write or edit his posts. This repo only drives the look.

## What it does

- **Sky** (every 30 min, cron `11,41 * * * *`): `sky/sky.py sky` gets Berlin weather (Bright Sky / DWD first, Open-Meteo as fallback; if both fail it exits quietly and the blog keeps its sky) and sends the whole theme to Bear as `custom_styles`: `sky/fonts/fraunces.css` + `sky/base.css` + the sky layers + the weather symbol for the Berlin badge.
- **Time of day** (dawn/day/dusk/night) is set in the reader's browser by the footer script from Berlin time and the sun, so it is right even when GitHub skips runs. The theme carries all four palettes (`html.sky-dawn` … `html.sky-night`); `:root` holds the script's guess as a no-JS fallback.
- **Weather**: background layers stay still (sun glow, stars on clear nights, clouds, fog bands; rain/snow only tint the sky). The **Berlin badge** (top right: time, temperature, "BERLIN") shows an animated symbol on the left: sun/moon, partly cloudy (sun or moon behind cloud), cloud, fog, rain drop, snowflake, thunder. Day/night variants switch with the reader's clock. Animations are transform-only, small, and off for `prefers-reduced-motion`.
- **Quote** (daily 04:17, `sky/sky.py quotes`): saves the paths of posts tagged `quotable` to `sky/quotable.txt` (committed by the workflow) and into the theme as `--sky-posts`. The footer script, on the home page only, picks a random post, fetches it (same site), takes a random sentence or poem line and shows it large in Fraunces with a sky-coloured opening mark (style "B"). Home page content stays only Onur's own line.
- `tag-all` was a one-off job that tagged existing posts; "bazı şarkılar" and "serbest çeviri" posts are never quotable. Onur tags new posts himself.

## Decisions Onur made

- No animation on the page background (an animated full-page rain/snow crashed his iPhone). Only the badge symbol moves.
- No blur, no drops or flakes on the page: they looked repetitive and dirty.
- Berlin sky for everyone, also dark-mode readers.
- Style B for the quote; long lines step down in size (`is-long`, `is-xlong`).
- The `quotable` tag is hidden from readers via CSS.

## Footer snippet

`footer.html` is pasted by hand into Bear: Settings → Header and footer directives → footer. Bear wraps it in `<span id="footer-directive">`. If the script changes, Onur must paste the new version; give him the full file, never a diff.

## Operating notes

- Secret `BEAR_API_KEY` (key of this blog), subdomain set in the workflow.
- Bear's Cloudflare blocks Python's default User-Agent (error 1010); requests send `bear-sky/1.0`.
- Run by hand: Actions → Berlin sky → Run workflow → sky / quotes / tag-all.
- Edit the look in `sky/base.css` or `sky/sky.py`, never in the Bear dashboard (overwritten every run).
- Check from a Claude session: `curl` the blog and grep `sky: <time>, <weather>, <temp>, set HH:MM` in the CSS; runs via `api.github.com/repos/eyeofsudoku/bear-sky/actions/runs`. Test CSS by rendering a saved copy of the live page with Playwright and swapping in `build_css(...)`.
- Scheduled GitHub runs are best effort and can be late or skipped; a run uses the code from when it was queued.
