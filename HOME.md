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

## Updating to a new upstream release

```bash
git fetch upstream --tags
git rebase --onto <new-tag> <old-tag> home
docker build --build-arg VERSION=<new-tag>+home.1 -t home/homebox:<ver>-home.1 .
```

Use `+home.N` in VERSION (semver build metadata) so the "new version available" popup
only fires for real upstream releases. Then back up `data/homebox/homebox.db`, change the
image tag in `~/Developer/home-site/docker/compose.yml`, and `docker compose up -d homebox`.
