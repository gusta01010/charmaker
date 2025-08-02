# CharMaker
Web Search-based AI Card Character Creator

**Create Character Cards by sending multiple URLs and even Images to AI!**

This simple open-source tool helps you create a desired character by appending to AI the website scrapped content and inserted images, generating its
- Name
- Carefully detailed description
- Brief personality
- Example messages
- Greeting messages

Built with selenium.

## Usage
1. Run `main.py`
2. Set up your desired save folder, provider, with your own API key,
    1. Separate System Messages: Disables or enables if should merge all scrapped content into a single system prompt
3. Start Character Creation - Here, you can **append URLs of characters for example, from wiki**, **append image URLs** and using `!` **you can append images from local computer**, press `ENTER` in the empty input box to send the appended information
4. After scrapping its contents and the AI returns the character's metadata, you can:
    1. Save the character card image using **SillyTavern's default .png template**, **Image from local computer** or **Image from a URL**
    2. Retry (You can send additional instruction as user to AI for feedback)
    3. Discard (Discards the character)

The character card will be saved in the set up save folder.
