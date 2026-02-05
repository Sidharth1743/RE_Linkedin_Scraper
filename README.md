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

## Notes

- Cookies are saved in `linkedin_cookies/` to speed up subsequent runs.
- Use this tool responsibly and respect LinkedIn’s Terms of Service.
