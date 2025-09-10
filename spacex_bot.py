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

# X API credentials (use config.py or environment variables)
try:
    import config
    API_KEY = config.API_KEY
    API_SECRET = config.API_SECRET
    ACCESS_TOKEN = config.ACCESS_TOKEN
    ACCESS_TOKEN_SECRET = config.ACCESS_TOKEN_SECRET
    BEARER_TOKEN = config.BEARER_TOKEN
except ImportError:
    API_KEY = os.getenv("API_KEY", "your_api_key")
    API_SECRET = os.getenv("API_SECRET", "your_api_secret")
    ACCESS_TOKEN = os.getenv("ACCESS_TOKEN", "your_access_token")
    ACCESS_TOKEN_SECRET = os.getenv("ACCESS_TOKEN_SECRET", "your_access_token_secret")
    BEARER_TOKEN = os.getenv("BEARER_TOKEN", "your_bearer_token")

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

# File paths
TRACKER_FILE = "tweeted_launches.json"
TWEET_TRACKER_FILE = "tweeted_x_posts.json"
UPCOMING_FILE = "upcoming_launches.json"
PAST_FILE = "past_launches.json"
STARSHIP_ELON_FILE = "starship_elon_posts.json"

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
    tweeted_launches = load_json(TRACKER_FILE)
    if launch_id in tweeted_launches:
        return

    name = launch.get("name", "Unknown Mission")
    date_utc = launch.get("date_utc", "TBD")
    date = format_date(date_utc)
    tweet = f"Upcoming SpaceX Launch: {name} on {date}"
    try:
        client.create_tweet(text=tweet)
        tweeted_launches.append(launch_id)
        save_json(TRACKER_FILE, tweeted_launches)
        print(f"Tweeted launch: {tweet}")
        logging.info(f"Tweeted launch: {tweet}")
    except tweepy.TweepyException as e:
        print(f"Error tweeting launch: {e}")
        logging.error(f"Error tweeting launch: {e}")

def tweet_daily_launches(launches):
    now = datetime.now(timezone.utc)
    next_24hrs = now + timedelta(hours=24)
    daily_launches = [
        l for l in launches
        if l.get("date_utc") and now < datetime.fromisoformat(l["date_utc"].replace('Z', '+00:00')) < next_24hrs
    ]
    if not daily_launches:
        tweet = "No SpaceX launches scheduled in the next 24 hours."
    else:
        launch_list = "\n".join([f"- {l['name']} on {format_date(l['date_utc'])}" for l in daily_launches])
        tweet = f"SpaceX Launches in Next 24 Hours:\n{launch_list}"
    try:
        client.create_tweet(text=tweet)
        print(f"Tweeted daily launches: {tweet}")
        logging.info(f"Tweeted daily launches: {tweet}")
    except tweepy.TweepyException as e:
        print(f"Error tweeting daily launches: {e}")
        logging.error(f"Error tweeting daily launches: {e}")

def tweet_livestream_start():
    # Simple placeholder for livestream start tweet (expand with search if needed)
    tweet = "SpaceX Livestream Starting Soon. Check @SpaceX for details."
    try:
        client.create_tweet(text=tweet)
        print(f"Tweeted livestream start: {tweet}")
        logging.info(f"Tweeted livestream start: {tweet}")
    except tweepy.TweepyException as e:
        print(f"Error tweeting livestream start: {e}")
        logging.error(f"Error tweeting livestream start: {e}")

def tweet_end_of_day_summary():
    tweet = "SpaceX Daily Summary: Check @SpaceX for today's updates."
    try:
        client.create_tweet(text=tweet)
        print(f"Tweeted end-of-day summary: {tweet}")
        logging.info(f"Tweeted end-of-day summary: {tweet}")
    except tweepy.TweepyException as e:
        print(f"Error tweeting end-of-day summary: {e}")
        logging.error(f"Error tweeting end-of-day summary: {e}")

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
    post_id = post.id
    tweeted_posts = load_json(TWEET_TRACKER_FILE)
    if str(post_id) in tweeted_posts:
        return

    text = post.text[:200] + "..." if len(post.text) > 200 else post.text
    post_url = f"https://x.com/SpaceX/status/{post_id}"
    tweet = f"Starlink Update: {text} {post_url}"
    if len(tweet) > 280:
        text = post.text[:280 - len(post_url) - 25] + "..."
        tweet = f"Starlink Update: {text} {post_url}"
    try:
        client.create_tweet(text=tweet)
        tweeted_posts.append(str(post_id))
        save_json(TWEET_TRACKER_FILE, tweeted_posts)
        print(f"Tweeted Starlink update: {tweet}")
        logging.info(f"Tweeted Starlink update: {tweet}")
    except tweepy.TweepyException as e:
        print(f"Error tweeting Starlink update: {e}")
        logging.error(f"Error tweeting Starlink update: {e}")

def search_starship_elon():
    query = "from:elonmusk Starship -launch -rocket"
    try:
        tweets = client.search_recent_tweets(query=query, max_results=5)
        return tweets.data if tweets.data else []
    except tweepy.TweepyException as e:
        if e.response and e.response.status_code == 429:
            logging.error(f"Rate limit exceeded for Starship Elon search: {e}. Waiting 15 minutes.")
            time.sleep(900)
            return []
        logging.error(f"Error searching Starship Elon: {e}")
        return []

def tweet_starship_elon(post):
    post_id = post.id
    tweeted_posts = load_json(STARSHIP_ELON_FILE)
    if str(post_id) in tweeted_posts:
        return

    text = post.text[:200] + "..." if len(post.text) > 200 else post.text
    post_url = f"https://x.com/elonmusk/status/{post_id}"
    tweet = f"Starship Update from Elon: {text} {post_url}"
    if len(tweet) > 280:
        text = post.text[:280 - len(post_url) - 25] + "..."
        tweet = f"Starship Update from Elon: {text} {post_url}"
    try:
        client.create_tweet(text=tweet)
        tweeted_posts.append(str(post_id))
        save_json(STARSHIP_ELON_FILE, tweeted_posts)
        print(f"Tweeted Starship Elon update: {tweet}")
        logging.info(f"Tweeted Starship Elon update: {tweet}")
    except tweepy.TweepyException as e:
        print(f"Error tweeting Starship Elon update: {e}")
        logging.error(f"Error tweeting Starship Elon update: {e}")

def main():
    now = datetime.now(timezone.utc)
    
    # Starlink updates (10 reads/day, 2 writes; every 4 hours, 6 times/day)
    if now.hour % 4 == 0:  # Approximate; adjust as needed
        posts = search_starlink_updates()
        if posts:
            for post in posts[:2]:  # 2 writes
                tweet_starlink_update(post)
    
    # Daily launch summary at 1am GMT (1 write, 2 reads)
    if now.hour == 1:
        launches = get_spacex_launches("upcoming")
        tweet_daily_launches(launches)
    
    # Livestream starting (1 write, 2 reads; check 4 times/day)
    if now.hour in [0, 6, 12, 18]:
        tweet_livestream_start()
    
    # End-of-day summary at 11:59 (1 write, 2 reads)
    if now.hour == 23:
        tweet_end_of_day_summary()
    
    # Starship stuff (8 reads, 9 writes; every 3 hours, 8 times/day)
    if now.hour % 3 == 0:
        starship_posts = search_starship_elon()  # Re-use for general
        for post in starship_posts[:7]:  # 7 writes
            tweet_starship_elon(post)
    
    # Extra Elon Starship (2 reads, 2 writes; every 12 hours)
    if now.hour % 12 == 0:
        elon_posts = search_starship_elon()
        for post in elon_posts[:2]:
            tweet_starship_elon(post)

if __name__ == "__main__":
    main()

