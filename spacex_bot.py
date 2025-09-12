import tweepy
import requests
import json
import os
import logging
import time
from datetime import datetime, timedelta, timezone

# Set up logging
logging.basicConfig(filename="spacex_bot.log", level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logging.info("Script started")

# X API credentials (use environment variables from GitHub secrets)
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
ACCESS_TOKEN_SECRET = os.getenv("ACCESS_TOKEN_SECRET")
BEARER_TOKEN = os.getenv("BEARER_TOKEN")

# Authenticate with X API v2
try:
    client = tweepy.Client(
        bearer_token=BEARER_TOKEN,
        consumer_key=API_KEY,
        consumer_secret=API_SECRET,
        access_token=ACCESS_TOKEN,
        access_token_secret=ACCESS_TOKEN_SECRET
    )
    user = client.get_me().data
    logging.info(f"Authenticated as: {user.username}")
    print(f"Authenticated as: {user.username}")
except tweepy.TweepyException as e:
    logging.error(f"X API v2 authentication failed: {e}")
    print(f"Authentication error: {e}")
    exit()

# File paths for tracking
TWEETED_POSTS_FILE = "tweeted_x_posts.json"
LAUNCH_WINDOW_FILE = "launch_window.json"

def load_json(file_path):
    if os.path.exists(file_path):
        try:
            with open(file_path, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            logging.error(f"Corrupted JSON file: {file_path}. Resetting.")
            return []
    return []

def save_json(file_path, data):
    try:
        with open(file_path, "w") as f:
            json.dump(data, f)
    except Exception as e:
        logging.error(f"Error saving JSON to {file_path}: {e}")

def get_spacex_launches():
    url = "https://api.spacexdata.com/v4/launches/upcoming"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        logging.info(f"Fetched SpaceX upcoming launches")
        return data
    except requests.RequestException as e:
        logging.error(f"Error fetching SpaceX data: {e}")
        print(f"Error fetching SpaceX data: {e}")
        return []

def format_date(utc_date_str):
    try:
        dt = datetime.fromisoformat(utc_date_str.replace('Z', '+00:00'))
        return dt
    except (ValueError, TypeError):
        return None

def search_social_updates(account, query):
    try:
        tweets = client.search_recent_tweets(query=query, max_results=10)
        return tweets.data if tweets.data else []
    except tweepy.TweepyException as e:
        if e.response and e.response.status_code == 429:
            logging.error(f"Rate limit exceeded for {account} search: {e}. Waiting 15 minutes.")
            time.sleep(900)
            return []
        logging.error(f"Error searching {account} updates: {e}")
        return []

def categorize_elon_post(post_text):
    post_text = post_text.lower()
    if any(keyword in post_text for keyword in ["falcon", "launch", "mission"]):
        return "SpaceX Update from Elon"
    elif any(keyword in post_text for keyword in ["starlink", "satellite"]):
        return "Starlink Update from Elon"
    elif any(keyword in post_text for keyword in ["starship", "rocket", "test"]):
        return "Starship Update from Elon"
    return None

def tweet_update(post, category):
    post_id = str(post.id)
    tweeted_posts = load_json(TWEETED_POSTS_FILE)
    if post_id in tweeted_posts:
        print(f"Post {post_id} already tweeted, skipping.")
        logging.info(f"Post {post_id} already tweeted, skipping.")
        return

    text = post.text[:200] + "..." if len(post.text) > 200 else post.text
    post_url = f"https://x.com/{post.author_id}/status/{post_id}"
    tweet = f"{category}: {text} {post_url}"
    if len(tweet) > 280:
        text = post.text[:280 - len(post_url) - len(category) - 3] + "..."
        tweet = f"{category}: {text} {post_url}"
    try:
        client.create_tweet(text=tweet)
        tweeted_posts.append(post_id)
        save_json(TWEETED_POSTS_FILE, tweeted_posts)
        print(f"Tweeted: {tweet}")
        logging.info(f"Tweeted: {tweet}")
    except tweepy.TweepyException as e:
        print(f"Error tweeting: {e}")
        logging.error(f"Error tweeting: {e}")

def check_launch_window():
    launches = get_spacex_launches()
    now = datetime.now(timezone.utc)
    launch_window = load_json(LAUNCH_WINDOW_FILE)
    in_window = launch_window.get("in_window", False)
    next_check = launch_window.get("next_check", 1800)  # Default 30 minutes in seconds

    for launch in launches:
        date_utc = format_date(launch.get("date_utc"))
        if date_utc and abs((date_utc - now).total_seconds()) <= 3600:  # ±1 hour window
            in_window = True
            next_check = 60  # Switch to 1-minute checks
            save_json(LAUNCH_WINDOW_FILE, {"in_window": True, "next_check": next_check})
            logging.info(f"Entered launch window for {launch.get('name')} at {date_utc}")
            return next_check

    # Check for payload deploy confirmation
    spacex_posts = search_social_updates("SpaceX", 'from:SpaceX ("payload deploy" OR "mission success" lang:en)')
    if spacex_posts and any("payload deploy" in post.text.lower() or "mission success" in post.text.lower() for post in spacex_posts):
        in_window = False
        next_check = 1800  # Revert to 30 minutes
        save_json(LAUNCH_WINDOW_FILE, {"in_window": False, "next_check": next_check})
        logging.info("Payload deploy confirmed, exiting launch window")

    save_json(LAUNCH_WINDOW_FILE, {"in_window": in_window, "next_check": next_check})
    return next_check

def main():
    now = datetime.now(timezone.utc)
    next_check = check_launch_window()

    # Run every 30 minutes or 1 minute during launch window
    if now.second == 0:  # Align with minute boundary
        # SpaceX launch events
        spacex_posts = search_social_updates("SpaceX", 'from:SpaceX ("Watch Falcon 9 launch" OR "Liftoff of Falcon 9" OR "Falcon 9 launches" lang:en)')
        if spacex_posts:
            for post in spacex_posts:
                tweet_update(post, "SpaceX Update")

        # Starlink updates (twice daily at 00:00 and 12:00 UTC)
        if now.hour in [0, 12]:
            starlink_posts = search_social_updates("Starlink", 'from:Starlink (launch OR availability OR deployment lang:en)')
            if starlink_posts:
                for post in starlink_posts[:2]:  # 2 writes
                    tweet_update(post, "Starlink Update from Starlink")

        # Elon Musk updates
        elon_posts = search_social_updates("Elon", 'from:elonmusk -filter:retweets lang:en')
        if elon_posts:
            for post in elon_posts:
                category = categorize_elon_post(post.text)
                if category:
                    tweet_update(post, category)

    # Schedule next run based on launch window
    time.sleep(max(0, next_check - now.second))  # Wait until next interval

if __name__ == "__main__":
    while True:
        main()
