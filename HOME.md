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
- **Item page.** Large primary photo in the header; custom fields (Author, ISBN, ...) first;
  empty fields, "No" flags, quantity 1 and Manufacturer/Model rows that repeat a custom field
  are hidden (own Show empty switch, off); "+ Add purchase details / warranty" links; label,
  QR, duplicate, template and delete actions in the ⋮ menu.
- **Location page items.** Search (title, author, ISBN, maker, model), type chips, sort, and
  Grid / List / Table views (Table is the original). Create Item is the only button; edit,
  labels and delete are in a ⋮ menu. Empty details card hidden.
- **Import product dialog.** Results as wrapping rows; a single match is preselected.
- **Faster adding.** The Create dialog remembers the last type and location (and applies the
  type's default template); a scan warns when you already have that ISBN/barcode; "Create and
  add another" after a scan goes straight back to the camera; photos sit right under the name
  with a "Take photo" button. Defaults to the Item type. Product images that failed to
  download are skipped instead of throwing.
- **Item types.** Electronics, Appliance, Furniture & Decor and Tool, each with a default
  template of fields. These live in the database, not the code; `home/create-types.py <url>
  <token>` creates or updates them.
- **Handheld barcode scanner.** A Bluetooth/USB scanner (which types the code like a
  keyboard) works anywhere outside a text field: a known code opens the item (or a search
  when several match), Homebox label QR codes open their page, and anything else starts the
  product lookup. Scans are told apart from typing by speed; the code can end with Enter,
  Tab or Down Arrow (the PecuMecu sends Down Arrow) or nothing.
- **Book scans.** An ISBN switches the Create dialog to the Book type (without making it the
  remembered type) and fills the title, author, publisher, year, pages, format and cover from
  Open Library; the details are saved as custom fields next to the ISBN, with the publisher as
  manufacturer. The Import product dialog falls back to Open Library when the product
  databases (UPCitemDB's free tier is rate-limited) return nothing for an ISBN.
- **Create dialog photos** are small thumbnails with delete / rotate / main-photo buttons.
- **"Create and add another" after a scan** reopens the camera only after a camera scan; after
  a handheld-scanner scan it closes the form and waits for the next scan.
- **Packing mode (boxes).** "Pack items" on a location (e.g. one of the Box location type, which
  lives in the database) puts a bar on every page; each handheld or camera scan then moves the
  item there (the camera stays on), recording a "Packed from" field linking the previous
  location. Unknown barcodes go through the product lookup and are created in the box.
- **Item right-click menu** on location pages (long-press on phones): Open, Take out (back to
  "Packed from", else the box's room), Move to…, Delete. Type chips don't double the plural.
  `[text](/path)` custom fields render as in-app links.
- **Barcode fallbacks.** Products found are cached for a week (UPCitemDB's free tier allows
  ~100 lookups a day); Open Pet Food Facts is also queried. When nothing is found, the Import
  product dialog offers a Google search and "Add it anyway" (Create with the barcode saved).
- **Location map.** A location whose sub-locations have a "Region" field (`x,y,w,h` in % of
  the parent's main photo) shows that photo with the areas outlined, labelled with item counts;
  each area shows thumbnails of its items; beside it a contents list has a section per area
  (loose items first, empty areas on one line), linked to the map by hover and click. Used for the ALEX
  drawer's compartments (Storage location type; the drawer photo is a generated empty insert).
- **Packing without barcodes.** The packing bar can add items by name, create new items
  straight into the box, and pack an item by scanning its Homebox QR label.
- **Item order on location pages.** While packing a box, its list shows newest packed first;
  "Recently added" otherwise sorts by when an item last changed (moving it counts).
- **Sub-locations as rows.** A location's sub-locations are full-width rows (natural order)
  with item counts including nested compartments, thumbnails, and compartment chips in layout
  order; empty ones are one line with "Pack here". The empty item list is hidden when things
  live in sub-locations.
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
