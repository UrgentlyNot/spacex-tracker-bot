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

def search_spacex_launch_events():
    # Target specific phrases for today's launch events
    today = datetime.now(timezone.utc).date()
    query = 'from:SpaceX ("Watch Falcon 9 launch" OR "Liftoff of Falcon 9" OR "Falcon 9 launches" lang:en)'
    try:
        tweets = client.search_recent_tweets(query=query, max_results=10)
        return [tweet for tweet in (tweets.data or []) if datetime.fromisoformat(tweet.created_at.replace(tzinfo=timezone.utc)).date() == today]
    except tweepy.TweepyException as e:
        if e.response and e.response.status_code == 429:
            logging.error(f"Rate limit exceeded for launch event search: {e}. Waiting 15 minutes.")
            time.sleep(900)
            return []
        logging.error(f"Error searching launch events: {e}")
        return []

def tweet_launch_event(post):
    post_id = str(post.id)
    tweeted_posts = load_json(TWEETED_POSTS_FILE)
    if post_id in tweeted_posts:
        print(f"Post {post_id} already tweeted, skipping.")
        logging.info(f"Post {post_id} already tweeted, skipping.")
        return

    text = post.text[:200] + "..." if len(post.text) > 200 else post.text
    post_url = f"https://x.com/SpaceX/status/{post_id}"
    tweet = f"SpaceX Update: {text} {post_url}"
    if len(tweet) > 280:
        text = post.text[:280 - len(post_url) - 25] + "..."
        tweet = f"SpaceX Update: {text} {post_url}"
    try:
        client.create_tweet(text=tweet)
        tweeted_posts.append(post_id)
        save_json(TWEETED_POSTS_FILE, tweeted_posts)
        print(f"Tweeted launch event: {tweet}")
        logging.info(f"Tweeted launch event: {tweet}")
    except tweepy.TweepyException as e:
        print(f"Error tweeting launch event: {e}")
        logging.error(f"Error tweeting launch event: {e}")

def search_starlink_updates():
    # Target Starlink posts twice daily
    query = 'from:Starlink (launch OR availability OR deployment lang:en)'
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
    post_url = f"https://x.com/Starlink/status/{post_id}"
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

def search_starship_elon():
    # Target Elon Musk's Starship posts
    query = 'from:elonmusk (Starship OR rocket OR launch OR test) -filter:retweets lang:en'
    try:
        tweets = client.search_recent_tweets(query=query, max_results=10)
        return tweets.data if tweets.data else []
    except tweepy.TweepyException as e:
        if e.response and e.response.status_code == 429:
            logging.error(f"Rate limit exceeded for Starship Elon search: {e}. Waiting 15 minutes.")
            time.sleep(900)
            return []
        logging.error(f"Error searching Starship Elon: {e}")
        return []

def tweet_starship_elon(post):
    post_id = str(post.id)
    tweeted_posts = load_json(TWEETED_POSTS_FILE)
    if post_id in tweeted_posts:
        print(f"Post {post_id} already tweeted, skipping.")
        logging.info(f"Post {post_id} already tweeted, skipping.")
        return

    text = post.text[:200] + "..." if len(post.text) > 200 else post.text
    post_url = f"https://x.com/elonmusk/status/{post_id}"
    tweet = f"Starship Update from Elon: {text} {post_url}"
    if len(tweet) > 280:
        text = post.text[:280 - len(post_url) - 25] + "..."
        tweet = f"Starship Update from Elon: {text} {post_url}"
    try:
        client.create_tweet(text=tweet)
        tweeted_posts.append(post_id)
        save_json(TWEETED_POSTS_FILE, tweeted_posts)
        print(f"Tweeted Starship Elon update: {tweet}")
        logging.info(f"Tweeted Starship Elon update: {tweet}")
    except tweepy.TweepyException as e:
        print(f"Error tweeting Starship Elon update: {e}")
        logging.error(f"Error tweeting Starship Elon update: {e}")

def main():
    now = datetime.now(timezone.utc)
    
    # SpaceX launch events (checked hourly for today's posts)
    launch_events = search_spacex_launch_events()
    if launch_events:
        for event in launch_events:
            tweet_launch_event(event)
    
    # Starlink updates (2 writes/day, at 00:00 and 12:00 UTC)
    if now.hour in [0, 12]:
        starlink_posts = search_starlink_updates()
        if starlink_posts:
            for post in starlink_posts[:2]:  # 2 writes
                tweet_starlink_update(post)
    
    # Starship updates from Elon (7 writes every 3 hours, 8 times/day)
    if now.hour % 3 == 0:
        starship_posts = search_starship_elon()
        if starship_posts:
            for post in starship_posts[:7]:  # 7 writes
                tweet_starship_elon(post)
    
    # Extra Elon Starship updates (2 writes every 12 hours)
    if now.hour % 12 == 0:
        elon_posts = search_starship_elon()
        if elon_posts:
            for post in elon_posts[:2]:  # 2 writes
                tweet_starship_elon(post)

if __name__ == "__main__":
    main()
