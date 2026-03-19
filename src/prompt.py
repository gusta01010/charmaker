"""
Scorecard (Accuracy + Roleplaying quality):
        	Description	    	  Greeting		 Combined
Preset 1     	80.50	           83.00	       81.33
Preset 2     	71.38	           80.75	       75.95
Preset 3		87.75			   87.00		   87.68
-Average analyzed with internet sources from the models:
	anthropic/claude-opus-4.6-search
    anthropic/claude-opus-4.6-search
    google/gemini-3.1-pro-preview-grounding,
    gpt-5.2-search
    
using same 3 URLS + 1 image and gemini-3-flash-preview to generate.

Preset 1: Captures character's psychological profile, alive experience
Preset 2: Prioritizes dramatic flair and "spicy" dialogue over strict wiki-adherence, cinematic experience
Preset 3: Sensory-rich prose that excels at atmospheric writing and internal emotional depth, fewest factual errors.
"""

from presets import PRESET1, PRESET2, PRESET3

INSTRUCTIONS = PRESET3