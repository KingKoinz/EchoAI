# EchoAI - AI Video Generator

Create viral short-form videos for TikTok, YouTube Shorts, Instagram Reels, and more using AI.

## Features

✨ **AI-Powered Script Generation** - Claude AI creates engaging scripts
🎤 **Voice Synthesis** - ElevenLabs premium voices with free fallback
📸 **Automatic Image Selection** - Vecteezy, Pexels, and fallback sources
🎬 **Professional Transitions** - 6+ transition effects
💬 **Auto Captions** - Multiple caption styles (bounce, color box, karaoke)
🌍 **Multi-Platform** - TikTok, YouTube, Instagram optimized
⚙️ **Customizable** - Duration, style, transitions all configurable

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure API Keys

Edit `config/settings.yaml` with your API keys:
- Claude API key
- ElevenLabs API key (optional, has free fallback)
- Pexels API key
- Vecteezy API key (optional)

### 3. Run Web Interface

```bash
python app.py
```

Open http://localhost:5000 in your browser

### 4. Or Use Command Line

```bash
python run_pipeline.py "Your Video Topic"
```

## Web Interface

The web interface provides:
- **Easy Form** - Just enter a topic and click generate
- **Platform Selection** - Choose TikTok, YouTube, Instagram, etc.
- **Style Options** - Viral facts, story time, motivational, educational
- **Real-time Progress** - Watch your video being created
- **Preview & Download** - Preview before downloading

## Command Line Usage

```bash
# Basic usage
python run_pipeline.py "Things I Ignored Because She Was Cute"

# Use stored images (skip image generation)
python run_pipeline.py "Your Topic" --use-stored-images
```

## Configuration

Edit `config/settings.yaml` to customize:

```yaml
video:
  duration_seconds: 25
  style: "viral_facts"
  transition:
    enabled: true
    type: "fade"  # fade, slideright, wiperight, dissolve, etc.
    duration: 0.5
```

## Available Transitions

- **fade** - Classic crossfade
- **slideright** / **slideleft** - Slide transitions
- **wiperight** / **wipeleft** - Wipe effects
- **dissolve** - Pixel dissolve
- **circleopen** / **circleclose** - Circular reveals

## Project Structure

```
EchoAI/
├── app.py                    # Flask web server
├── run_pipeline.py           # CLI pipeline runner
├── config/
│   └── settings.yaml         # Configuration
├── scripts/
│   ├── make_script.py        # AI script generation
│   ├── make_voice.py         # Voice synthesis
│   ├── make_images.py        # Image collection
│   ├── make_captions_*.py    # Caption styles
│   └── make_video_render.py  # Video rendering
├── templates/
│   └── index.html            # Web interface
├── output/                   # Generated content
├── images/                   # Downloaded images
└── jobs/                     # Web job tracking

## API Endpoints

- `GET /` - Web interface
- `POST /api/generate` - Start video generation
- `GET /api/status/<job_id>` - Check job status
- `GET /api/download/<job_id>` - Download video
- `GET /api/config` - Get available options

## Deployment

### Local Development
```bash
python app.py
```

### Production (Gunicorn)
```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Docker (Coming Soon)
```bash
docker build -t echoai .
docker run -p 5000:5000 echoai
```

## Requirements

- Python 3.8+
- FFmpeg (for video rendering)
- API Keys:
  - Claude (Anthropic)
  - ElevenLabs (optional)
  - Pexels
  - Vecteezy (optional)

## License

MIT License - Use freely for commercial projects

## Support

For issues or questions, open a GitHub issue or contact support.

---

Made with ❤️ by EchoAI Team
