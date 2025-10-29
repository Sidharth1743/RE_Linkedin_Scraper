<<<<<<< HEAD
run linkedin_acctivity_fetcher.py
this is the final code

Needed playwright 
=======
# LinkedIn Scraper Web App

A modern, responsive web application for scraping and viewing LinkedIn profile activities with automatic media download.

## Features

🎨 **Modern UI**
- LinkedIn-like feed view with cards
- Clean and minimal design
- Dark mode support
- Fully responsive (mobile-friendly)

📸 **Media Support**
- Image carousel for multi-image posts
- Inline video player
- Lightbox for full-size image viewing
- Automatic media download

🔍 **Session Management**
- Displays latest scraping session
- Session statistics (posts, videos, images)
- Organized directory structure

⚡ **Interactive Features**
- Start new scrapes directly from UI
- Keyboard navigation for lightbox (Arrow keys, ESC)
- Auto-pause videos when scrolled out of view
- Smooth animations and transitions

## Installation

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Install Playwright Browsers

```bash
playwright install chromium
```

### 3. Configure Environment

Create a `.env` file with your LinkedIn credentials:

```env
LINKEDIN_EMAIL=your_email@example.com
LINKEDIN_PASSWORD=your_password
```

## Usage

### Running the Web App

```bash
python web_app.py
```

The app will start on `http://localhost:5000`

### Starting a New Scrape

1. Click the **"New Scrape"** button in the header
2. Enter:
   - **LinkedIn Username** (e.g., `billgates` or `https://linkedin.com/in/billgates`)
   - **Target Range** (e.g., `60` to fetch posts 0-60 in batches of 20)
3. Click **"Start Scraping"**
4. Wait for the scraping to complete
5. Page will auto-refresh with new data

### Alternative: Command Line Scraping

You can also run the scraper directly:

```bash
python linkedin_activity_fetcher.py
```

Then start the web app to view the results.

## Directory Structure

```
linkedin_data/
  └── username_0-60_20251029_143022/
      ├── activity_range0_20.json       # Raw activity data
      ├── activity_range20_40.json
      ├── activity_range40_60.json
      ├── media_summary.json             # Media summary with URLs
      ├── posts/                         # Individual post JSON files
      │   ├── post_1.json
      │   ├── post_2.json
      │   └── ...
      ├── extracted_text/                # Post text files
      │   ├── post_1.txt
      │   ├── post_2.txt
      │   └── ...
      ├── images/                        # Downloaded images
      │   ├── post_1_image_1.jpg
      │   ├── post_1_image_2.jpg
      │   └── ...
      └── videos/                        # Downloaded videos
          ├── post_3_video.mp4
          └── ...
```

## Web App Features

### Dark Mode

Toggle between light and dark themes using the moon/sun icon in the header.
Your preference is saved locally.

### Image Viewing

- **Click any image** to open in lightbox
- **Arrow keys** or on-screen buttons to navigate
- **ESC key** to close lightbox

### Carousel Navigation

For posts with multiple images:
- Use **arrow buttons** to navigate
- Click **indicator dots** to jump to specific image
- Smooth transitions between images

### Video Playback

- Videos play directly in the browser
- Auto-pause when scrolled out of view
- Standard HTML5 video controls

## API Endpoints

- `GET /` - Home page
- `POST /api/start-scrape` - Start new scraping session
- `GET /api/scrape-status` - Get scraping progress
- `GET /api/refresh` - Refresh session data
- `GET /media/<filename>` - Serve media files

## Technology Stack

- **Backend**: Flask (Python)
- **Frontend**: HTML5, CSS3, JavaScript (Vanilla)
- **Scraping**: Playwright
- **Icons**: Font Awesome 6
- **Storage**: File-based (JSON + media files)

## Browser Support

- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)
- Mobile browsers (iOS Safari, Chrome Mobile)

## Security Notes

⚠️ **Important**:
- Never commit `.env` file (it's in `.gitignore`)
- Keep your LinkedIn cookies private
- Use this tool responsibly and respect LinkedIn's Terms of Service
- Scraped data is stored locally only

## Troubleshooting

### Issue: "No data available"

**Solution**: Run the scraper first to generate data, then refresh the web app.

### Issue: Images/videos not loading

**Solution**: Check that the session directory exists in `linkedin_data/` and media files are present.

### Issue: Scraping fails

**Solution**:
1. Check your LinkedIn credentials in `.env`
2. Ensure you're not blocked by LinkedIn
3. Try logging in manually first to save cookies

### Issue: Dark mode not working

**Solution**: Clear browser cache and localStorage, then refresh.

## Contributing

Feel free to submit issues, fork the repository, and create pull requests for any improvements.

## License

This project is for educational purposes only. Use responsibly.

## Credits

Made with ❤️ by [Your Name]

---

**Note**: This tool is not affiliated with LinkedIn. Use at your own risk and in accordance with LinkedIn's Terms of Service.
>>>>>>> 0b8f0c8 (Fixed adding users)
