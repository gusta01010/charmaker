"""
Scorecard (Accuracy + Roleplaying quality):
        	Description    Greeting     Combined  
Preset 1    88.3           88.0         88.2
Preset 2    78.0           84.3         81.2 
Preset 3    82.0           78.0         80.0

-Average analyzed with internet sources from the models:
	anthropic/claude-opus-4.6-search
    google/gemini-3.1-pro-preview-grounding,
    gpt-5.2-search
    
using the same 2 URLS + 2 images and gemini-3-flash-preview + crawl4ai to generate.

Preset 1: Experimental,  great results.
Preset 2: Tends to write shorter descriptions (1300 - 2100)
Preset 3: Tends to write longer descriptions (2000 - 3500)
"""

from presets import PRESET1, PRESET2, PRESET3

INSTRUCTIONS = PRESET1