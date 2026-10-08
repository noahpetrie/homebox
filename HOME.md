# noahpetrie/homebox: home fork of Homebox

Runs the household Homebox at https://homebox.madiba.ca: the upstream release plus a few
commits on the `home` branch. Source for this modified version is public here, as the
AGPL requires.

## What's different from upstream

- **Scanned barcodes are kept.** Creating an item from a barcode lookup saves the code as
  a custom field ("ISBN" for 978/979 codes, otherwise "Barcode"), and fills Manufacturer
  and Model Number from the lookup (ISBN as model number for books). UPCitemDB results
  use the publisher when there is no brand.
- **Item cards.** Photos sit on a plain muted backdrop with a soft shadow instead of a
  blurred copy of themselves; the quantity badge is hidden when it is 1.
- **Faster scanner.** Product barcodes are decoded with zxing-cpp (WebAssembly) from a
  1080p stream on the best back camera (iPhone multi-lens cameras, not telephoto), and the
  lookup opens as soon as a code is read twice; aiming box; AR mode is explained.
- **Locations page.** Cards with item counts, photo strips and sub-locations (non-empty
  first, compact empty ones), a New location button, and a labelled Cards/Tree toggle.
- **Collapsed sidebar.** The Collection chevron is hidden in icon mode so the cog isn't
  cut off.

## Updating to a new upstream release

```bash
git fetch upstream --tags
git rebase --onto <new-tag> <old-tag> home
docker build --build-arg VERSION=<new-tag>+home.1 -t home/homebox:<ver>-home.1 .
```

Use `+home.N` in VERSION (semver build metadata) so the "new version available" popup
only fires for real upstream releases. To preview a build first: tag it `home/homebox:<ver>-home.N-test`, copy the live data to
`data/homebox-test`, and `docker compose --profile test up -d homebox-test`
(https://homebox-test.madiba.ca). Then back up `data/homebox/homebox.db`, change the
image tag in `~/Developer/home-site/docker/compose.yml`, and `docker compose up -d homebox`.
