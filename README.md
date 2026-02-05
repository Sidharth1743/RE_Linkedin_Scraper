# LinkedIn Activity Fetcher

This repo contains two main scripts:

- `linkedin_activity_fetcher.py`: scrapes a LinkedIn profile’s recent activity/posts.
- `download_pdf.py`: logs in and downloads a LinkedIn profile PDF.

## Requirements

1. Python dependencies (uv):

```bash
uv sync
```

2. Playwright browsers:

```bash
playwright install chromium
```

3. Environment variables (optional but recommended):

```env
LINKEDIN_EMAIL=your_email@example.com
LINKEDIN_PASSWORD=your_password
```

## Usage

### Fetch profile activity

```bash
python linkedin_activity_fetcher.py
```

This script uses Playwright to log in (or reuse cookies) and then pulls activity via LinkedIn’s GraphQL calls.

### Download profile PDF

```bash
python download_pdf.py
```

This script reuses the login/session handling from `linkedin_activity_fetcher.py`, fetches the profile URN, and downloads the profile PDF.

## How It Works

### `linkedin_activity_fetcher.py`

1. Starts Playwright, logs into LinkedIn, and saves cookies in `linkedin_cookies/linkedin_session.json`.
2. Opens the target profile page and extracts the `profileUrn` using HTML and network data.
3. Calls LinkedIn’s GraphQL feed endpoint in 20-post ranges, using a pagination token for subsequent pages.
4. Saves each range response as JSON inside a session folder under `linkedin_data/`.
5. Extracts individual posts in LinkedIn order, creates `media_summary.json`, and downloads text/images/videos.

### `download_pdf.py`

1. Reuses the same Playwright login and cookie logic from `linkedin_activity_fetcher.py`.
2. Resolves the target profile URN.
3. Calls the GraphQL PDF action endpoint to retrieve a `downloadUrl`.
4. Downloads the PDF and saves it to `output/username_pdf/`.
5. Writes a JSON log to `output/pdf_json/pdf_downloads.json`.

## Architecture

Diagrammatic view:

```text
                         +----------------------+
                         |   Playwright Login   |
                         |  (cookies/session)   |
                         +----------+-----------+
                                    |
                                    v
                        +-----------------------+
                        | LinkedInActivityFetcher|
                        |  (core scraper class) |
                        +----+-----------+------+
                             |           |
          +------------------+           +------------------+
          |                                     |
          v                                     v
 +------------------------+           +----------------------+
 | linkedin_activity_     |           |    download_pdf.py   |
 | fetcher.py (CLI/usage) |           | (extends fetcher)     |
 +-----------+------------+           +----------+-----------+
             |                                   |
             v                                   v
 +------------------------+           +----------------------+
 | GraphQL Feed Fetch     |           | GraphQL PDF Action   |
 | (pagination token)     |           | (downloadUrl)        |
 +-----------+------------+           +----------+-----------+
             |                                   |
             v                                   v
 +------------------------+           +----------------------+
 | Parse + Media Download |           | Save PDF + JSON Log  |
 +-----------+------------+           +----------+-----------+
             |                                   |
             v                                   v
 +------------------------+           +----------------------+
 | linkedin_data/<session>|           | output/username_pdf  |
 | media_summary + assets |           | output/pdf_json      |
 +------------------------+           +----------------------+
```

Key points:

1. `linkedin_activity_fetcher.py` contains the `LinkedInActivityFetcher` class for login, URN extraction, GraphQL fetches, and media downloads.
2. `download_pdf.py` extends `LinkedInActivityFetcher` to reuse session and URN logic, then adds the PDF download flow.
3. Output is file-based and organized per run for activity scraping, and per profile for PDFs.

## Output Layout

Activity scraper session output:

```
linkedin_data/
  └── <username>_0-<range>_<timestamp>/
      ├── activity_range0_20.json
      ├── activity_range20_40.json
      ├── media_summary.json
      ├── posts/
      ├── extracted_text/
      ├── images/
      └── videos/
```

PDF downloads:

```
output/
  ├── pdf_json/
  │   └── pdf_downloads.json
  └── username_pdf/
      ├── <username>.pdf
      └── ...
```

## Notes

- Cookies are saved in `linkedin_cookies/` to speed up subsequent runs.
- Use this tool responsibly and respect LinkedIn’s Terms of Service.
