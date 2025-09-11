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

# File paths for tracking (prevent duplicates)
TWEETED_LAUNCHES_FILE = "tweeted_launches.json"
TWEETED_POSTS_FILE = "tweeted_x_posts.json"

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

def format_date(utc_date_str):
    try:
        dt = datetime.fromisoformat(utc_date_str.replace('Z', '+00:00'))
        return dt.strftime("%b %d, %Y, %I:%M %p UTC")
    except (ValueError, TypeError):
        return "TBD"

def get_spacex_launches(endpoint="upcoming"):
    url = f"https://api.spacexdata.com/v4/launches/{endpoint}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        logging.info(f"Fetched SpaceX {endpoint} launches")
        return [data] if isinstance(data, dict) else data
    except requests.RequestException as e:
        logging.error(f"Error fetching SpaceX data: {e}")
        print(f"Error fetching SpaceX data: {e}")
        return []

def tweet_launch(launch):
    launch_id = launch.get("id")
    tweeted_launches = load_json(TWEETED_LAUNCHES_FILE)
    if launch_id in tweeted_launches:
        print(f"Launch {launch_id} already tweeted.")
        logging.info(f"Launch {launch_id} already tweeted")
        return

    name = launch.get("name", "Unknown Mission")
    date_utc = launch.get("date_utc", "TBD")
    date = format_date(date_utc)
    tweet = f"Upcoming SpaceX Launch: {name} on {date}"
    try:
        client.create_tweet(text=tweet)
        tweeted_launches.append(launch_id)
        save_json(TWEETED_LAUNCHES_FILE, tweeted_launches)
        print(f"Tweeted launch: {tweet}")
        logging.info(f"Tweeted launch: {tweet}")
    except tweepy.TweepyException as e:
        print(f"Error tweeting launch: {e}")
        logging.error(f"Error tweeting launch: {e}")

def search_starlink_updates():
    query = "from:SpaceX (Starlink launch OR Starlink availability OR Starlink deployment)"
    try:
        tweets = client.search_recent_tweets(query=query, max_results=10)
        return tweets.data if tweets.data else []
    except tweepy.TweepyException as e:
        if e.response and e.response.status_code == 429:
            logging.error(f"Rate limit exceeded for Starlink search: {e}. Waiting 15 minutes.")
            time.sleep(900)
            return []
        logging.error(f"Error searching Starlink updates: {e}")
        return []

def tweet_starlink_update(post):
    post_id = str(post.id)
    tweeted_posts = load_json(TWEETED_POSTS_FILE)
    if post_id in tweeted_posts:
        print(f"Post {post_id} already tweeted, skipping.")
        logging.info(f"Post {post_id} already tweeted, skipping.")
        return

    text = post.text[:200] + "..." if len(post.text) > 200 else post.text
    post_url = f"https://x.com/SpaceX/status/{post_id}"
    tweet = f"Starlink Update: {text} {post_url}"
    if len(tweet) > 280:
        text = post.text[:280 - len(post_url) - 25] + "..."
        tweet = f"Starlink Update: {text} {post_url}"
    try:
        client.create_tweet(text=tweet)
        tweeted_posts.append(post_id)
        save_json(TWEETED_POSTS_FILE, tweeted_posts)
        print(f"Tweeted Starlink update: {tweet}")
        logging.info(f"Tweeted Starlink update: {tweet}")
    except tweepy.TweepyException as e:
        print(f"Error tweeting Starlink update: {e}")
        logging.error(f"Error tweeting Starlink update: {e}")

def main():
    now = datetime.now(timezone.utc)
    
    # Starlink updates (10 reads/day, 2 writes; every 4 hours, 6 times/day)
    if now.hour % 4 == 0:
        posts = search_starlink_updates()
        if posts:
            for post in posts[:2]:  # 2 writes
                tweet_starlink_update(post)
    
    # Daily launch summary at 1am GMT (1 write, 2 reads)
    if now.hour == 1:
        launches = get_spacex_launches("upcoming")
        tweet_daily_launches(launches)
    
    # Livestream starting (1 write, 2 reads; 4 times/day)
    if now.hour in [0, 6, 12, 18]:
        launches = get_spacex_launches("upcoming")
        if launches:
            tweet_launch(launches[0])  # 1 write

    # End-of-day summary at 11:59 (1 write, 2 reads)
    if now.hour == 23:
        launches = get_spacex_launches("upcoming")
        if launches:
            tweet_launch(launches[0])  # 1 write

    # Starship stuff (8 reads, 9 writes; every 3 hours, 8 times/day)
    if now.hour % 3 == 0:
        starship_posts = search_starship_elon()  # 8 reads
        if starship_posts:
            for post in starship_posts[:7]:  # 7 writes
                tweet_starship_elon(post)
    
    # Extra Elon Starship (2 reads, 2 writes; every 12 hours)
    if now.hour % 12 == 0:
        elon_posts = search_starship_elon()
        if elon_posts:
            for post in elon_posts[:2]:  # 2 writes
                tweet_starship_elon(post)

if __name__ == "__main__":
    main()
