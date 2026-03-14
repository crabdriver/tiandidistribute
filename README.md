# WeChat Article Auto-Publisher

A minimalist Python tool to automatically convert Markdown articles into beautifully formatted WeChat Official Account drafts.

## Features
- **Automatic Styling**: Converts Markdown to WeChat-ready HTML with premium minimalist CSS.
- **Image Hosting**: Automatically uploads images from Markdown to WeChat's servers.
- **Theme Support**: Clean, elegant design replication based on modern styles.
- **Credential Protection**: Uses `.env` files to keep API tokens safe.

## Setup
1. Clone this repository.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `secrets.env` file in the root directory:
   ```env
   WECHAT_APPID=your_appid
   WECHAT_SECRET=your_secret
   ```
4. Run the publisher:
   ```bash
   python wechat_publisher.py
   ```

## Usage
Edit the article directory path in `wechat_publisher.py` to point to your Markdown collection.
