# 16PF Voice Personality Analysis Integration

This document explains how to configure and use the 16PF (Sixteen Personality Factor) voice analysis feature in the Rolevo application.

## Overview

The 16PF voice analysis feature allows you to analyze user's voice recordings during roleplay sessions to generate personality factor scores. This is powered by the **Persona360 API** and can also integrate with third-party plugins.

## Features

- **Automatic Analysis**: When enabled, audio recordings from roleplay sessions are automatically analyzed after completion
- **Manual Analysis**: Admin users can trigger analysis manually via API endpoints
- **Report Integration**: 16PF scores are automatically included in the Skills Gauge PDF reports
- **Configurable per Roleplay**: Each roleplay can have its own 16PF configuration

## Setup

### 1. Database Migration

Run the migration script to add the necessary database columns and tables:

```bash
python sql/add_16pf_analysis.py
```

This creates:
- New columns in `roleplay_config` table for 16PF settings
- New `pf16_analysis_results` table for storing analysis results

### 2. Environment Variables (Optional)

Add these to your `.env` file to customize the Persona360 API configuration:

```env
# Persona360 API Configuration
PERSONA360_API_URL=http://api.persona360.rapeti.dev:8290/predict
PERSONA360_API_KEY=your_api_key_if_required
PERSONA360_TIMEOUT=120
```

### 3. Enable for Roleplay

In the Admin Panel when creating or editing a roleplay:

1. Scroll to **"16PF Voice Personality Analysis"** section
2. Check **"Enable 16PF Voice Analysis"**
3. Select the **Analysis Source**:
   - `Persona360 API` - Uses the Persona360 service
   - `Third Party Plugin` - For custom integrations
4. Configure additional options:
   - `Require User Age for Analysis` - Prompts user for age
   - `Require User Gender for Analysis` - Prompts user for gender
   - `Send Audio for Analysis` - Enables audio submission to API
   - `Default Age` - Fallback age if not provided

## API Endpoints

### 1. Check Analysis Status

Get the status and results of 16PF analysis for a play session:

```
GET /api/16pf/status/<play_id>
```

**Response:**
```json
{
    "success": true,
    "status": "completed",
    "personality_scores": {
        "Warmth": 65,
        "Reasoning": 72,
        ...
    },
    "composite_scores": {
        "Adjustment": 70,
        "Communication": 68,
        ...
    },
    "overall_role_fit": 72.5,
    "analysis_confidence": 85.0
}
```

### 2. Manually Trigger Analysis (Admin Only)

Trigger 16PF analysis for a completed play session:

```
POST /api/16pf/trigger/<play_id>

{
    "age": 35,
    "gender": "Male",
    "source": "persona360"
}
```

### 3. Analyze Custom Audio File (Admin Only)

Analyze an audio file directly:

```
POST /api/16pf/analyze

{
    "audio_file_path": "/path/to/audio.mp3",
    "age": 30,
    "gender": "Female"
}
```

### 4. Upload and Analyze (Admin Only)

Upload an audio/video file for analysis:

```
POST /api/16pf/upload-analyze

Form Data:
- file: audio/video file
- age: 30
- gender: Male
```

## 16PF Personality Factors

The analysis provides scores for these 16 primary personality factors:

| Factor | Description |
|--------|-------------|
| Warmth (A) | Reserved vs. Warm |
| Reasoning (B) | Concrete vs. Abstract |
| Emotional Stability (C) | Reactive vs. Emotionally Stable |
| Dominance (E) | Deferential vs. Dominant |
| Liveliness (F) | Serious vs. Lively |
| Rule-Consciousness (G) | Expedient vs. Rule-Conscious |
| Social Boldness (H) | Shy vs. Socially Bold |
| Sensitivity (I) | Utilitarian vs. Sensitive |
| Vigilance (L) | Trusting vs. Vigilant |
| Abstractedness (M) | Grounded vs. Abstracted |
| Privateness (N) | Forthright vs. Private |
| Apprehension (O) | Self-Assured vs. Apprehensive |
| Openness to Change (Q1) | Traditional vs. Open to Change |
| Self-Reliance (Q2) | Group-Oriented vs. Self-Reliant |
| Perfectionism (Q3) | Tolerates Disorder vs. Perfectionistic |
| Tension (Q4) | Relaxed vs. Tense |

## Composite Scores

In addition to the 16 primary factors, composite scores are calculated for:

- Adjustment
- Agreeableness
- Ambition
- Communication
- Conscientiousness
- Cooperation
- Creativity
- Technology Fit
- Sales Fit
- Management Fit
- Customer Service Fit

## Report Integration

When 16PF analysis is complete, the results are automatically included in the "Personality Fit (Voice)" section of the Skills Gauge PDF report. This includes:

- Overall Role Fit percentage
- Individual personality trait scores with visual indicators
- Comparison against target scores

## Troubleshooting

### Analysis Not Triggering

1. Verify 16PF is enabled for the roleplay in admin settings
2. Check that `pf16_analysis_source` is set to `persona360` (not `none`)
3. Ensure `pf16_send_audio_for_analysis` is enabled
4. Verify audio files are being recorded during the session

### API Connection Issues

1. Check the Persona360 API URL is correct
2. Verify network connectivity to the API endpoint
3. Check the `PERSONA360_TIMEOUT` setting if requests are timing out
4. Review server logs for detailed error messages

### Missing Personality Data in Reports

1. Check analysis status via `/api/16pf/status/<play_id>`
2. Ensure analysis completed before report generation
3. The report generation now waits for 16PF data when available

## Files Modified/Created

- `app/persona360_service.py` - Persona360 API service
- `app/queries.py` - Database functions for 16PF
- `app/routes.py` - 16PF API endpoints and triggering logic
- `app/report_generator_v2.py` - Report integration
- `app/templates/adminview.html` - Admin UI configuration
- `sql/add_16pf_analysis.py` - Database migration
- `config.py` - Configuration options

## Example Usage with cURL

```bash
# Upload and analyze a file
curl -X POST "http://localhost:5000/api/16pf/upload-analyze" \
    -H "Content-Type: multipart/form-data" \
    -F "file=@recording.mp4" \
    -F "age=35" \
    -F "gender=Male"

# Direct API call to Persona360
curl -X POST "http://api.persona360.rapeti.dev:8290/predict" \
    -H "accept: application/json" \
    -H "Content-Type: multipart/form-data" \
    -F "file=@recording.mp4" \
    -F "mode=audio_only" \
    -F "age=35" \
    -F "gender=Male"
```
