"""
Scorecard (Accuracy + Roleplaying quality):
        	Description	    Greeting	Combined
Preset 1     	78	           82	       80
Preset 2     	74	           81	      77.5
-Analyzed with anthropic/claude-opus-4.6-search + google/gemini-3.1-pro-preview-grounding, using same 3 URLS + 1 image

Preset 1: Most canon-faithful voice, captures character's exact psychological profile, real experience
Preset 2: Best thematic writing, Prioritizes dramatic flair and "spicy" dialogue over strict wiki-adherence, cinematic experience
"""

from presets import PRESET1, PRESET2

INSTRUCTIONS = PRESET1